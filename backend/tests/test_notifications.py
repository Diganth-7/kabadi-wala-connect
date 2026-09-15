"""
tests/test_notifications.py
------------------------------
Tests covering:
  19. Notifications

Checks that all 5 spec-listed events actually generate a notification
(pickup accepted, pickup rejected, pickup arriving, handover completed,
payment recorded), plus listing/read-marking access control.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COLLECTOR_EMAIL = "collector@test.com"
COLLECTOR2_EMAIL = "collector2@test.com"
RECYCLER_EMAIL = "recycler@test.com"  # manages GreenCycle Traders


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


def _create_lot_and_pickup(collector_headers: dict) -> tuple[str, str]:
    lot_resp = client.post(
        "/api/lots",
        json={
            "material_id": "MAT001", "estimated_weight": 5.0, "condition": "GOOD",
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
    return lot_id, pickup_id


def _latest_notification_type(collector_headers: dict) -> str:
    resp = client.get("/api/notifications", headers=collector_headers)
    return resp.json()["data"][0]["type"]  # most recent first


# ----------------------------------------------------------------
# 19. Notifications
# ----------------------------------------------------------------

def test_pickup_accepted_generates_notification():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    _, pickup_id = _create_lot_and_pickup(collector_headers)

    client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ACCEPTED"}, headers=recycler_headers)

    assert _latest_notification_type(collector_headers) == "PICKUP_ACCEPTED"


def test_pickup_rejected_generates_notification():
    """Cancelling straight from REQUESTED reads as a rejection."""
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    _, pickup_id = _create_lot_and_pickup(collector_headers)

    client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "CANCELLED"}, headers=recycler_headers)

    assert _latest_notification_type(collector_headers) == "PICKUP_REJECTED"


def test_pickup_arriving_generates_notification():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    _, pickup_id = _create_lot_and_pickup(collector_headers)

    for s in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY"]:
        client.patch(f"/api/pickups/{pickup_id}/status", json={"status": s}, headers=recycler_headers)

    assert _latest_notification_type(collector_headers) == "PICKUP_ARRIVING"


def test_handover_completed_generates_notification():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_lot_and_pickup(collector_headers)

    for s in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER"]:
        client.patch(f"/api/pickups/{pickup_id}/status", json={"status": s}, headers=recycler_headers)

    client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 4.8, "agreed_price": 650},
        headers=recycler_headers,
    )

    assert _latest_notification_type(collector_headers) == "HANDOVER_COMPLETED"


def test_payment_recorded_generates_notification():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_lot_and_pickup(collector_headers)

    for s in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER"]:
        client.patch(f"/api/pickups/{pickup_id}/status", json={"status": s}, headers=recycler_headers)

    client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 4.8, "agreed_price": 650},
        headers=recycler_headers,
    )
    txns = client.get("/api/transactions", headers=collector_headers).json()["data"]
    txn_id = next(t for t in txns if t["lot_id"] == lot_id)["id"]

    client.post("/api/payments", json={"transaction_id": txn_id, "method": "UPI"}, headers=recycler_headers)

    assert _latest_notification_type(collector_headers) == "PAYMENT_RECORDED"


def test_failed_payment_does_not_generate_payment_recorded_notification():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_lot_and_pickup(collector_headers)

    for s in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER"]:
        client.patch(f"/api/pickups/{pickup_id}/status", json={"status": s}, headers=recycler_headers)

    client.post(
        "/api/handovers",
        json={"lot_id": lot_id, "pickup_id": pickup_id, "actual_weight": 4.8, "agreed_price": 650},
        headers=recycler_headers,
    )
    txns = client.get("/api/transactions", headers=collector_headers).json()["data"]
    txn_id = next(t for t in txns if t["lot_id"] == lot_id)["id"]

    client.post(
        "/api/payments",
        json={"transaction_id": txn_id, "method": "UPI", "simulate_failure": True},
        headers=recycler_headers,
    )

    # Latest notification should still be the handover one, not a
    # "payment recorded" notification for a payment that failed.
    assert _latest_notification_type(collector_headers) == "HANDOVER_COMPLETED"


# ----------------------------------------------------------------
# List / mark-as-read access control
# ----------------------------------------------------------------

def test_list_notifications_requires_auth():
    resp = client.get("/api/notifications")
    assert resp.status_code == 401


def test_user_only_sees_own_notifications():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    _, pickup_id = _create_lot_and_pickup(collector_headers)
    client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ACCEPTED"}, headers=recycler_headers)

    other_headers = _auth_header(COLLECTOR2_EMAIL)
    resp = client.get("/api/notifications", headers=other_headers)
    body = resp.json()
    assert resp.status_code == 200
    # collector2 shouldn't see collector's notification
    assert all(n["user_id"] != "" for n in body["data"])  # sanity: has user_id
    resp_own = client.get("/api/notifications", headers=collector_headers)
    own_ids = {n["id"] for n in resp_own.json()["data"]}
    other_ids = {n["id"] for n in body["data"]}
    assert own_ids.isdisjoint(other_ids)


def test_mark_notification_as_read():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    _, pickup_id = _create_lot_and_pickup(collector_headers)
    client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ACCEPTED"}, headers=recycler_headers)

    notifications = client.get("/api/notifications", headers=collector_headers).json()["data"]
    unread = next(n for n in notifications if not n["read"])

    resp = client.patch(f"/api/notifications/{unread['id']}/read", headers=collector_headers)
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["read"] is True


def test_cannot_mark_someone_elses_notification_as_read():
    collector_headers = _auth_header(COLLECTOR_EMAIL)
    recycler_headers = _auth_header(RECYCLER_EMAIL)
    _, pickup_id = _create_lot_and_pickup(collector_headers)
    client.patch(f"/api/pickups/{pickup_id}/status", json={"status": "ACCEPTED"}, headers=recycler_headers)

    notifications = client.get("/api/notifications", headers=collector_headers).json()["data"]
    notification_id = notifications[0]["id"]

    other_headers = _auth_header(COLLECTOR2_EMAIL)
    resp = client.patch(f"/api/notifications/{notification_id}/read", headers=other_headers)
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_mark_nonexistent_notification_returns_404():
    resp = client.patch("/api/notifications/not-a-real-id/read", headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "NOTIFICATION_NOT_FOUND"
