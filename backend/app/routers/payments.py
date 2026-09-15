"""
routers/payments.py
----------------------
POST /api/payments -> record a (simulated) payment for a transaction.

Restricted to the recycler on that transaction, or an admin -- same
reasoning as handovers: the recycler is the one paying, so they're the
one confirming the payment went through.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.payment import PaymentCreateRequest, PaymentOut
from app.services import payment_service
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.utils.errors import success_response

router = APIRouter()


@router.post("", status_code=201)
def create_payment(
    payload: PaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payment = payment_service.create_payment(db, current_user, payload)
    return success_response(PaymentOut.model_validate(payment).model_dump(mode="json"))
