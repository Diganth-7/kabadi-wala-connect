"""
services/pickup_service.py
----------------------------
Business logic for Pickups, including the status transition STATE
MACHINE that enforces the exact flow from the spec:

  REQUESTED -> ACCEPTED -> ASSIGNED -> ON_THE_WAY -> ARRIVED -> HANDOVER -> COMPLETED

  with CANCELLED reachable from REQUESTED/ACCEPTED/ASSIGNED/ON_THE_WAY.

Any transition not explicitly listed in ALLOWED_TRANSITIONS is rejected
-- e.g. COMPLETED -> REQUESTED fails because COMPLETED's allowed set is
empty.

WHO CAN DO WHAT (a judgment call, since the spec doesn't spell this out
in full detail):
- Only the COLLECTOR who owns the lot can create a pickup request for it.
- Only the RECYCLER assigned to a pickup (or an ADMIN) can update its
  status. This matches the spec's description of the Recycler role
  ("accept/reject requests," "update pickup status") -- collectors
  request pickups but don't drive them through the workflow themselves.
"""

from sqlalchemy.orm import Session

from app.models.pickup import Pickup, PickupStatus
from app.models.lot import Lot, LotStatus
from app.models.user import User, UserRole
from app.schemas.pickup import PickupCreateRequest
from app.services import recycler_service, notification_service
from app.utils.errors import AppError

# The state machine: for each status, which statuses it's allowed to move to.
# A transition not listed here (e.g. COMPLETED -> anything) is rejected.
ALLOWED_TRANSITIONS: dict[PickupStatus, set[PickupStatus]] = {
    PickupStatus.REQUESTED: {PickupStatus.ACCEPTED, PickupStatus.CANCELLED},
    PickupStatus.ACCEPTED: {PickupStatus.ASSIGNED, PickupStatus.CANCELLED},
    PickupStatus.ASSIGNED: {PickupStatus.ON_THE_WAY, PickupStatus.CANCELLED},
    PickupStatus.ON_THE_WAY: {PickupStatus.ARRIVED, PickupStatus.CANCELLED},
    PickupStatus.ARRIVED: {PickupStatus.HANDOVER},
    PickupStatus.HANDOVER: {PickupStatus.COMPLETED},
    PickupStatus.COMPLETED: set(),  # terminal -- nothing can follow
    PickupStatus.CANCELLED: set(),  # terminal -- nothing can follow
}

# Lots don't have a distinct status for every pickup step (there's no
# separate LotStatus for "ASSIGNED" or "ON_THE_WAY", for example) -- we
# only sync the lot's status at the pickup transitions that actually
# correspond to a meaningful change in the lot's own lifecycle.
LOT_STATUS_SYNC: dict[PickupStatus, LotStatus] = {
    PickupStatus.ACCEPTED: LotStatus.ACCEPTED,
    PickupStatus.HANDOVER: LotStatus.HANDOVER,
    PickupStatus.COMPLETED: LotStatus.COMPLETED,
    PickupStatus.CANCELLED: LotStatus.CREATED,  # reverts so the collector can request pickup again
}


def create_pickup(db: Session, collector: User, payload: PickupCreateRequest) -> Pickup:
    lot = db.query(Lot).filter(Lot.id == payload.lot_id).first()
    if not lot:
        raise AppError(code="LOT_NOT_FOUND", message="Lot not found.", status_code=404)

    if lot.collector_id != collector.id:
        raise AppError(code="FORBIDDEN", message="You can only request pickups for your own lots.", status_code=403)

    if lot.status != LotStatus.CREATED:
        raise AppError(
            code="INVALID_STATUS_TRANSITION",
            message=f"This lot is not available for a new pickup request (current status: {lot.status.value}).",
            status_code=400,
        )

    recycler = recycler_service.get_recycler_or_404(db, payload.recycler_id)
    if not recycler.authorized:
        raise AppError(code="UNAUTHORIZED_RECYCLER", message="This recycler is not authorized.", status_code=403)

    pickup = Pickup(
        lot_id=lot.id,
        collector_id=collector.id,
        recycler_id=recycler.id,
        status=PickupStatus.REQUESTED,
        pickup_latitude=payload.pickup_location.latitude,
        pickup_longitude=payload.pickup_location.longitude,
    )
    db.add(pickup)

    lot.status = LotStatus.PICKUP_REQUESTED

    db.commit()
    db.refresh(pickup)
    # No notification here: the spec's notification list (Phase 10) starts
    # at "Pickup accepted", not creation itself -- see update_status()
    # below for where notifications are actually generated.
    return pickup


