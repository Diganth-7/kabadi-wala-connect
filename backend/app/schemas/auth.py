"""
schemas/auth.py
----------------
Pydantic schemas define the SHAPE of data going in and out of the auth
endpoints. FastAPI uses these to:
- automatically validate incoming request bodies (reject bad input
  before it reaches our code)
- automatically document the API in Swagger (/docs)
- control exactly what fields go OUT in a response (so we don't
  accidentally leak internal fields)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    """
    Body for POST /api/auth/login.
    `identifier` can be either an email or a phone number — whichever
    the user registered with (from seed data, e.g. "collector@test.com").
    """
    identifier: str

    @field_validator("identifier")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("identifier must not be empty")
        return v.strip()


class VerifyOtpRequest(BaseModel):
    """Body for POST /api/auth/verify-otp."""
    identifier: str
    otp: str


class UserOut(BaseModel):
    """
    What we send back to describe a user — deliberately leaves out any
    internal-only fields. Used in /auth/me and inside the login response.
    """
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    # Lets Pydantic build this schema directly from a SQLAlchemy User
    # object (model.attribute -> schema.field), not just from a dict.
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Returned by POST /api/auth/verify-otp on success."""
    access_token: str
    token_type: str = "bearer"
    user: UserOut
