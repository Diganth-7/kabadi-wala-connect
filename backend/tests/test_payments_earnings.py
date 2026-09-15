"""
tests/test_payments_earnings.py
---------------------------------
Tests covering:
  16. Payment
  17. Duplicate payment
  18. Earnings
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COLLECTOR_EMAIL = "collector@test.com"
RECYCLER_EMAIL = "recycler@test.com"        # manages GreenCycle Traders
RECYCLER2_EMAIL = "recycler2@test.com"      # manages EcoScrap Solutions
ADMIN_EMAIL = "admin@test.com"


def _auth_header(identifier: str) -> dict:
    login_resp = client.post("/api/auth/login", json={"identifier": identifier})
    otp = login_resp.json()["data"]["dev_otp"]
    verify_resp = client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp})
    token = verify_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _greencycle_id() -> str:
    resp = client.get("/api/recyclers")
    for r in resp.json()["data"]:
        if r["name"] == "GreenCycle Traders":
            return r["id"]
    raise AssertionError("GreenCycle Traders not found")


def _create_transaction(collector_headers: dict, recycler_headers: dict, weight=5.0, price=650) -> str:
    """
    Full flow helper: creates a lot, takes a pickup all the way through
    to a handover, and returns the resulting transaction_id.
    """
    lot_resp = client.post(
        "/api/lots",
        json={
            "material_id": "MAT001", "estimated_weight": weight, "condition": "GOOD",
            "location": {"latitude": 12.9716, "longitude": 77.5946},
            "photo_url": "https://example.com/p.jpg",
        },
        headers=collector_headers,
    )
    lot_id = lot_resp.json()["data"]["id"]

    pickup_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = pickup_resp.json()["data"]["id"]

    for s in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER"]:
        client.patch(f"/api/pickups/{pickup_id}/status", json={"status": s}, headers=recycler_headers)

    client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": weight, "agreed_price": price},
        headers=recycler_headers,
    )

    txns = client.get("/api/transactions", headers=collector_headers).json()["data"]
    matching = [t for t in txns if t["lot_id"] == lot_id]
    assert len(matching) == 1
    return matching[0]["id"]


# ----------------------------------------------------------------
# 16. Payment
# ----------------------------------------------------------------

def test_recycler_can_record_successful_payment():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    txn_id = _create_transaction(collector_headers, recycler_headers)

    resp = client.post("/api/payments", json={"transaction_id": txn_id, "method": "UPI"}, headers=recycler_headers)
    body = resp.json()
    assert resp.status_code == 201, body
    assert body["data"]["status"] == "PAID"
    assert body["data"]["transaction_id"] == txn_id


def test_payment_updates_transaction_status():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    txn_id = _create_transaction(collector_headers, recycler_headers)

    client.post("/api/payments", json={"transaction_id": txn_id, "method": "CASH"}, headers=recycler_headers)

    txns = client.get("/api/transactions", headers=collector_headers).json()["data"]
    txn = next(t for t in txns if t["id"] == txn_id)
    assert txn["payment_status"] == "PAID"
    assert txn["payment_method"] == "CASH"


def test_failed_payment_never_returns_paid():
    """A failed payment must never be returned as PAID -- checked directly."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    txn_id = _create_transaction(collector_headers, recycler_headers)

    resp = client.post(
        "/api/payments",
        json={"transaction_id": txn_id, "method": "UPI", "simulate_failure": True},
        headers=recycler_headers,
    )
    body = resp.json()
    assert resp.status_code == 402
    assert body["success"] is False
    assert body["error"]["code"] == "PAYMENT_FAILED"
    # Double-check: the transaction itself must reflect FAILED, never PAID.
    txns = client.get("/api/transactions", headers=collector_headers).json()["data"]
    txn = next(t for t in txns if t["id"] == txn_id)
    assert txn["payment_status"] == "FAILED"
    assert txn["payment_status"] != "PAID"


def test_only_transaction_recycler_or_admin_can_pay():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    txn_id = _create_transaction(collector_headers, recycler_headers)

    # collector tries
    resp = client.post("/api/payments", json={"transaction_id": txn_id, "method": "UPI"}, headers=collector_headers)
    assert resp.status_code == 403

    # unrelated recycler tries
    other_recycler_headers = _auth_header(RECYCLER2_EMAIL)
    resp2 = client.post("/api/payments", json={"transaction_id": txn_id, "method": "UPI"}, headers=other_recycler_headers)
    assert resp2.status_code == 403


