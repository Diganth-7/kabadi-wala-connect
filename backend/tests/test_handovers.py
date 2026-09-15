"""
tests/test_handovers.py
-------------------------
Tests covering:
  13. Handover
  14. Final amount calculation
  15. Duplicate handover

Plus: automatic Transaction creation, pickup auto-completion, and
role-based transaction listing.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COLLECTOR_EMAIL = "collector@test.com"
COLLECTOR2_EMAIL = "collector2@test.com"
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
    raise AssertionError("GreenCycle Traders not found in seed data")


def _create_lot(headers: dict, material_id="MAT001") -> str:
    payload = {
        "material_id": material_id,
        "estimated_weight": 6.0,
        "condition": "GOOD",
        "location": {"latitude": 12.9716, "longitude": 77.5946},
        "photo_url": "https://example.com/p.jpg",
    }
    resp = client.post("/api/lots", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def _create_pickup_at_handover_stage(collector_headers: dict, recycler_headers: dict, material_id="MAT001") -> tuple[str, str]:
    """
    Helper: creates a lot + pickup and advances the pickup all the way
    to HANDOVER status, returning (lot_id, pickup_id) ready for a
    handover to be recorded.
    """
    lot_id = _create_lot(collector_headers, material_id)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    for next_status in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER"]:
        resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": next_status}, headers=recycler_headers)
        assert resp.status_code == 200, resp.text

    return lot_id, pickup_id


def _get_lot_status(lot_id: str, headers: dict) -> str:
    resp = client.get(f"/api/lots/{lot_id}", headers=headers)
    return resp.json()["data"]["status"]


# ----------------------------------------------------------------
# 13. Handover
# ----------------------------------------------------------------

def test_recycler_can_record_handover():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    payload = {
        "lot_id": lot_id,
        "pickup_id": pickup_id,
        "actual_weight": 5.8,
        "agreed_price": 650,
        "verification_reference": "QR-TEST-001",
    }
    resp = client.post("/api/handovers", json=payload, headers=recycler_headers)
    body = resp.json()
    assert resp.status_code == 201, body
    assert body["data"]["lot_id"] == lot_id
    assert body["data"]["pickup_id"] == pickup_id
    assert body["data"]["verification_reference"] == "QR-TEST-001"


def test_handover_completes_pickup_and_lot():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650},
        headers=recycler_headers,
    )

    pickup_resp = client.get(f"/api/pickups/{pickup_id}", headers=recycler_headers)
    assert pickup_resp.json()["data"]["status"] == "COMPLETED"
    assert _get_lot_status(lot_id, collector_headers) == "COMPLETED"


def test_handover_creates_transaction_automatically():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650},
        headers=recycler_headers,
    )

    resp = client.get("/api/transactions", headers=collector_headers)
    transactions = resp.json()["data"]
    matching = [t for t in transactions if t["lot_id"] == lot_id]
    assert len(matching) == 1
    txn = matching[0]
    assert txn["payment_status"] == "PENDING"
    assert txn["payment_method"] is None
    assert txn["material"] == "Copper"
    assert float(txn["weight"]) == 5.8


def test_only_assigned_recycler_or_admin_can_create_handover():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    # collector tries
    resp = client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650},
        headers=collector_headers,
    )
    assert resp.status_code == 403

    # unrelated recycler tries
    other_recycler_headers = _auth_header(RECYCLER2_EMAIL)
    resp2 = client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650},
        headers=other_recycler_headers,
    )
    assert resp2.status_code == 403


def test_handover_requires_pickup_at_handover_status():
    """A pickup still at REQUESTED (not yet HANDOVER) should reject handover creation."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    resp = client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650},
        headers=recycler_headers,
    )
    body = resp.json()
    assert resp.status_code == 400
    assert body["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_handover_with_nonexistent_pickup_returns_404():
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    resp = client.post(
        "/api/handovers",
        json={"lot_id": "whatever", "pickup_id": "not-a-real-pickup", "actual_weight": 5.8, "agreed_price": 650},
        headers=recycler_headers,
    )
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "PICKUP_NOT_FOUND"


def test_handover_invalid_weight_rejected():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    resp = client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 0, "agreed_price": 650},
        headers=recycler_headers,
    )
    body = resp.json()
    assert resp.status_code == 400
    assert body["error"]["code"] == "INVALID_WEIGHT"


# ----------------------------------------------------------------
# 14. Final amount calculation
# ----------------------------------------------------------------

def test_final_amount_calculated_by_backend():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    resp = client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650},
        headers=recycler_headers,
    )
    body = resp.json()
    # 5.8 * 650 = 3770.00
    assert float(body["data"]["final_amount"]) == 3770.00


def test_client_cannot_supply_final_amount():
    """The schema has no final_amount field -- sending one is simply ignored."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    resp = client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650, "final_amount": 1},
        headers=recycler_headers,
    )
    body = resp.json()
    assert resp.status_code == 201
    assert float(body["data"]["final_amount"]) == 3770.00  # not 1


# ----------------------------------------------------------------
# 15. Duplicate handover
# ----------------------------------------------------------------

def test_duplicate_handover_for_same_lot_rejected():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)

    payload = {"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650}
    first = client.post("/api/handovers", json=payload, headers=recycler_headers)
    assert first.status_code == 201

    # Note: after the first handover, the pickup is already COMPLETED,
    # so a second attempt will actually fail on the status check first
    # (INVALID_STATUS_TRANSITION) rather than reaching the duplicate
    # check -- both are correct rejections of the same underlying
    # situation ("you can't hand this lot over again").
    second = client.post("/api/handovers", json=payload, headers=recycler_headers)
    body = second.json()
    assert second.status_code == 400
    assert body["error"]["code"] in ("HANDOVER_ALREADY_COMPLETED", "INVALID_STATUS_TRANSITION")


# ----------------------------------------------------------------
# GET /api/transactions -- role-based listing
# ----------------------------------------------------------------

def test_collector_sees_only_own_transactions():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_pickup_at_handover_stage(collector_headers, recycler_headers)
    client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 5.8, "agreed_price": 650},
        headers=recycler_headers,
    )

    resp = client.get("/api/transactions", headers=collector_headers)
    body = resp.json()
    assert resp.status_code == 200
    collector_ids = {t["collector_id"] for t in body["data"]}
    assert collector_ids.issubset({resp.json()["data"][0]["collector_id"]}) if body["data"] else True


def test_admin_sees_all_transactions():
    resp = client.get("/api/transactions", headers=_auth_header(ADMIN_EMAIL))
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


def test_transactions_require_auth():
    resp = client.get("/api/transactions")
    assert resp.status_code == 401
