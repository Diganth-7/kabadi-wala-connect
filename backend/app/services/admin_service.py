"""
services/admin_service.py
----------------------------
Business logic for admin-only operations: dashboard statistics
(calculated live from real data, never hard-coded -- same principle as
GET /api/earnings in Phase 9) and recycler authorization management.
"""

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.recycler import Recycler
from app.models.transaction import Transaction
from app.schemas.admin import DashboardOut
from app.utils.errors import AppError


def get_dashboard_stats(db: Session) -> DashboardOut:
    total_collectors = db.query(func.count(User.id)).filter(User.role == UserRole.COLLECTOR).scalar() or 0
    active_collectors = (
        db.query(func.count(User.id))
        .filter(User.role == UserRole.COLLECTOR, User.is_active == True)  # noqa: E712
        .scalar()
        or 0
    )
    authorized_recyclers = db.query(func.count(Recycler.id)).filter(Recycler.authorized == True).scalar() or 0  # noqa: E712

    # "Total e-waste" is measured from actual handed-over weight, since
    # Transaction.weight is the real, weighed amount (not just an
    # estimate) -- see handover_service.py, where a Transaction is only
    # ever created after a real handover happens.
    total_ewaste_kg = db.query(func.coalesce(func.sum(Transaction.weight), 0)).scalar() or 0
    total_ewaste_kg = round(float(total_ewaste_kg), 2)

    total_transactions = db.query(func.count(Transaction.id)).scalar() or 0

    # Total value of all recorded transactions, regardless of payment
    # status -- this reflects total transaction VOLUME processed by the
    # platform, not just money actually collected (which would be a
    # narrower "total paid" figure, not what "total_transaction_value" implies).
    total_transaction_value = db.query(func.coalesce(func.sum(Transaction.amount), 0)).scalar() or Decimal("0")

    return DashboardOut(
        total_collectors=total_collectors,
        active_collectors=active_collectors,
        authorized_recyclers=authorized_recyclers,
        total_ewaste_kg=total_ewaste_kg,
        total_transactions=total_transactions,
        total_transaction_value=total_transaction_value,
    )


def list_collectors(db: Session) -> list[User]:
    return db.query(User).filter(User.role == UserRole.COLLECTOR).order_by(User.created_at.desc()).all()


def update_recycler_authorization(db: Session, recycler_id: str, authorized: bool) -> Recycler:
    recycler = db.query(Recycler).filter(Recycler.id == recycler_id).first()
    if not recycler:
        raise AppError(code="RECYCLER_NOT_FOUND", message="Recycler not found.", status_code=404)

    recycler.authorized = authorized
    db.commit()
    db.refresh(recycler)
    return recycler
