"""
tests/test_recyclers.py
-------------------------
Tests covering:
  10. Recycler matching

Plus listing/retrieval and authorization-filtering checks.

Requires PostgreSQL running with seed data loaded. Seed data recap
(scripts/seed.py):
  - GreenCycle Traders: authorized, accepts Copper/Aluminium/PCB/Cable,
    location ~ (12.9716, 77.5946), radius 15km
  - EcoScrap Solutions: authorized, accepts LCD/CRT/Battery/Plastic/Other,
    location ~ (12.9352, 77.6146), radius 10km
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COLLECTOR_EMAIL = "collector@test.com"
COLLECTOR2_EMAIL = "collector2@test.com"
ADMIN_EMAIL = "admin@test.com"


def _auth_header(identifier: str) -> dict:
    login_resp = client.post("/api/auth/login", json={"identifier": identifier})
    otp = login_resp.json()["data"]["dev_otp"]
    verify_resp = client.post("/api/auth/verify-otp", json={"identifier": identifier, "otp": otp})
    token = verify_resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_lot(material_id: str, headers: dict, lat=12.9716, lng=77.5946) -> str:
    payload = {
        "material_id": material_id,
        "estimated_weight": 8.0,
        "condition": "GOOD",
        "location": {"latitude": lat, "longitude": lng},
        "photo_url": "https://example.com/p.jpg",
    }
    resp = client.post("/api/lots", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


# ----------------------------------------------------------------
# Listing / retrieval
# ----------------------------------------------------------------

def test_list_recyclers_returns_seeded_two():
    resp = client.get("/api/recyclers")
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["data"]) == 2


def test_recycler_fields_present():
    resp = client.get("/api/recyclers")
    recycler = resp.json()["data"][0]
    expected_fields = {
        "id", "name", "authorized", "location", "service_radius_km",
        "pickup_available", "accepted_materials", "reliability_score",
    }
    assert expected_fields.issubset(recycler.keys())


def test_get_recycler_by_id():
    list_resp = client.get("/api/recyclers")
    recycler_id = list_resp.json()["data"][0]["id"]

    resp = client.get(f"/api/recyclers/{recycler_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == recycler_id


def test_get_nonexistent_recycler_returns_404():
    resp = client.get("/api/recyclers/not-a-real-id")
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "RECYCLER_NOT_FOUND"


# ----------------------------------------------------------------
# 10. Recycler matching
# ----------------------------------------------------------------

def test_match_returns_compatible_authorized_recycler():
    headers = _auth_header(COLLECTOR_EMAIL)
    # MAT001 = Copper, near GreenCycle Traders' location -- should match.
    lot_id = _create_lot("MAT001", headers, lat=12.9716, lng=77.5946)

    resp = client.get(f"/api/recyclers/match?lot_id={lot_id}", headers=headers)
    body = resp.json()
    assert resp.status_code == 200
    assert len(body["data"]) >= 1

    match = body["data"][0]
    assert match["authorized"] is True
    assert "distance_km" in match
    assert "match_score" in match
    assert 0 <= match["match_score"] <= 100


def test_match_results_are_sorted_best_first():
    headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot("MAT001", headers)

    resp = client.get(f"/api/recyclers/match?lot_id={lot_id}", headers=headers)
    scores = [m["match_score"] for m in resp.json()["data"]]
    assert scores == sorted(scores, reverse=True)


def test_match_excludes_recyclers_that_dont_accept_material():
    """
    MAT001 (Copper) is only accepted by GreenCycle Traders in seed data,
    not EcoScrap Solutions -- so EcoScrap should never appear.
    """
    headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot("MAT001", headers)

    resp = client.get(f"/api/recyclers/match?lot_id={lot_id}", headers=headers)
    names = [m["name"] for m in resp.json()["data"]]
    assert "EcoScrap Solutions" not in names


def test_match_returns_404_when_no_recycler_accepts_material_in_range():
    """
    Pick a location far from both seeded recyclers with a material
    only accepted nearby -- should find nobody in range.
    """
    headers = _auth_header(COLLECTOR_EMAIL)
    # Far away location (Mumbai, ~800km from Bengaluru), well outside
    # both recyclers' service radii (15km / 10km).
    lot_id = _create_lot("MAT001", headers, lat=19.0760, lng=72.8777)

    resp = client.get(f"/api/recyclers/match?lot_id={lot_id}", headers=headers)
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "NO_RECYCLER_FOUND"


def test_match_requires_lot_ownership():
    """A collector cannot request matches for another collector's lot."""
    owner_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot("MAT001", owner_headers)

    other_headers = _auth_header(COLLECTOR2_EMAIL)
    resp = client.get(f"/api/recyclers/match?lot_id={lot_id}", headers=other_headers)
    body = resp.json()
    assert resp.status_code == 403
    assert body["error"]["code"] == "FORBIDDEN"


def test_match_admin_can_check_any_lot():
    owner_headers = _auth_header(COLLECTOR_EMAIL)
    lot_id = _create_lot("MAT001", owner_headers)

    admin_headers = _auth_header(ADMIN_EMAIL)
    resp = client.get(f"/api/recyclers/match?lot_id={lot_id}", headers=admin_headers)
    assert resp.status_code == 200


def test_match_nonexistent_lot_returns_404():
    headers = _auth_header(COLLECTOR_EMAIL)
    resp = client.get("/api/recyclers/match?lot_id=not-a-real-lot", headers=headers)
    body = resp.json()
    assert resp.status_code == 404
    assert body["error"]["code"] == "LOT_NOT_FOUND"


def test_match_without_auth_fails():
    resp = client.get("/api/recyclers/match?lot_id=whatever")
    assert resp.status_code == 401
