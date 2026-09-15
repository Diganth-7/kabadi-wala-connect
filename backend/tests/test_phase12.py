"""
tests/test_phase12.py
---------------------
Phase 12: final verification and security-focused regression tests.

These tests intentionally exercise the API through FastAPI's TestClient.
They use the real PostgreSQL database configured in .env, just like the
existing test suite.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COLLECTOR_EMAIL = "collector@test.com"
RECYCLER_EMAIL = "recycler@test.com"
ADMIN_EMAIL = "admin@test.com"
COLLECTOR2_EMAIL = "collector2@test.com"


def _auth_header(identifier: str) -> dict:
    login = client.post("/api/auth/login", json={"identifier": identifier})
    assert login.status_code == 200, login.text
    otp = login.json()["data"]["dev_otp"]

    verify = client.post(
        "/api/auth/verify-otp",
        json={"identifier": identifier, "otp": otp},
    )
    assert verify.status_code == 200, verify.text
    return {"Authorization": f"Bearer {verify.json()['data']['access_token']}"}


def _greencycle_id() -> str:
    response = client.get("/api/recyclers")
    assert response.status_code == 200, response.text
    for recycler in response.json()["data"]:
        if recycler["name"] == "GreenCycle Traders":
            return recycler["id"]
    raise AssertionError("GreenCycle Traders not found")


def _create_lot(headers: dict) -> str:
    response = client.post(
        "/api/lots",
        json={
            "material_id": "MAT001",
            "estimated_weight": 6.0,
            "condition": "GOOD",
            "location": {"latitude": 12.9716, "longitude": 77.5946},
            "photo_url": "https://example.com/demo.jpg",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def _create_handover_ready_pickup(collector_headers: dict, recycler_headers: dict) -> tuple[str, str]:
    lot_id = _create_lot(collector_headers)
    response = client.post(
        "/api/pickups",
        json={
            "lot_id": lot_id,
            "recycler_id": _greencycle_id(),
            "pickup_location": {"latitude": 12.9716, "longitude": 77.5946},
        },
        headers=collector_headers,
    )
    assert response.status_code == 201, response.text
    pickup_id = response.json()["data"]["id"]

    for status in ["ACCEPTED", "ASSIGNED", "ON_THE_WAY", "ARRIVED", "HANDOVER"]:
        response = client.patch(
            f"/api/pickups/{pickup_id}/status",
            json={"status": status},
            headers=recycler_headers,
        )
        assert response.status_code == 200, response.text

    return lot_id, pickup_id


# ------------------------------------------------------------------
# API availability / documentation
# ------------------------------------------------------------------

def test_health_endpoint_has_required_envelope():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "healthy"}}


def test_swagger_and_redoc_are_available():
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_openapi_contains_all_major_api_groups():
    paths = client.get("/openapi.json").json()["paths"]
    required_prefixes = [
        "/api/auth",
        "/api/materials",
        "/api/prices",
        "/api/lots",
        "/api/recyclers",
        "/api/pickups",
        "/api/handovers",
        "/api/transactions",
        "/api/payments",
        "/api/earnings",
        "/api/notifications",
        "/api/admin",
    ]
    for prefix in required_prefixes:
        assert any(path.startswith(prefix) for path in paths), f"Missing OpenAPI group: {prefix}"


# ------------------------------------------------------------------
# CORS / standard errors
# ------------------------------------------------------------------

def test_allowed_frontend_origin_is_configured_for_vite():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_disallowed_origin_is_not_granted_cors_access():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "http://evil.example"


def test_invalid_json_request_uses_standard_error_envelope():
    response = client.post("/api/lots", json={})
    body = response.json()
    assert response.status_code == 422
    assert body["success"] is False
    assert set(body["error"].keys()) == {"code", "message"}
    assert "detail" not in body


def test_malformed_token_does_not_expose_internal_details():
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer definitely-not-a-valid-jwt"},
    )
    body = response.json()
    assert response.status_code == 401
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert "Traceback" not in response.text


# ------------------------------------------------------------------
# Backend source-of-truth price validation
# ------------------------------------------------------------------

def test_handover_rejects_price_below_backend_minimum():
    collector = _auth_header(COLLECTOR_EMAIL)
    recycler = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_handover_ready_pickup(collector, recycler)

    response = client.post(
        "/api/handovers",
        json={
            "lot_id": lot_id,
            "pickup_id": pickup_id,
            "actual_weight": 5.8,
            "agreed_price": 599,
        },
        headers=recycler,
    )
    body = response.json()
    assert response.status_code == 400
    assert body["error"]["code"] == "INVALID_PRICE"


def test_handover_rejects_price_above_backend_maximum():
    collector = _auth_header(COLLECTOR2_EMAIL)
    recycler = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_handover_ready_pickup(collector, recycler)

    response = client.post(
        "/api/handovers",
        json={
            "lot_id": lot_id,
            "pickup_id": pickup_id,
            "actual_weight": 5.8,
            "agreed_price": 701,
        },
        headers=recycler,
    )
    body = response.json()
    assert response.status_code == 400
    assert body["error"]["code"] == "INVALID_PRICE"


def test_handover_accepts_price_inside_backend_range():
    collector = _auth_header(COLLECTOR2_EMAIL)
    recycler = _auth_header(RECYCLER_EMAIL)
    lot_id, pickup_id = _create_handover_ready_pickup(collector, recycler)

    response = client.post(
        "/api/handovers",
        json={
            "lot_id": lot_id,
            "pickup_id": pickup_id,
            "actual_weight": 5.8,
            "agreed_price": 650,
        },
        headers=recycler,
    )
    assert response.status_code == 201, response.text
    assert float(response.json()["data"]["final_amount"]) == 3770.0


# ------------------------------------------------------------------
# IDOR / role isolation regression checks
# ------------------------------------------------------------------

def test_collector_cannot_view_another_collectors_lot():
    collector = _auth_header(COLLECTOR_EMAIL)
    other_collector = _auth_header(COLLECTOR2_EMAIL)
    lot_id = _create_lot(collector)

    response = client.get(f"/api/lots/{lot_id}", headers=other_collector)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_collector_cannot_access_admin_dashboard():
    collector = _auth_header(COLLECTOR_EMAIL)
    response = client.get("/api/admin/dashboard", headers=collector)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_recycler_cannot_access_admin_dashboard():
    recycler = _auth_header(RECYCLER_EMAIL)
    response = client.get("/api/admin/dashboard", headers=recycler)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_access_admin_dashboard():
    admin = _auth_header(ADMIN_EMAIL)
    response = client.get("/api/admin/dashboard", headers=admin)
    assert response.status_code == 200
    assert response.json()["success"] is True
