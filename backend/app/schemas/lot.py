"""
schemas/lot.py
---------------
Request/response schemas for Scrap Lots.

IMPORTANT (per spec): notice `LotCreateRequest` has NO `estimated_value`
field at all — the frontend physically cannot send one, because the
schema doesn't accept it. The backend always calculates it (see
services/lot_service.py). This is the cleanest way to enforce "don't
trust the frontend for this value": if the field doesn't exist in the
input schema, there's nothing to trust or distrust — it's simply not
accepted as input.

Likewise, there's no `collector_id` field in the request — the lot's
owner is always taken from the logged-in user's JWT (see the lots
router), never from anything the client sends.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models.lot import LotCondition, LotStatus


class LocationIn(BaseModel):
    latitude: float
    longitude: float


class LotCreateRequest(BaseModel):
    material_id: str
    estimated_weight: float
    condition: LotCondition
    location: LocationIn
    photo_url: Optional[str] = None

    @field_validator("material_id")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("material_id must not be empty")
        return v.strip()


class LocationOut(BaseModel):
    latitude: float
    longitude: float


class LotOut(BaseModel):
    id: str
    collector_id: str
    material_id: str
    estimated_weight: float
    actual_weight: Optional[float] = None
    condition: LotCondition
    estimated_value: Decimal
    status: LotStatus
    location: LocationOut
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
