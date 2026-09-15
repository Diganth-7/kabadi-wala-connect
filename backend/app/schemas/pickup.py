"""
schemas/pickup.py
-------------------
Request/response schemas for Pickups.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.pickup import PickupStatus


class LocationIn(BaseModel):
    latitude: float
    longitude: float


class LocationOut(BaseModel):
    latitude: float
    longitude: float


class PickupCreateRequest(BaseModel):
    lot_id: str
    recycler_id: str
    pickup_location: LocationIn


class PickupStatusUpdateRequest(BaseModel):
    status: PickupStatus


class PickupOut(BaseModel):
    id: str
    lot_id: str
    collector_id: str
    recycler_id: str
    status: PickupStatus
    pickup_location: LocationOut
    created_at: datetime
    updated_at: datetime
