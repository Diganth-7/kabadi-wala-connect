"""
tests/test_materials_prices.py
--------------------------------
Tests covering:
  5. Material retrieval
  6. Price retrieval

Requires PostgreSQL running with seed data loaded (python scripts/seed.py),
same as tests/test_auth.py.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ----------------------------------------------------------------
# 5. Material retrieval
# ----------------------------------------------------------------

def test_list_materials_returns_all_nine():
    resp = client.get("/api/materials")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert len(body["data"]) == 9


def test_materials_have_expected_fields():
    resp = client.get("/api/materials")
    material = resp.json()["data"][0]
    assert set(["id", "name", "display_name", "icon", "unit"]).issubset(material.keys())


def test_materials_include_copper():
    resp = client.get("/api/materials")
    names = [m["name"] for m in resp.json()["data"]]
    assert "copper" in names


# ----------------------------------------------------------------
# 6. Price retrieval
# ----------------------------------------------------------------

def test_list_all_prices():
    resp = client.get("/api/prices")
    body = resp.json()
    assert resp.status_code == 200
    assert body["success"] is True
    assert len(body["data"]) == 9


def test_get_price_for_valid_material():
    resp = client.get("/api/prices/MAT001")
    body = resp.json()
    assert resp.status_code == 200
    assert body["data"]["material_id"] == "MAT001"
    assert float(body["data"]["current_price"]) > 0
    assert body["data"]["currency"] == "INR"


def test_get_price_for_invalid_material_returns_404():
    resp = client.get("/api/prices/NOT_A_REAL_MATERIAL")
    body = resp.json()
    assert resp.status_code == 404
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_MATERIAL"


def test_prices_do_not_require_auth():
    """Materials/prices are public reference data — no token needed."""
    resp = client.get("/api/materials")
    assert resp.status_code == 200
    resp2 = client.get("/api/prices")
    assert resp2.status_code == 200
