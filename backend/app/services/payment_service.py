"""
services/payment_service.py
------------------------------
Business logic for simulated Payments (no real gateway integration,
per spec).

KEY RULE: "a failed payment must never be returned as PAID." We enforce
this structurally, not just by convention: a failed simulated payment
still gets its Payment row saved (status=FAILED, for an audit trail),
but the API call itself raises AppError(PAYMENT_FAILED) rather than
returning a normal success response -- so there's no code path where a
failed attempt could accidentally be serialized back as PAID.
"""

from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus
from app.models.transaction import Transaction
from app.models.user import User, UserRole
from app.schemas.payment import PaymentCreateRequest
from app.services import notification_service
from app.utils.errors import AppError


def _simulate_payment_result(payload: PaymentCreateRequest) -> bool:
    """
    Stands in for a real payment gateway call. Returns True (success)
    or False (failure).

    In this prototype, payments succeed by default -- there's no real
    gateway to fail against. `simulate_failure` (see schemas/payment.py)
    is a dev-only escape hatch for deterministically testing the
    failure path.
    """
    return not payload.simulate_failure


def create_payment(db: Session, current_user: User, payload: PaymentCreateRequest) -> Payment:
    transaction = db.query(Transaction).filter(Transaction.id == payload.transaction_id).first()
    if not transaction:
        raise AppError(code="TRANSACTION_NOT_FOUND", message="Transaction not found.", status_code=404)

    # Authorization: the recycler involved in this transaction (the one
    # paying the collector) or an admin can record a payment for it.
    is_admin = current_user.role == UserRole.ADMIN
    is_transaction_recycler = current_user.role == UserRole.RECYCLER and transaction.recycler.user_id == current_user.id
    if not (is_admin or is_transaction_recycler):
        raise AppError(
            code="FORBIDDEN",
            message="Only the recycler on this transaction can record a payment for it.",
            status_code=403,
        )

    existing_paid = (
        db.query(Payment)
        .filter(Payment.transaction_id == payload.transaction_id, Payment.status == PaymentStatus.PAID)
        .first()
    )
    if existing_paid:
        raise AppError(
            code="PAYMENT_ALREADY_COMPLETED",
            message="This transaction has already been paid.",
            status_code=409,
        )

    succeeded = _simulate_payment_result(payload)

    payment = Payment(
        transaction_id=transaction.id,
        method=payload.method,
        status=PaymentStatus.PAID if succeeded else PaymentStatus.FAILED,
        amount=transaction.amount,
    )
    db.add(payment)

    # Keep the Transaction's own payment_status/method fields in sync
    # with the latest payment attempt -- this is what GET /api/transactions
    # and GET /api/earnings read from.
    transaction.payment_method = payload.method
    transaction.payment_status = PaymentStatus.PAID if succeeded else PaymentStatus.FAILED

    db.commit()
    db.refresh(payment)

    if not succeeded:
        raise AppError(code="PAYMENT_FAILED", message="Payment could not be processed.", status_code=402)

    notification_service.create_notification(
        db, transaction.collector_id,
        title="Payment recorded",
        message=f"A payment of \u20b9{transaction.amount} via {payload.method.value} has been recorded for your {transaction.material_name} transaction.",
        type="PAYMENT_RECORDED",
    )

    return payment
