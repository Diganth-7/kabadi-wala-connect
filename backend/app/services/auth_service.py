"""
services/auth_service.py
-------------------------
Business logic for the mock OTP login flow:

  1. login(identifier)       -> looks up the user, generates a one-time
                                  OTP code, "sends" it (just prints it to
                                  the console for this prototype), and
                                  stores a HASHED version of it in memory.
  2. verify_otp(identifier, otp) -> checks the OTP is correct and not
                                  expired, then issues a JWT.

WHY IN-MEMORY OTP STORAGE (not a database table)?
For a prototype, OTPs are short-lived (a few minutes) and don't need to
survive a server restart or be queried later — a database table would
be unnecessary complexity. A simple Python dict works fine here. (If
this app is later deployed with multiple server instances, this would
need to move to something shared like Redis — noted here for future
reference, but out of scope for this prototype.)

WHY HASH THE OTP EVEN THOUGH IT'S JUST A DEV MOCK?
The spec says "do not store passwords in plaintext" — the same
principle applies to OTPs, since they're also a secret credential.
Hashing costs us nothing here and is the right habit to build.
"""

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.auth.jwt import create_access_token
from app.utils.errors import AppError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory OTP store: { identifier: {"hashed_otp": str, "expires_at": datetime} }
# NOTE: this resets whenever the server restarts — expected and fine for dev.
_otp_store: dict[str, dict] = {}

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5


def _find_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    """A user can log in with either their email or their phone number."""
    return db.query(User).filter(
        (User.email == identifier) | (User.phone == identifier)
    ).first()


def _generate_otp() -> str:
    """Generates a random 6-digit numeric OTP, e.g. '482913'."""
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def request_otp(db: Session, identifier: str) -> dict:
    """
    Step 1 of login: find the user, generate + "send" an OTP.

    Returns a dict with a message, and — ONLY when not in production —
    the raw OTP itself, so you can test the flow without wiring up real
    SMS. In production this key is omitted entirely.
    """
    user = _find_user_by_identifier(db, identifier)
    if not user:
        raise AppError(code="USER_NOT_FOUND", message="No account found with that email or phone.", status_code=404)

    if not user.is_active:
        raise AppError(code="FORBIDDEN", message="This account has been deactivated.", status_code=403)

    otp = _generate_otp()
    hashed_otp = pwd_context.hash(otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    _otp_store[identifier] = {"hashed_otp": hashed_otp, "expires_at": expires_at}

    # Mock "sending" the OTP — in a real app this would call an SMS/email
    # provider. For the prototype, we just log it to the server console.
    print(f"[DEV OTP] OTP for {identifier} is: {otp} (expires in {OTP_EXPIRY_MINUTES} min)")

    result = {
        "message": "OTP sent successfully.",
        "expires_in_minutes": OTP_EXPIRY_MINUTES,
    }
    if not settings.is_production:
        # Dev convenience only — lets you test login end-to-end via
        # Swagger without needing a real SMS provider hooked up.
        result["dev_otp"] = otp

    return result


def verify_otp(db: Session, identifier: str, otp: str) -> dict:
    """
    Step 2 of login: check the OTP is correct and not expired, then
    issue a JWT access token for the user.
    """
    entry = _otp_store.get(identifier)
    if not entry:
        raise AppError(code="UNAUTHORIZED", message="No OTP was requested for this identifier, or it already expired.", status_code=401)

    if datetime.now(timezone.utc) > entry["expires_at"]:
        del _otp_store[identifier]
        raise AppError(code="UNAUTHORIZED", message="OTP has expired. Please request a new one.", status_code=401)

    if not pwd_context.verify(otp, entry["hashed_otp"]):
        raise AppError(code="UNAUTHORIZED", message="Incorrect OTP.", status_code=401)

    # OTP is correct and used — remove it so it can't be reused (one-time use).
    del _otp_store[identifier]

    user = _find_user_by_identifier(db, identifier)
    if not user:
        # Very unlikely (user existed at request_otp time) but handled
        # defensively in case the account was deleted in between.
        raise AppError(code="USER_NOT_FOUND", message="No account found with that email or phone.", status_code=404)

    access_token = create_access_token(user_id=user.id, role=user.role.value)

    return {"access_token": access_token, "token_type": "bearer", "user": user}