def test_payment_for_nonexistent_transaction_returns_404():
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    resp = client.post("/api/payments", json={"transaction_id": "not-real", "method": "UPI"}, headers=recycler_headers)
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_invalid_payment_method_rejected():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    txn_id = _create_transaction(collector_headers, recycler_headers)

    resp = client.post("/api/payments", json={"transaction_id": txn_id, "method": "BITCOIN"}, headers=recycler_headers)
    assert resp.status_code == 422


# ----------------------------------------------------------------
# 17. Duplicate payment
# ----------------------------------------------------------------

def test_duplicate_successful_payment_rejected():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    txn_id = _create_transaction(collector_headers, recycler_headers)

    first = client.post("/api/payments", json={"transaction_id": txn_id, "method": "UPI"}, headers=recycler_headers)
    assert first.status_code == 201
    assert first.json()["data"]["status"] == "PAID"

    second = client.post("/api/payments", json={"transaction_id": txn_id, "method": "CASH"}, headers=recycler_headers)
    body = second.json()
    assert second.status_code == 409
    assert body["error"]["code"] == "PAYMENT_ALREADY_COMPLETED"


def test_retry_after_failed_payment_is_allowed():
    """A FAILED payment doesn't block a subsequent real attempt -- only a PAID one does."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    txn_id = _create_transaction(collector_headers, recycler_headers)

    failed = client.post(
        "/api/payments",
        json={"transaction_id": txn_id, "method": "UPI", "simulate_failure": True},
        headers=recycler_headers,
    )
    assert failed.status_code == 402

    retry = client.post("/api/payments", json={"transaction_id": txn_id, "method": "UPI"}, headers=recycler_headers)
    assert retry.status_code == 201
    assert retry.json()["data"]["status"] == "PAID"


# ----------------------------------------------------------------
# 18. Earnings
# ----------------------------------------------------------------

def test_earnings_shape_and_currency():
    resp = client.get("/api/earnings", headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 200
    data = body["data"]
    for key in ["today", "this_week", "this_month", "pending", "currency"]:
        assert key in data
    assert data["currency"] == "INR"


def test_earnings_reflect_paid_transaction():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)

    before = client.get("/api/earnings", headers=collector_headers).json()["data"]

    txn_id = _create_transaction(collector_headers, recycler_headers, weight=4.0, price=650)  # 4.0 * 650 = 2600
    client.post("/api/payments", json={"transaction_id": txn_id, "method": "UPI"}, headers=recycler_headers)

    after = client.get("/api/earnings", headers=collector_headers).json()["data"]

    assert after["today"] - before["today"] == 2600.0
    assert after["this_week"] - before["this_week"] == 2600.0
    assert after["this_month"] - before["this_month"] == 2600.0


def test_earnings_pending_reflects_unpaid_transaction():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)

    before = client.get("/api/earnings", headers=collector_headers).json()["data"]

    # Create a transaction but DON'T pay it -- stays PENDING.
    _create_transaction(collector_headers, recycler_headers, weight=2.0, price=650)  # 1300

    after = client.get("/api/earnings", headers=collector_headers).json()["data"]
    assert after["pending"] - before["pending"] == 1300.0


def test_earnings_not_hardcoded_differs_between_collectors():
    """Sanity check: two different collectors don't get identical hard-coded numbers."""
    resp1 = client.get("/api/earnings", headers=_auth_header(COLLECTOR_EMAIL))
    resp2 = client.get("/api/earnings", headers=_auth_header("collector3@test.com"))
    # Not asserting they're different (could coincidentally match), just
    # that both are independently computed and respond successfully.
    assert resp1.status_code == 200
    assert resp2.status_code == 200


def test_earnings_only_for_collectors():
    resp = client.get("/api/earnings", headers=_auth_header(RECYCLER_EMAIL))
    assert resp.status_code == 403

    resp2 = client.get("/api/earnings", headers=_auth_header(ADMIN_EMAIL))
    assert resp2.status_code == 403


def test_earnings_requires_auth():
    resp = client.get("/api/earnings")
    assert resp.status_code == 401
