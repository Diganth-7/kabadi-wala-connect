"""
routers/transactions.py
--------------------------
GET /api/transactions -> role-based list of transactions.

Transactions are never created directly through this router -- they're
generated automatically by services/handover_service.py after a
successful handover (see Phase 8's Handover section). This endpoint is
read-only by design.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction
from app.models.user import User, UserRole
from app.services import transaction_service
from app.auth.dependencies import get_current_user
from app.utils.errors import success_response

router = APIRouter()


@router.get("")
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    - COLLECTOR -> only their own transactions
    - RECYCLER  -> only their own transactions
    - ADMIN     -> every transaction
    """
    query = db.query(Transaction).order_by(Transaction.created_at.desc())

    if current_user.role == UserRole.COLLECTOR:
        transactions = query.filter(Transaction.collector_id == current_user.id).all()
    elif current_user.role == UserRole.RECYCLER:
        # Transaction.recycler_id references Recycler.id, not the login
        # user's own id -- so we filter by matching that recycler's user_id.
        transactions = [t for t in query.all() if t.recycler.user_id == current_user.id]
    else:  # ADMIN
        transactions = transaction_service.list_all_transactions(db)

    return success_response([transaction_service.serialize_transaction(t) for t in transactions])
