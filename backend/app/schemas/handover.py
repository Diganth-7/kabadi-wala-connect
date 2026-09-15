"""
schemas/handover.py
---------------------
Request/response schemas for Handovers.

IMPORTANT (per spec): notice `HandoverCreateRequest` has NO
`final_amount` field. The backend always calculates it as
`actual_weight * agreed_price` (see services/handover_service.py) --
same pattern as `estimated_value` on lots (Phase 5): if the field isn't
in the input schema, the frontend has no way to influence it.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class HandoverCreateRequest(BaseModel):
    lot_id: str
    pickup_id: str
    actual_weight: float
    agreed_price: Decimal
    verification_reference: Optional[str] = None


class HandoverOut(BaseModel):
    id: str
    lot_id: str
    pickup_id: str
    collector_id: str
    recycler_id: str
    estimated_weight: float
    actual_weight: float
    agreed_price: Decimal
    final_amount: Decimal
    verification_reference: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
