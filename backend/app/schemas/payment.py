"""
schemas/payment.py
---------------------
Request/response schemas for simulated Payments.

NOTE on `simulate_failure`: this is a DEV-ONLY testing convenience, not
part of the spec's required request shape. It's optional and defaults
to False, so normal clients sending only {transaction_id, method} work
exactly as documented -- but it lets us deterministically test the
"payment failed" path (see services/payment_service.py) without random
flakiness. Since there's no real payment gateway to actually fail
against yet (per spec: simulate only, no Razorpay/Stripe/etc.), some
way to exercise the failure path is needed for testing -- a random
coin-flip would make tests unreliable, so an explicit opt-in flag is
the simplest deterministic alternative.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentCreateRequest(BaseModel):
    transaction_id: str
    method: PaymentMethod
    simulate_failure: bool = False


class PaymentOut(BaseModel):
    id: str
    transaction_id: str
    method: PaymentMethod
    status: PaymentStatus
    amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
