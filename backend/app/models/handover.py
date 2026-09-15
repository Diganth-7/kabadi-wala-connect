"""
models/handover.py
-------------------
A Handover records the moment scrap is physically handed from the
Collector to the Recycler — the actual weighed amount, the agreed
price, and the final payout amount.

IMPORTANT (per spec): `final_amount` is ALWAYS calculated by the
backend as `actual_weight * agreed_price`. The frontend must never be
trusted to send this number directly — that calculation happens in the
handover SERVICE (Phase 8), not here.

We also store `estimated_weight` (copied from the Lot at handover time)
so we can compare estimated vs actual later without an extra join.
"""

import uuid

from sqlalchemy import Column, String, Float, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Handover(Base):
    __tablename__ = "handovers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    lot_id = Column(String, ForeignKey("lots.id"), nullable=False, index=True)
    pickup_id = Column(String, ForeignKey("pickups.id"), nullable=False, index=True)
    collector_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    recycler_id = Column(String, ForeignKey("recyclers.id"), nullable=False, index=True)

    estimated_weight = Column(Float, nullable=False)
    actual_weight = Column(Float, nullable=False)

    agreed_price = Column(Numeric(10, 2), nullable=False)     # price per unit, agreed at handover
    final_amount = Column(Numeric(10, 2), nullable=False)     # backend-calculated: actual_weight * agreed_price

    verification_reference = Column(String, nullable=True)     # e.g. a QR code reference

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lot = relationship("Lot")
    pickup = relationship("Pickup")
    collector = relationship("User")
    recycler = relationship("Recycler")

    # Enforces "prevent duplicate handovers for the same lot" directly
    # at the database level — even if application code has a bug, the
    # database itself will reject a second handover row for the same lot_id.
    __table_args__ = (
        UniqueConstraint("lot_id", name="uq_handover_lot_id"),
    )

    def __repr__(self):
        return f"<Handover id={self.id} lot_id={self.lot_id} final_amount={self.final_amount}>"
