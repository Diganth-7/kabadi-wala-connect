"""
models/material.py
-------------------
The catalog of scrap/e-waste material types (Copper, Aluminium, PCB,
etc.). This is mostly static reference data — seeded once, rarely
changed after that.
"""

from sqlalchemy import Column, String

from app.database import Base


class Material(Base):
    __tablename__ = "materials"

    # Human-friendly IDs like "MAT001" (matches the examples in the spec)
    # instead of a UUID, since these are seeded, fixed reference rows —
    # not user-generated data — so no need to hide/obscure the ID.
    id = Column(String, primary_key=True)

    name = Column(String, unique=True, nullable=False)          # e.g. "copper"
    display_name = Column(String, nullable=False)                 # e.g. "Copper"
    icon = Column(String, nullable=True)                          # e.g. an icon name/URL for the frontend
    unit = Column(String, nullable=False, default="kg")           # e.g. "kg"

    def __repr__(self):
        return f"<Material id={self.id} name={self.name}>"
