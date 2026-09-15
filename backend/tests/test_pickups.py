"""
tests/test_pickups.py
-----------------------
Tests covering:
  11. Pickup creation
  12. Invalid pickup transition

Plus: the full valid transition flow, cancellation + lot status revert,
and authorization (only the assigned recycler or admin can update status).

Requires PostgreSQL running with seed data loaded. Seed data recap:
  - recycler@test.com manages "GreenCycle Traders" (accepts Copper etc.)
  - recycler2@test.com manages "EcoScrap Solutions" (accepts LCD etc.)
"""

import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.recycler import Recycler
from app.models.user import User, UserRole

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


def _get_recycler_id_by_name(name: str) -> str:
    resp = client.get("/api/recyclers")
    for r in resp.json()["data"]:
        if r["name"] == name:
            return r["id"]
    raise AssertionError(f"Recycler '{name}' not found in seed data")


def _create_lot(headers: dict, material_id="MAT001", lat=12.9716, lng=77.5946) -> str:
    payload = {
        "material_id": material_id,
        "estimated_weight": 6.0,
        "condition": "GOOD",
        "location": {"latitude": lat, "longitude": lng},
        "photo_url": "https://example.com/p.jpg",
    }
    resp = client.post("/api/lots", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def _get_lot_status(lot_id: str, headers: dict) -> str:
    resp = client.get(f"/api/lots/{lot_id}", headers=headers)
    return resp.json()["data"]["status"]


GREENCYCLE_ID = None  # resolved lazily in first test that needs it


def _greencycle_id() -> str:
    global GREENCYCLE_ID
    if GREENCYCLE_ID is None:
        GREENCYCLE_ID = _get_recycler_id_by_name("GreenCycle Traders")
    return GREENCYCLE_ID


# ----------------------------------------------------------------
# 11. Pickup creation
# ----------------------------------------------------------------

def test_collector_can_create_pickup_for_own_lot():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot(collector_headers)

    payload = {
        "lot_id": lot_id,
        "recycler_id": _greencycle_id(),
        "pickup_location": {"latitude": 12.9716, "longitude": 77.5946},
    }
    resp = client.post("/api/pickups", json=payload, headers=collector_headers)
    body = resp.json()
    assert resp.status_code == 201
    assert body["data"]["status"] == "REQUESTED"
    assert body["data"]["lot_id"] == lot_id


def test_creating_pickup_moves_lot_to_pickup_requested():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot(collector_headers)

    payload = {
        "lot_id": lot_id,
        "recycler_id": _greencycle_id(),
        "pickup_location": {"latitude": 12.9716, "longitude": 77.5946},
    }
    client.post("/api/pickups", json=payload, headers=collector_headers)

    assert _get_lot_status(lot_id, collector_headers) == "PICKUP_REQUESTED"


def test_cannot_create_pickup_for_someone_elses_lot():
    owner_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot(owner_headers)

    other_headers = _auth_header(COLLECTOR2_EMAIL)
    payload = {
        "lot_id": lot_id,
        "recycler_id": _greencycle_id(),
        "pickup_location": {"latitude": 12.9716, "longitude": 77.5946},
    }
    resp = client.post("/api/pickups", json=payload, headers=other_headers)
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_cannot_create_duplicate_pickup_for_same_lot():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot(collector_headers)

    payload = {
        "lot_id": lot_id,
        "recycler_id": _greencycle_id(),
        "pickup_location": {"latitude": 12.9716, "longitude": 77.5946},
    }
    first = client.post("/api/pickups", json=payload, headers=collector_headers)
    assert first.status_code == 201

    second = client.post("/api/pickups", json=payload, headers=collector_headers)
    body = second.json()
    assert second.status_code == 400
    assert body["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_recycler_cannot_create_pickups():
    resp = client.post(
        "/api/pickups",
        json={"lot_id": "whatever", "recycler_id": "whatever", "pickup_location": {"latitude": 0, "longitude": 0}},
        headers=_auth_header(RECYCLER_EMAIL),
    )
    assert resp.status_code == 403


def test_create_pickup_for_nonexistent_lot_returns_404():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    payload = {
        "lot_id": "not-a-real-lot",
        "recycler_id": _greencycle_id(),
        "pickup_location": {"latitude": 12.9716, "longitude": 77.5946},
    }
    resp = client.post("/api/pickups", json=payload, headers=collector_headers)
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "LOT_NOT_FOUND"


def test_create_pickup_with_unauthorized_recycler_rejected():
    """Uses a direct DB insert to create an unauthorized recycler, since seed data has none."""
    db = SessionLocal()
    temp_user_id = None
    unauthorized_recycler_id = None
    try:
        temp_user = User(
            id=str(uuid.uuid4()), email=f"temp-{uuid.uuid4()}@test.com", name="Temp Recycler",
            role=UserRole.RECYCLER, is_active=True,
        )
        db.add(temp_user)
        db.commit()
        temp_user_id = temp_user.id

        unauthorized_recycler = Recycler(
            id=str(uuid.uuid4()), user_id=temp_user.id, name="Sketchy Scrap Co",
            authorized=False, latitude=12.9716, longitude=77.5946,
            service_radius_km=50.0, pickup_available=True, reliability_score=1.0,
        )
        db.add(unauthorized_recycler)
        db.commit()
        unauthorized_recycler_id = unauthorized_recycler.id

        collector_headers = _auth_header(COLLECTOR_EMAIL)
        lot_id = _create_lot(collector_headers)

        payload = {
            "lot_id": lot_id,
            "recycler_id": unauthorized_recycler_id,
            "pickup_location": {"latitude": 12.9716, "longitude": 77.5946},
        }
        resp = client.post("/api/pickups", json=payload, headers=collector_headers)
        body = resp.json()
        assert resp.status_code == 403
        assert body["error"]["code"] == "UNAUTHORIZED_RECYCLER"
    finally:
        # Clean up so this doesn't pollute other tests that count recyclers/users
        # (e.g. tests/test_recyclers.py expects exactly the 2 seeded recyclers).
        if unauthorized_recycler_id:
            db.query(Recycler).filter(Recycler.id == unauthorized_recycler_id).delete()
        if temp_user_id:
            db.query(User).filter(User.id == temp_user_id).delete()
        db.commit()
        db.close()


# ----------------------------------------------------------------
# Full valid transition flow
# ----------------------------------------------------------------

def test_full_valid_pickup_flow_completes_and_completes_lot():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)  # manages GreenCycle Traders

    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    flow = ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER", "COMPLETED"]
    for next_status in flow:
        resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": next_status}, headers=recycler_headers)
        body = resp.json()
        assert resp.status_code == 200, f"failed at {next_status}: {body}"
        assert body["data"]["status"] == next_status

    assert _get_lot_status(lot_id, collector_headers) == "COMPLETED"


# ----------------------------------------------------------------
# 12. Invalid pickup transition
# ----------------------------------------------------------------

def test_completed_to_requested_transition_fails():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)

    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    for next_status in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER", "COMPLETED"]:
        client.patch(f"/api/pickups/{pickup_id}/status", json={"status": next_status}, headers=recycler_headers)

    resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "REQUESTED"}, headers=recycler_headers)
    body = resp.json()
    assert resp.status_code == 400
    assert body["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_skipping_a_step_fails():
    """REQUESTED -> ON_THE_WAY (skipping ACCEPTED, ASSIGNED) should fail."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)

    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ON_THE_WAY"}, headers=recycler_headers)
    body = resp.json()
    assert resp.status_code == 400
    assert body["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_cancellation_reverts_lot_to_created():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)

    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "CANCELLED"}, headers=recycler_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "CANCELLED"

    assert _get_lot_status(lot_id, collector_headers) == "CREATED"


def test_cannot_cancel_after_arrived():
    """ARRIVED only allows -> HANDOVER, cancellation is no longer possible."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)

    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    for next_status in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED"]:
        client.patch(f"/api/pickups/{pickup_id}/status", json={"status": next_status}, headers=recycler_headers)

    resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "CANCELLED"}, headers=recycler_headers)
    body = resp.json()
    assert resp.status_code == 400
    assert body["error"]["code"] == "INVALID_STATUS_TRANSITION"


