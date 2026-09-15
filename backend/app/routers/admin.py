"""
routers/admin.py
-------------------
All 5 admin-only endpoints. Every single one is gated behind
require_role(UserRole.ADMIN) -- collectors and recyclers get 403 on
all of them, no exceptions.

GET   /api/admin/dashboard
GET   /api/admin/collectors
GET   /api/admin/recyclers
GET   /api/admin/transactions
PATCH /api/admin/recyclers/{recycler_id}/authorization
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import UserOut
from app.schemas.admin import RecyclerAuthorizationUpdateRequest
from app.services import admin_service, recycler_service, transaction_service
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.utils.errors import success_response

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    stats = admin_service.get_dashboard_stats(db)
    return success_response(stats.model_dump(mode="json"))


@router.get("/collectors")
def list_collectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    collectors = admin_service.list_collectors(db)
    data = [UserOut.model_validate(c).model_dump(mode="json") for c in collectors]
    return success_response(data)


@router.get("/recyclers")
def list_recyclers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    recyclers = recycler_service.list_recyclers(db)
    return success_response([recycler_service.serialize_recycler(r) for r in recyclers])


@router.get("/transactions")
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    transactions = transaction_service.list_all_transactions(db)
    return success_response([transaction_service.serialize_transaction(t) for t in transactions])


@router.patch("/recyclers/{recycler_id}/authorization")
def update_recycler_authorization(
    recycler_id: str,
    payload: RecyclerAuthorizationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    recycler = admin_service.update_recycler_authorization(db, recycler_id, payload.authorized)
    return success_response(recycler_service.serialize_recycler(recycler))
