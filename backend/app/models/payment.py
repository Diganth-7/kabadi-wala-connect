"""
models/payment.py
------------------
A Payment records an attempt to pay out a Transaction (simulated for
now — no real UPI/Razorpay/etc. integration, per spec).

We keep Payment as its own table (separate from Transaction) because:
- A transaction could, in theory, have more than one payment attempt
  (e.g. first attempt FAILED, second attempt PAID).
- It keeps "the sale record" (Transaction) separate from "the money
  movement record" (Payment), which is a natural, common separation.

"Prevent duplicate successful payments" (per spec) is enforced in the
payment SERVICE (Phase 9) by checking there isn't already a PAID
payment for this transaction before creating a new one.
"""

import enum
import uuid

from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class PaymentMethod(str, enum.Enum):
    UPI = "UPI"
    CASH = "CASH"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    DISPUTED = "DISPUTED"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False, index=True)

    method = Column(SAEnum(PaymentMethod), nullable=False)
    status = Column(SAEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)
    amount = Column(Numeric(10, 2), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    transaction = relationship("Transaction")

    def __repr__(self):
        return f"<Payment id={self.id} transaction_id={self.transaction_id} status={self.status}>"
