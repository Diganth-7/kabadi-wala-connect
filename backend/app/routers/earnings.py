"""
routers/earnings.py
----------------------
GET /api/earnings -> a collector's earnings summary, calculated live
from their own transactions (never hard-coded, per spec).

Restricted to COLLECTOR role: your spec's Roles section explicitly
grants "view their own transactions and earnings" to Collectors, and
doesn't mention earnings for Recyclers or Admins -- admins get
aggregate financial figures through a separate admin dashboard
endpoint instead (Phase 11), so there's no overlap/ambiguity about
where "the real numbers" live.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction
from app.models.payment import PaymentStatus
from app.auth.dependencies import require_role
from app.models.user import User, UserRole
from app.utils.errors import success_response

router = APIRouter()


def _sum_amount(db: Session, collector_id: str, status: PaymentStatus, since: datetime | None = None) -> Decimal:
    query = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.collector_id == collector_id,
        Transaction.payment_status == status,
    )
    if since is not None:
        query = query.filter(Transaction.created_at >= since)
    return query.scalar() or Decimal("0")


@router.get("")
def get_earnings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COLLECTOR)),
):
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=start_of_today.weekday())  # Monday
    start_of_month = start_of_today.replace(day=1)

    today = _sum_amount(db, current_user.id, PaymentStatus.PAID, since=start_of_today)
    this_week = _sum_amount(db, current_user.id, PaymentStatus.PAID, since=start_of_week)
    this_month = _sum_amount(db, current_user.id, PaymentStatus.PAID, since=start_of_month)
    pending = _sum_amount(db, current_user.id, PaymentStatus.PENDING)

    return success_response({
        "today": float(today),
        "this_week": float(this_week),
        "this_month": float(this_month),
        "pending": float(pending),
        "currency": "INR",
    })
