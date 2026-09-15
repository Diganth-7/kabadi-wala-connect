"""
auth/dependencies.py
---------------------
Reusable FastAPI "dependencies" that other routers plug into their
endpoints to require login and/or specific roles.

Usage in a future router:

    from app.auth.dependencies import get_current_user, require_role
    from app.models.user import UserRole

    @router.get("/my-lots")
    def get_my_lots(current_user: User = Depends(get_current_user)):
        # current_user is guaranteed to be a valid, logged-in, active user
        ...

    @router.get("/admin/dashboard")
    def dashboard(current_user: User = Depends(require_role(UserRole.ADMIN))):
        # current_user is guaranteed to be logged in AND have role=ADMIN
        ...
"""

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.auth.jwt import decode_access_token
from app.utils.errors import AppError

# HTTPBearer reads the "Authorization: Bearer <token>" header for us.
# auto_error=False means FastAPI does NOT raise its own default error
# when the header is missing -- instead we handle that ourselves below,
# so a missing token produces the same {"success": false, "error": {...}}
# shape (and 401 status) as every other auth failure, instead of
# FastAPI's default {"detail": "Not authenticated"} / 403.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decodes the JWT from the Authorization header, then loads the
    CURRENT version of that user from the database.

    We deliberately re-fetch from the database every time (rather than
    trusting only what's inside the token) so that:
    - a deactivated user is blocked immediately, not just when their
      old token eventually expires
    - role changes take effect immediately
    """
    if credentials is None:
        raise AppError(code="UNAUTHORIZED", message="Authentication token is required.", status_code=401)

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")

    if not user_id:
        raise AppError(code="UNAUTHORIZED", message="Invalid authentication token.", status_code=401)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise AppError(code="USER_NOT_FOUND", message="User account no longer exists.", status_code=404)

    if not user.is_active:
        raise AppError(code="FORBIDDEN", message="This account has been deactivated.", status_code=403)

    return user


def require_role(*allowed_roles: UserRole):
    """
    Dependency FACTORY: call this with one or more allowed roles to get
    a dependency that enforces them.

    Example: Depends(require_role(UserRole.ADMIN))
             Depends(require_role(UserRole.COLLECTOR, UserRole.ADMIN))
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppError(
                code="FORBIDDEN",
                message="You do not have permission to access this resource.",
                status_code=403,
            )
        return current_user

    return dependency
