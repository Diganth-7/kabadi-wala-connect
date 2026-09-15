"""
tests/test_admin.py
----------------------
Tests covering:
  20. Admin authorization

Plus dashboard correctness (computed, not hard-coded), listing
endpoints, and the recycler authorization toggle.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COLLECTOR_EMAIL = "collector@test.com"
RECYCLER_EMAIL = "recycler@test.com"
ADMIN_EMAIL = "admin@test.com"

ADMIN_ENDPOINTS = [
    ("GET", "/api/admin/dashboard"),
    ("GET", "/api/admin/collectors"),
    ("GET", "/api/admin/recyclers"),
    ("GET", "/api/admin/transactions"),
]


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


# ----------------------------------------------------------------
# 20. Admin authorization
# ----------------------------------------------------------------

def test_admin_can_access_all_admin_endpoints():
    admin_headers = _auth_header(ADMIN_EMAIL)
    for method, path in ADMIN_ENDPOINTS:
        resp = client.request(method, path, headers=admin_headers)
        assert resp.status_code == 200, f"{method} {path} failed: {resp.text}"
        assert resp.json()["success"] is True


def test_collector_blocked_from_all_admin_endpoints():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    for method, path in ADMIN_ENDPOINTS:
        resp = client.request(method, path, headers=collector_headers)
        body = resp.json()
        assert resp.status_code == 403, f"{method} {path} should be 403, got {resp.status_code}"
        assert body["error"]["code"] == "FORBIDDEN"


def test_recycler_blocked_from_all_admin_endpoints():
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    for method, path in ADMIN_ENDPOINTS:
        resp = client.request(method, path, headers=recycler_headers)
        body = resp.json()
        assert resp.status_code == 403, f"{method} {path} should be 403, got {resp.status_code}"
        assert body["error"]["code"] == "FORBIDDEN"


def test_unauthenticated_blocked_from_all_admin_endpoints():
    for method, path in ADMIN_ENDPOINTS:
        resp = client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should be 401, got {resp.status_code}"


def test_recycler_authorization_update_requires_admin():
    recycler_id = _greencycle_id()

    collector_resp = client.patch(
        f"/api/admin/recyclers/{recycler_id}/authorization",
        json={"authorized": False},
        headers=_auth_header(COLLECTOR_EMAIL),
    )
    assert collector_resp.status_code == 403

    recycler_resp = client.patch(
        f"/api/admin/recyclers/{recycler_id}/authorization",
        json={"authorized": False},
        headers=_auth_header(RECYCLER_EMAIL),
    )
    assert recycler_resp.status_code == 403


# ----------------------------------------------------------------
# Dashboard correctness
# ----------------------------------------------------------------

def test_dashboard_has_all_required_fields():
    resp = client.get("/api/admin/dashboard", headers=_auth_header(ADMIN_EMAIL))
    data = resp.json()["data"]
    for key in [
        "total_collectors", "active_collectors", "authorized_recyclers",
        "total_ewaste_kg", "total_transactions", "total_transaction_value",
    ]:
        assert key in data


def test_dashboard_matches_seed_data_minimums():
    """Seed data has 3 collectors, 2 authorized recyclers, at least 1 transaction."""
    resp = client.get("/api/admin/dashboard", headers=_auth_header(ADMIN_EMAIL))
    data = resp.json()["data"]
    assert data["total_collectors"] >= 3
    assert data["active_collectors"] >= 3
    assert data["authorized_recyclers"] >= 2
    assert data["total_transactions"] >= 1


def test_dashboard_reflects_new_transaction():
    """Dashboard totals change after new activity -- proves it's computed live, not hard-coded."""
    admin_headers = _auth_header(ADMIN_EMAIL)
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)

    before = client.get("/api/admin/dashboard", headers=admin_headers).json()["data"]

    lot_resp = client.post(
        "/api/lots",
        json={
            "material_id": "MAT001", "estimated_weight": 3.0, "condition": "GOOD",
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
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 3.0, "agreed_price": 650},
        headers=recycler_headers,
    )

    after = client.get("/api/admin/dashboard", headers=admin_headers).json()["data"]

    assert after["total_transactions"] == before["total_transactions"] + 1
    assert after["total_ewaste_kg"] - before["total_ewaste_kg"] == 3.0
    assert float(after["total_transaction_value"]) - float(before["total_transaction_value"]) == 1950.0  # 3.0 * 650


# ----------------------------------------------------------------
# Recycler authorization toggle
# ----------------------------------------------------------------

def test_admin_can_toggle_recycler_authorization():
    admin_headers = _auth_header(ADMIN_EMAIL)
    recycler_id = _greencycle_id()

    resp = client.patch(
        f"/api/admin/recyclers/{recycler_id}/authorization",
        json={"authorized": False},
        headers=admin_headers,
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["authorized"] is False

    # restore it, so we don't break other tests that rely on GreenCycle being authorized
    restore = client.patch(
        f"/api/admin/recyclers/{recycler_id}/authorization",
        json={"authorized": True},
        headers=admin_headers,
    )
    assert restore.json()["data"]["authorized"] is True


def test_authorization_toggle_nonexistent_recycler_returns_404():
    resp = client.patch(
        "/api/admin/recyclers/not-a-real-id/authorization",
        json={"authorized": True},
        headers=_auth_header(ADMIN_EMAIL),
    )
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "RECYCLER_NOT_FOUND"


# ----------------------------------------------------------------
# Listing endpoints return sensible data
# ----------------------------------------------------------------

def test_admin_collectors_list_only_contains_collectors():
    resp = client.get("/api/admin/collectors", headers=_auth_header(ADMIN_EMAIL))
    data = resp.json()["data"]
    assert len(data) >= 3
    assert all(c["role"] == "COLLECTOR" for c in data)


def test_admin_transactions_list_matches_regular_admin_view():
    """/api/admin/transactions and /api/transactions (as admin) should return the same data."""
    admin_headers = _auth_header(ADMIN_EMAIL)
    admin_endpoint = client.get("/api/admin/transactions", headers=admin_headers).json()["data"]
    regular_endpoint = client.get("/api/transactions", headers=admin_headers).json()["data"]
    assert len(admin_endpoint) == len(regular_endpoint)
