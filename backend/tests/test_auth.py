"""
tests/test_auth.py
-------------------
Tests covering:
  1. Login (OTP request)
  2. OTP verification
  3. JWT authentication (/me with/without/invalid token)
  4. Role-based authorization (require_role dependency)

These use FastAPI's TestClient, which runs the app in-process (no need
to have `uvicorn` running separately) but talks to your REAL database
configured in .env — so make sure PostgreSQL is running and you've run
`python scripts/seed.py` before running these tests.

Run with:
    pytest tests/test_auth.py -v
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import auth_service
from app.auth.dependencies import require_role
from app.utils.errors import AppError
from app.models.user import UserRole

client = TestClient(app)

# Matches scripts/seed.py demo data.
COLLECTOR_EMAIL = "collector@test.com"
RECYCLER_EMAIL = "recycler@test.com"
ADMIN_EMAIL = "admin@test.com"
UNKNOWN_EMAIL = "nobody-should-exist@test.com"


def _login_and_get_otp(identifier: str) -> str:
    """Helper: calls /login and pulls the dev_otp out of the response."""
    resp = client.post("/api/auth/login", json={"identifier": identifier})
    assert resp.status_code == 200
    return resp.json()["data"]["dev_otp"]


def _login_and_get_token(identifier: str) -> str:
    """Helper: full login -> verify-otp flow, returns a usable JWT."""
    otp = _login_and_get_otp(identifier)
    resp = client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


# ----------------------------------------------------------------
# 1. Login (OTP request)
# ----------------------------------------------------------------

def test_login_known_user_returns_otp():
    resp = client.post("/api/auth/login", json={"identifier": COLLECTOR_EMAIL})
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert "dev_otp" in body["data"]
    assert len(body["data"]["dev_otp"]) == 6


def test_login_unknown_user_returns_404():
    resp = client.post("/api/auth/login", json={"identifier": UNKNOWN_EMAIL})
    body = resp.json()
    assert resp.status_code == 404
    assert body["success"] is False
    assert body["error"]["code"] == "USER_NOT_FOUND"


def test_login_missing_identifier_returns_422():
    resp = client.post("/api/auth/login", json={})
    body = resp.json()
    assert resp.status_code == 422
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


# ----------------------------------------------------------------
# 2. OTP verification
# ----------------------------------------------------------------

def test_verify_correct_otp_succeeds():
    otp = _login_and_get_otp(COLLECTOR_EMAIL)
    resp = client.post("/api/auth/verify-otp", json={"identifier": COLLECTOR_EMAIL, "otp": otp})
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert body["data"]["user"]["email"] == COLLECTOR_EMAIL


def test_verify_wrong_otp_fails():
    _login_and_get_otp(COLLECTOR_EMAIL)  # generates and stores a real OTP
    resp = client.post("/api/auth/verify-otp", json={"identifier": COLLECTOR_EMAIL, "otp": "000000"})
    body = resp.json()
    assert resp.status_code == 401
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_otp_cannot_be_reused():
    otp = _login_and_get_otp(COLLECTOR_EMAIL)
    first = client.post("/api/auth/verify-otp", json={"identifier": COLLECTOR_EMAIL, "otp": otp})
    assert first.status_code == 200

    second = client.post("/api/auth/verify-otp", json={"identifier": COLLECTOR_EMAIL, "otp": otp})
    assert second.status_code == 401
    assert second.json()["error"]["code"] == "UNAUTHORIZED"


def test_verify_otp_without_requesting_login_first_fails():
    resp = client.post("/api/auth/verify-otp", json={"identifier": "someone-who-never-logged-in@test.com", "otp": "123456"})
    assert resp.status_code == 401


# ----------------------------------------------------------------
# 3. JWT authentication
# ----------------------------------------------------------------

def test_me_with_valid_token_succeeds():
    token = _login_and_get_token(COLLECTOR_EMAIL)
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["email"] == COLLECTOR_EMAIL
    assert body["data"]["role"] == "COLLECTOR"


def test_me_without_token_fails_401():
    resp = client.get("/api/auth/me")
    body = resp.json()
    assert resp.status_code == 401
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_me_with_malformed_token_fails_401():
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    body = resp.json()
    assert resp.status_code == 401
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_no_stack_trace_ever_leaks_in_error_response():
    """
    Spot-check: no error response anywhere should contain typical
    Python traceback markers, per the "never expose stack traces" rule.
    """
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    text = resp.text
    assert "Traceback" not in text
    assert ".py\"" not in text


# ----------------------------------------------------------------
# 4. Role-based authorization
# ----------------------------------------------------------------
# There's no role-restricted ROUTE yet (that starts with /api/admin/*
# in Phase 11), so these test the `require_role` dependency directly —
# the actual mechanism every future protected route will rely on.

def test_require_role_allows_matching_role():
    dependency = require_role(UserRole.ADMIN)

    class FakeUser:
        role = UserRole.ADMIN

    result = dependency(current_user=FakeUser())
    assert result is not None


def test_require_role_blocks_non_matching_role():
    dependency = require_role(UserRole.ADMIN)

    class FakeUser:
        role = UserRole.COLLECTOR

    with pytest.raises(AppError) as exc_info:
        dependency(current_user=FakeUser())

    assert exc_info.value.code == "FORBIDDEN"
    assert exc_info.value.status_code == 403


def test_require_role_allows_multiple_roles():
    dependency = require_role(UserRole.ADMIN, UserRole.RECYCLER)

    class FakeUser:
        role = UserRole.RECYCLER

    result = dependency(current_user=FakeUser())
    assert result is not None
