"""
models/pickup.py
-----------------
A Pickup request connects a specific Lot to a specific Recycler, and
tracks the physical pickup process through a sequence of statuses
(REQUESTED -> ACCEPTED -> ... -> COMPLETED, or cancelled along the way).

The actual "is this status change allowed?" validation logic (e.g.
rejecting COMPLETED -> REQUESTED) lives in the pickup SERVICE, not here
— this model just stores the data. Keeping validation logic out of
models is a common, simple pattern: models describe data shape, services
describe business rules.
"""

import enum
import uuid

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class PickupStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    ASSIGNED = "ASSIGNED"
    ON_THE_WAY = "ON_THE_WAY"
    ARRIVED = "ARRIVED"
    HANDOVER = "HANDOVER"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Pickup(Base):
    __tablename__ = "pickups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    lot_id = Column(String, ForeignKey("lots.id"), nullable=False, index=True)
    collector_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    recycler_id = Column(String, ForeignKey("recyclers.id"), nullable=False, index=True)

    status = Column(SAEnum(PickupStatus), nullable=False, default=PickupStatus.REQUESTED, index=True)

    pickup_latitude = Column(Float, nullable=False)
    pickup_longitude = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    lot = relationship("Lot")
    collector = relationship("User")
    recycler = relationship("Recycler")

    def __repr__(self):
        return f"<Pickup id={self.id} lot_id={self.lot_id} status={self.status}>"
