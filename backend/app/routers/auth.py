"""
routers/auth.py
----------------
The 3 authentication endpoints:

  POST /api/auth/login        -> request an OTP for your email/phone
  POST /api/auth/verify-otp   -> submit the OTP, get back a JWT
  GET  /api/auth/me           -> (requires login) get your own profile

Routers stay THIN on purpose: they just parse the request, call the
service layer to do the actual work, and wrap the result in
success_response(). All real logic lives in services/auth_service.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, VerifyOtpRequest, TokenResponse, UserOut
from app.services import auth_service
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.utils.errors import success_response

router = APIRouter()


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Step 1 of login. Looks up the user by email or phone and generates
    a mock OTP (printed to the server console; also returned directly
    in the response when not running in production, for easy testing).
    """
    result = auth_service.request_otp(db, payload.identifier)
    return success_response(result)


@router.post("/verify-otp", response_model=None)
def verify_otp(payload: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Step 2 of login. Checks the OTP and, if correct, returns a JWT
    access token plus the user's profile.
    """
    result = auth_service.verify_otp(db, payload.identifier, payload.otp)
    token_response = TokenResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
        user=UserOut.model_validate(result["user"]),
    )
    return success_response(token_response.model_dump(mode="json"))


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of whoever's JWT was sent in the Authorization header."""
    return success_response(UserOut.model_validate(current_user).model_dump(mode="json"))
