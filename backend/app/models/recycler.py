"""
models/recycler.py
-------------------
Represents a recycler BUSINESS (not just a login user). A recycler
business is run by a User with role=RECYCLER (linked via user_id), but
has its own extra fields: authorization status, location, accepted
materials, reliability score, etc.

`accepted_materials` uses a many-to-many relationship through a small
association table (`recycler_materials`), since one recycler can accept
many materials, and one material can be accepted by many recyclers.
"""

import uuid

from sqlalchemy import Column, String, Boolean, Float, DateTime, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


# Association table for the many-to-many relationship between
# Recycler and Material ("which materials does this recycler accept?").
# This is just a plain table (not a full model class) because it has no
# extra data of its own — it only links two IDs together.
recycler_materials = Table(
    "recycler_materials",
    Base.metadata,
    Column("recycler_id", String, ForeignKey("recyclers.id"), primary_key=True),
    Column("material_id", String, ForeignKey("materials.id"), primary_key=True),
)


class Recycler(Base):
    __tablename__ = "recyclers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Links this recycler business to the User account that logs in and
    # manages it. Nullable=False + unique means: every recycler business
    # has exactly one login user, and that user manages exactly one business.
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)

    name = Column(String, nullable=False)
    authorized = Column(Boolean, default=False, nullable=False, index=True)

    # Location stored as separate lat/lng columns rather than a special
    # geo type — simpler to set up for a prototype, and good enough for
    # the straight-line distance calculation used in recycler matching.
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    service_radius_km = Column(Float, nullable=False, default=10.0)
    pickup_available = Column(Boolean, default=True, nullable=False)

    # 0.0 to 5.0 scale, used as one of the recycler-matching factors.
    reliability_score = Column(Float, nullable=False, default=3.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")
    accepted_materials = relationship("Material", secondary=recycler_materials)

    def __repr__(self):
        return f"<Recycler id={self.id} name={self.name} authorized={self.authorized}>"