def get_pickup_or_404(db: Session, pickup_id: str) -> Pickup:
    pickup = db.query(Pickup).filter(Pickup.id == pickup_id).first()
    if not pickup:
        raise AppError(code="PICKUP_NOT_FOUND", message="Pickup not found.", status_code=404)
    return pickup


def _is_assigned_recycler(pickup: Pickup, current_user: User) -> bool:
    return current_user.role == UserRole.RECYCLER and pickup.recycler.user_id == current_user.id


def get_pickup_with_authorization(db: Session, pickup_id: str, current_user: User) -> Pickup:
    """
    A pickup is visible to: the collector who owns it, the recycler
    assigned to it, or an admin. Nobody else.
    """
    pickup = get_pickup_or_404(db, pickup_id)

    is_owner_collector = current_user.role == UserRole.COLLECTOR and pickup.collector_id == current_user.id
    is_assigned_recycler = _is_assigned_recycler(pickup, current_user)
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_owner_collector or is_assigned_recycler or is_admin):
        raise AppError(code="FORBIDDEN", message="You do not have permission to view this pickup.", status_code=403)

    return pickup


def list_pickups_for_user(db: Session, current_user: User) -> list[Pickup]:
    """
    - COLLECTOR -> pickups for their own lots
    - RECYCLER  -> pickups assigned to their recycler business
    - ADMIN     -> every pickup
    """
    query = db.query(Pickup).order_by(Pickup.created_at.desc())

    if current_user.role == UserRole.COLLECTOR:
        return query.filter(Pickup.collector_id == current_user.id).all()

    if current_user.role == UserRole.RECYCLER:
        return [p for p in query.all() if p.recycler.user_id == current_user.id]

    if current_user.role == UserRole.ADMIN:
        return query.all()

    return []


def update_status(db: Session, pickup_id: str, new_status: PickupStatus, current_user: User) -> Pickup:
    """
    Transitions a pickup to a new status, enforcing:
      1. Only the assigned recycler (or an admin) may do this.
      2. The transition must be allowed by the state machine above.
    """
    pickup = get_pickup_or_404(db, pickup_id)

    is_assigned_recycler = _is_assigned_recycler(pickup, current_user)
    is_admin = current_user.role == UserRole.ADMIN
    if not (is_assigned_recycler or is_admin):
        raise AppError(
            code="FORBIDDEN",
            message="Only the assigned recycler can update this pickup's status.",
            status_code=403,
        )

    current_status = pickup.status
    allowed_next = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed_next:
        raise AppError(
            code="INVALID_STATUS_TRANSITION",
            message=f"Cannot change pickup status from {current_status.value} to {new_status.value}.",
            status_code=400,
        )

    pickup.status = new_status

    # Keep the parent Lot's status in sync at the meaningful checkpoints.
    if new_status in LOT_STATUS_SYNC:
        pickup.lot.status = LOT_STATUS_SYNC[new_status]

    db.commit()
    db.refresh(pickup)

    _notify_status_change(db, pickup, current_status, new_status)

    return pickup


def _notify_status_change(db: Session, pickup: Pickup, previous_status: PickupStatus, new_status: PickupStatus) -> None:
    """
    Generates a notification for the collector when a pickup transition
    is one of the events the spec explicitly lists: "Pickup accepted,"
    "Pickup rejected," "Pickup arriving." Other transitions (ASSIGNED,
    ARRIVED, HANDOVER) don't have a listed notification of their own --
    HANDOVER's real "Handover completed" notification fires separately,
    from handover_service, once the Handover record actually exists.
    """
    material_name = pickup.lot.material.display_name

    if new_status == PickupStatus.ACCEPTED:
        notification_service.create_notification(
            db, pickup.collector_id,
            title="Pickup accepted",
            message=f"Your pickup request for {material_name} has been accepted.",
            type="PICKUP_ACCEPTED",
        )
    elif new_status == PickupStatus.CANCELLED:
        # A cancellation straight from REQUESTED reads as the recycler
        # declining the request outright ("rejected"); a cancellation
        # from a later stage reads as a cancellation of something
        # already underway -- different enough to warrant different wording.
        if previous_status == PickupStatus.REQUESTED:
            notification_service.create_notification(
                db, pickup.collector_id,
                title="Pickup rejected",
                message=f"Your pickup request for {material_name} was rejected.",
                type="PICKUP_REJECTED",
            )
        else:
            notification_service.create_notification(
                db, pickup.collector_id,
                title="Pickup cancelled",
                message=f"Your pickup for {material_name} was cancelled.",
                type="PICKUP_CANCELLED",
            )
    elif new_status == PickupStatus.ON_THE_WAY:
        notification_service.create_notification(
            db, pickup.collector_id,
            title="Pickup arriving",
            message=f"Your recycler is on the way to collect your {material_name}.",
            type="PICKUP_ARRIVING",
        )
