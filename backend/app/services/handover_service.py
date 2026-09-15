"""
services/handover_service.py
------------------------------
Business logic for Handovers. This is where several spec rules come
together at once:

  - final_amount is ALWAYS backend-calculated (actual_weight * agreed_price)
  - duplicate handovers for the same lot are rejected (both here AND at
    the database level, via the UniqueConstraint on Handover.lot_id --
    see models/handover.py)
  - a Transaction is created automatically right after a successful handover
  - the Pickup is automatically moved to COMPLETED (reusing pickup_service's
    state machine, so the same transition rules and lot-status-syncing
    apply here too -- no duplicated logic)
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.handover import Handover
from app.models.pickup import Pickup, PickupStatus
from app.models.transaction import Transaction
from app.models.payment import PaymentStatus
from app.models.price import Price
from app.models.user import User, UserRole
from app.schemas.handover import HandoverCreateRequest
from app.services import pickup_service, notification_service
from app.utils.errors import AppError


def _is_assigned_recycler(pickup: Pickup, current_user: User) -> bool:
    return current_user.role == UserRole.RECYCLER and pickup.recycler.user_id == current_user.id


def create_handover(db: Session, current_user: User, payload: HandoverCreateRequest) -> Handover:
    pickup = db.query(Pickup).filter(Pickup.id == payload.pickup_id).first()
    if not pickup:
        raise AppError(code="PICKUP_NOT_FOUND", message="Pickup not found.", status_code=404)

    # Authorization: same rule as updating pickup status -- only the
    # recycler assigned to this pickup (or an admin) can complete a
    # handover for it. Makes sense: the recycler is physically there
    # receiving the scrap.
    is_admin = current_user.role == UserRole.ADMIN
    if not (_is_assigned_recycler(pickup, current_user) or is_admin):
        raise AppError(
            code="FORBIDDEN",
            message="Only the assigned recycler can record a handover for this pickup.",
            status_code=403,
        )

    if pickup.lot_id != payload.lot_id:
        raise AppError(
            code="LOT_NOT_FOUND",
            message="This pickup does not belong to the given lot.",
            status_code=400,
        )

    if pickup.status != PickupStatus.HANDOVER:
        raise AppError(
            code="INVALID_STATUS_TRANSITION",
            message=f"A handover can only be recorded once the pickup has reached HANDOVER status (current: {pickup.status.value}).",
            status_code=400,
        )

    if payload.actual_weight <= 0:
        raise AppError(code="INVALID_WEIGHT", message="Actual weight must be greater than zero.", status_code=400)

    if payload.agreed_price <= 0:
        raise AppError(code="VALIDATION_ERROR", message="Agreed price must be greater than zero.", status_code=422)

    # The backend is the source of truth for pricing. A client may send
    # an agreed price, but it cannot send an arbitrary value outside the
    # configured price range for that material. This protects the final
    # amount calculation from manipulated frontend requests.
    price = db.query(Price).filter(Price.material_id == pickup.lot.material_id).first()
    if not price:
        raise AppError(
            code="SERVICE_UNAVAILABLE",
            message="No price configuration exists for this material.",
            status_code=503,
        )

    if payload.agreed_price < price.min_price or payload.agreed_price > price.max_price:
        raise AppError(
            code="INVALID_PRICE",
            message=f"Agreed price must be between ₹{price.min_price} and ₹{price.max_price} per kg.",
            status_code=400,
        )

    # Prevent duplicate handovers for the same lot. The database also
    # enforces this via a UniqueConstraint (models/handover.py), but
    # checking here first lets us return a clean, specific error code
    # instead of a raw database integrity error.
    existing = db.query(Handover).filter(Handover.lot_id == payload.lot_id).first()
    if existing:
        raise AppError(
            code="HANDOVER_ALREADY_COMPLETED",
            message="A handover has already been recorded for this lot.",
            status_code=409,
        )

    lot = pickup.lot
    final_amount = Decimal(str(payload.actual_weight)) * payload.agreed_price

    handover = Handover(
        lot_id=payload.lot_id,
        pickup_id=payload.pickup_id,
        collector_id=pickup.collector_id,
        recycler_id=pickup.recycler_id,
        estimated_weight=lot.estimated_weight,
        actual_weight=payload.actual_weight,
        agreed_price=payload.agreed_price,
        final_amount=final_amount,
        verification_reference=payload.verification_reference,
    )
    db.add(handover)

    lot.actual_weight = payload.actual_weight

    # Create the Transaction automatically -- per spec, this happens
    # right after a successful handover, not as a separate API call.
    transaction = Transaction(
        lot_id=lot.id,
        collector_id=pickup.collector_id,
        recycler_id=pickup.recycler_id,
        material_name=lot.material.display_name,
        weight=payload.actual_weight,
        amount=final_amount,
        payment_method=None,  # chosen later, in Phase 9's payment flow
        payment_status=PaymentStatus.PENDING,
    )
    db.add(transaction)

    db.commit()
    db.refresh(handover)

    notification_service.create_notification(
        db, pickup.collector_id,
        title="Handover completed",
        message=f"Your handover of {payload.actual_weight}kg {lot.material.display_name} for \u20b9{final_amount} has been recorded.",
        type="HANDOVER_COMPLETED",
    )

    # Move the pickup to COMPLETED. Reusing pickup_service.update_status
    # means the same state-machine validation and lot-status-syncing
    # (lot -> COMPLETED) applies here, instead of duplicating that logic.
    pickup_service.update_status(db, pickup.id, PickupStatus.COMPLETED, current_user)

    return handover