# ----------------------------------------------------------------
# Authorization
# ----------------------------------------------------------------

def test_collector_cannot_update_pickup_status():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ACCEPTED"}, headers=collector_headers)
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_unassigned_recycler_cannot_update_pickup_status():
    """recycler2 (EcoScrap) should not be able to update a pickup assigned to GreenCycle."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    other_recycler_headers = _auth_header(RECYCLER2_EMAIL)
    resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ACCEPTED"}, headers=other_recycler_headers)
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_admin_can_update_pickup_status():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    admin_headers = _auth_header(ADMIN_EMAIL)
    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    resp = client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ACCEPTED"}, headers=admin_headers)
    assert resp.status_code == 200


def test_collector_cannot_view_another_collectors_pickup():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    other_headers = _auth_header(COLLECTOR2_EMAIL)
    resp = client.get(f"/api/pickups/{pickup_id}", headers=other_headers)
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_assigned_recycler_can_view_pickup():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id = _create_lot(collector_headers)
    create_resp = client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )
    pickup_id = create_resp.json()["data"]["id"]

    resp = client.get(f"/api/pickups/{pickup_id}", headers=recycler_headers)
    assert resp.status_code == 200


def test_get_nonexistent_pickup_returns_404():
    resp = client.get("/api/pickups/not-a-real-id", headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "PICKUP_NOT_FOUND"


def test_recycler_list_only_shows_their_own_pickups():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id = _create_lot(collector_headers)
    client.post(
        "/api/pickups",
        json={"lot_id": lot_id, "recycler_id": _greencycle_id(), "pickup_location": {"latitude": 12.9716, "longitude": 77.5946}},
        headers=collector_headers,
    )

    resp = client.get("/api/pickups", headers=recycler_headers)
    body = resp.json()
    assert resp.status_code == 200
    assert all(p["recycler_id"] == _greencycle_id() for p in body["data"])
