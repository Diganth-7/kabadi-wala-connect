"""
auth/jwt.py
-----------
Handles creating and decoding JWT (JSON Web Token) access tokens.

Quick JWT primer, since you're new to this:
- A JWT is a signed string the server gives the user after login.
- The user sends it back on every request (in the "Authorization" header)
  to prove who they are, without the server needing to store sessions.
- "Signed" means: we can verify nobody tampered with it, because it's
  signed using JWT_SECRET_KEY (from .env) — a secret only our server
  knows. If anyone edits the token's contents, the signature check fails.

We store two things inside the token:
- "sub" (subject) = the user's ID
- "role" = the user's role, just for convenience/logging

IMPORTANT: We never trust the "role" inside the token alone for
authorization decisions. Every request re-loads the user's *current*
role from the database (see auth/dependencies.py), so if an admin
changes someone's role or deactivates them, that takes effect
immediately — not only after their old token expires.
"""

from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from app.config import settings
from app.utils.errors import AppError


def create_access_token(user_id: str, role: str) -> str:
    """
    Creates a signed JWT for a given user.

    `expires_delta` comes from settings (JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    in .env), so token lifetime is configurable without code changes.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> dict:
    """
    Verifies and decodes a JWT. Raises AppError (401) if the token is
    invalid, tampered with, or expired.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise AppError(
            code="UNAUTHORIZED",
            message="Invalid or expired authentication token.",
            status_code=401,
        )
