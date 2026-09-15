"""
schemas/recycler.py
---------------------
Response shapes for recyclers and recycler matching.
"""

from pydantic import BaseModel

from app.schemas.material import MaterialOut


class LocationOut(BaseModel):
    latitude: float
    longitude: float


class RecyclerOut(BaseModel):
    id: str
    name: str
    authorized: bool
    location: LocationOut
    service_radius_km: float
    pickup_available: bool
    accepted_materials: list[MaterialOut]
    reliability_score: float


class RecyclerMatchOut(BaseModel):
    """
    The result of matching ONE recycler against a lot. Field names match
    the spec exactly: recycler_id, name, distance_km, buying_price,
    pickup_available, authorized, accepted_materials, match_score.
    """
    recycler_id: str
    name: str
    distance_km: float
    buying_price: float
    pickup_available: bool
    authorized: bool
    accepted_materials: list[MaterialOut]
    match_score: float
