"""
models/transaction.py
----------------------
A Transaction is automatically created right after a successful
Handover (in the handover SERVICE, Phase 8 — not here). It's the
record collectors/recyclers/admins look at for earnings and history.

We store `material_name` and `weight`/`amount` directly on the
transaction (instead of only linking to material_id and recomputing)
so that transaction history stays accurate and readable even if a
material's name or a lot's data changes later. This is a common pattern
for financial/historical records: snapshot the important values at the
time of the event.
"""

import uuid

from sqlalchemy import Column, String, Float, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base
# Reuse the SAME enum classes as payment.py, rather than redefining them
# here. Two separate Python Enum classes with the same name would create
# a naming collision for the underlying Postgres ENUM type.
from app.models.payment import PaymentMethod, PaymentStatus


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    lot_id = Column(String, ForeignKey("lots.id"), nullable=False, index=True)
    collector_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    recycler_id = Column(String, ForeignKey("recyclers.id"), nullable=False, index=True)

    # Snapshot fields (see module docstring for why these are stored
    # directly instead of only referencing material_id).
    material_name = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    # Nullable because a transaction can exist before a payment method
    # is chosen (payment happens in a separate step, Phase 9).
    payment_method = Column(SAEnum(PaymentMethod), nullable=True)
    payment_status = Column(SAEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lot = relationship("Lot")
    collector = relationship("User")
    recycler = relationship("Recycler")

    def __repr__(self):
        return f"<Transaction id={self.id} amount={self.amount} status={self.payment_status}>"
