"""
models/lot.py
--------------
A "Lot" is a batch of scrap material a Collector wants to sell — e.g.
"10.5 kg of Copper, in good condition". This is the core object that
flows through the whole app: Lot -> Pickup -> Handover -> Transaction.

IMPORTANT (per spec): `estimated_value` is ALWAYS calculated by the
backend (estimated_weight × current_price at creation time). The
frontend is never trusted to send this value — see the lot creation
service in Phase 5, which is where that calculation will actually
happen. This model just stores the result.
"""

import enum
import uuid

from sqlalchemy import Column, String, Float, Numeric, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class LotCondition(str, enum.Enum):
    GOOD = "GOOD"
    MIXED = "MIXED"
    DAMAGED = "DAMAGED"


class LotStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CREATED = "CREATED"
    PICKUP_REQUESTED = "PICKUP_REQUESTED"
    ACCEPTED = "ACCEPTED"
    HANDOVER = "HANDOVER"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Lot(Base):
    __tablename__ = "lots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # index=True on collector_id: collectors will frequently query
    # "show me MY lots", so this speeds up that lookup.
    collector_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    material_id = Column(String, ForeignKey("materials.id"), nullable=False, index=True)

    estimated_weight = Column(Float, nullable=False)
    actual_weight = Column(Float, nullable=True)  # filled in later, at handover time

    condition = Column(SAEnum(LotCondition), nullable=False)

    # Numeric for money — see price.py for why.
    estimated_value = Column(Numeric(10, 2), nullable=False)

    status = Column(SAEnum(LotStatus), nullable=False, default=LotStatus.CREATED, index=True)

    # Location stored as plain lat/lng floats (see recycler.py for the
    # same reasoning).
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    photo_url = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    collector = relationship("User")
    material = relationship("Material")

    def __repr__(self):
        return f"<Lot id={self.id} material_id={self.material_id} status={self.status}>"
