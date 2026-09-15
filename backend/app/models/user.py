"""
models/user.py
---------------
The User table represents EVERY person who logs into the system —
Collectors, Recyclers (the person managing a recycler business), and
Admins. We tell them apart using the `role` column.

Why one table for all 3 roles instead of 3 separate tables?
- They all need to log in the same way (via phone/OTP + JWT).
- A "Recycler" business's extra details (service radius, accepted
  materials, etc.) live in their own `Recycler` table (see recycler.py),
  linked back to this User via `user_id`. That keeps this table simple.
- Collectors don't have any extra fields in this project's spec, so
  they don't get a separate table — that would be unnecessary
  complexity for a prototype.
"""

import enum
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, enum.Enum):
    """The 3 roles allowed in the system."""
    COLLECTOR = "COLLECTOR"
    RECYCLER = "RECYCLER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    # We use a UUID string as the primary key instead of an auto-increment
    # integer. This makes IDs unguessable (you can't just try id=1, id=2...
    # to snoop on other users' data), which matters since the spec says
    # users must never access another user's data by changing an ID.
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Contact info used for mock OTP login (Phase 3).
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)

    name = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, index=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User id={self.id} name={self.name} role={self.role}>"
