"""
models/price.py
----------------
One row per material, tracking today's price. This is the SOURCE OF
TRUTH for scrap value calculations — the frontend is never trusted to
send a price, only ever shown one.

We keep one row per material and UPDATE it when prices change (rather
than keeping full price history), since the spec only asks for
"current_price" + min/max, not a historical price chart. Simpler is
better for a prototype.
"""

from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Price(Base):
    __tablename__ = "prices"

    # material_id doubles as the primary key since there's exactly one
    # price row per material (a one-to-one relationship).
    material_id = Column(String, ForeignKey("materials.id"), primary_key=True)

    # Numeric (not Float) is used for money so we don't get floating-point
    # rounding errors like 10.1 + 20.2 = 30.299999999999997.
    current_price = Column(Numeric(10, 2), nullable=False)
    min_price = Column(Numeric(10, 2), nullable=False)
    max_price = Column(Numeric(10, 2), nullable=False)

    unit = Column(String, nullable=False, default="kg")
    currency = Column(String, nullable=False, default="INR")

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    material = relationship("Material")

    def __repr__(self):
        return f"<Price material_id={self.material_id} current_price={self.current_price}>"
