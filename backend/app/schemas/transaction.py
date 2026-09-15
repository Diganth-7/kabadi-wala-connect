"""
schemas/transaction.py
------------------------
Response schema for Transactions. Transactions are never created
directly via an API request -- they're generated automatically by
services/handover_service.py after a successful handover -- so there's
no "TransactionCreateRequest" here, only the output shape.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.payment import PaymentMethod, PaymentStatus


class TransactionOut(BaseModel):
    id: str
    lot_id: str
    collector_id: str
    recycler_id: str
    material: str
    weight: float
    amount: Decimal
    payment_method: Optional[PaymentMethod] = None
    payment_status: PaymentStatus
    created_at: datetime

    model_config = {"from_attributes": True}
