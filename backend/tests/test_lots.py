"""
tests/test_lots.py
--------------------
Tests covering:
  7. Lot creation
  8. Invalid weight
  9. Invalid material
  (plus: role authorization, ownership isolation, backend-calculated
  value, and rejecting client-supplied estimated_value/collector_id)

Requires PostgreSQL running with seed data loaded.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COLLECTOR_EMAIL = "collector@test.com"
COLLECTOR2_EMAIL = "collector2@test.com"
RECYCLER_EMAIL = "recycler@test.com"
ADMIN_EMAIL = "admin@test.com"

VALID_LOT_PAYLOAD = {
    "material_id": "MAT001",  # Copper, current_price = 650 (see scripts/seed.py)
    "estimated_weight": 10.0,
    "condition": "GOOD",
    "location": {"latitude": 12.9716, "longitude": 77.5946},
    "photo_url": "https://example.com/photo.jpg",
}


def _get_token(identifier: str) -> str:
    login_resp = client.post("/api/auth/login", json={"identifier": identifier})
    otp = login_resp.json()["data"]["dev_otp"]
    verify_resp = client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp})
    return verify_resp.json()["data"]["access_token"]


def _auth_header(identifier: str) -> dict:
    return {"Authorization": f"Bearer {_get_token(identifier)}"}


# ----------------------------------------------------------------
# 7. Lot creation
# ----------------------------------------------------------------

def test_collector_can_create_lot():
    resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 201
    assert body["success"] is True
    assert body["data"]["material_id"] == "MAT001"
    assert body["data"]["status"] == "CREATED"


def test_estimated_value_is_calculated_by_backend():
    resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    # 10.0 kg * 650 (MAT001 current_price from seed data) = 6500.00
    assert float(body["data"]["estimated_value"]) == 6500.00


def test_client_cannot_supply_estimated_value():
    """Even if the client tries to send estimated_value, it's ignored/rejected -- the schema doesn't accept it."""
    payload = dict(VALID_LOT_PAYLOAD, estimated_value=1)
    resp = client.post("/api/lots", json=payload, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    # extra field is simply ignored by pydantic (not an error) -- the
    # important check is that the resulting value is still backend-calculated.
    assert resp.status_code == 201
    assert float(body["data"]["estimated_value"]) == 6500.00  # not 1


def test_client_cannot_supply_collector_id():
    """The lot's collector_id always comes from the JWT, not the request body."""
    payload = dict(VALID_LOT_PAYLOAD, collector_id="some-other-user-id")
    resp = client.post("/api/lots", json=payload, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 201
    assert body["data"]["collector_id"] != "some-other-user-id"


def test_lot_location_is_nested_correctly():
    resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert body["data"]["location"]["latitude"] == 12.9716
    assert body["data"]["location"]["longitude"] == 77.5946


def test_only_collector_can_create_lots():
    resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(RECYCLER_EMAIL))
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_admin_cannot_create_lots():
    resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(ADMIN_EMAIL))
    assert resp.status_code == 403


def test_create_lot_without_auth_fails():
    resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD)
    assert resp.status_code == 401


# ----------------------------------------------------------------
# 8. Invalid weight
# ----------------------------------------------------------------

def test_zero_weight_rejected():
    payload = dict(VALID_LOT_PAYLOAD, estimated_weight=0)
    resp = client.post("/api/lots", json=payload, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 400
    assert body["error"]["code"] == "INVALID_WEIGHT"


def test_negative_weight_rejected():
    payload = dict(VALID_LOT_PAYLOAD, estimated_weight=-5)
    resp = client.post("/api/lots", json=payload, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 400
    assert body["error"]["code"] == "INVALID_WEIGHT"


# ----------------------------------------------------------------
# 9. Invalid material
# ----------------------------------------------------------------

def test_invalid_material_rejected():
    payload = dict(VALID_LOT_PAYLOAD, material_id="NOT_REAL")
    resp = client.post("/api/lots", json=payload, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "INVALID_MATERIAL"


def test_invalid_condition_rejected():
    payload = dict(VALID_LOT_PAYLOAD, condition="SUPER_DAMAGED")
    resp = client.post("/api/lots", json=payload, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_missing_required_field_rejected():
    payload = {"material_id": "MAT001"}  # missing weight, condition, location
    resp = client.post("/api/lots", json=payload, headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 422
    assert body["error"]["code"] == "VALIDATION_ERROR"


# ----------------------------------------------------------------
# GET /api/lots and /api/lots/{id} -- ownership & authorization
# ----------------------------------------------------------------

def test_collector_sees_only_own_lots():
    client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    resp = client.get("/api/lots", headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 200
    collector_ids = {lot["collector_id"] for lot in body["data"]}
    assert len(collector_ids) <= 1  # all lots belong to the same (this) collector


def test_admin_sees_all_lots():
    client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    resp = client.get("/api/lots", headers=_auth_header(ADMIN_EMAIL))
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["data"]) >= 1


def test_recycler_cannot_list_all_lots():
    resp = client.get("/api/lots", headers=_auth_header(RECYCLER_EMAIL))
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_collector_cannot_view_another_collectors_lot():
    """This is the exact scenario from the spec: never access another user's
    resource just by changing an ID in the URL."""
    create_resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    lot_id = create_resp.json()["data"]["id"]

    resp = client.get(f"/api/lots/{lot_id}", headers=_auth_header(COLLECTOR2_EMAIL))
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_collector_can_view_own_lot():
    create_resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    lot_id = create_resp.json()["data"]["id"]

    resp = client.get(f"/api/lots/{lot_id}", headers=_auth_header(COLLECTOR_EMAIL))
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == lot_id


def test_admin_can_view_any_lot():
    create_resp = client.post("/api/lots", json=VALID_LOT_PAYLOAD, headers=_auth_header(COLLECTOR_EMAIL))
    lot_id = create_resp.json()["data"]["id"]

    resp = client.get(f"/api/lots/{lot_id}", headers=_auth_header(ADMIN_EMAIL))
    assert resp.status_code == 200


def test_get_nonexistent_lot_returns_404():
    resp = client.get("/api/lots/not-a-real-id", headers=_auth_header(COLLECTOR_EMAIL))
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "LOT_NOT_FOUND"
