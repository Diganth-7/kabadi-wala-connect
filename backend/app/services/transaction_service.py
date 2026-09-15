"""
services/transaction_service.py
----------------------------------
Small shared helpers for Transactions -- extracted here (rather than
living only inside routers/transactions.py) so the admin router
(Phase 11) can list all transactions without duplicating the
serialization logic.
"""

from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.transaction import TransactionOut


def serialize_transaction(t: Transaction) -> dict:
    out = TransactionOut(
        id=t.id,
        lot_id=t.lot_id,
        collector_id=t.collector_id,
        recycler_id=t.recycler_id,
        material=t.material_name,
        weight=t.weight,
        amount=t.amount,
        payment_method=t.payment_method,
        payment_status=t.payment_status,
        created_at=t.created_at,
    )
    return out.model_dump(mode="json")


def list_all_transactions(db: Session) -> list[Transaction]:
    return db.query(Transaction).order_by(Transaction.created_at.desc()).all()
