"""
schemas/admin.py
------------------
Response/request shapes specific to admin endpoints.
"""

from decimal import Decimal

from pydantic import BaseModel


class DashboardOut(BaseModel):
    total_collectors: int
    active_collectors: int
    authorized_recyclers: int
    total_ewaste_kg: float
    total_transactions: int
    total_transaction_value: Decimal


class RecyclerAuthorizationUpdateRequest(BaseModel):
    authorized: bool
