"""
routers/pickups.py
--------------------
POST  /api/pickups              -> request a pickup (COLLECTOR only, for their own lot)
GET   /api/pickups                -> list pickups (role-based)
GET   /api/pickups/{pickup_id}     -> view one pickup (owner collector, assigned recycler, or admin)
PATCH /api/pickups/{pickup_id}/status -> transition status (assigned recycler or admin only)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.pickup import PickupCreateRequest, PickupStatusUpdateRequest, PickupOut, LocationOut
from app.services import pickup_service
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.utils.errors import success_response

router = APIRouter()


def _serialize_pickup(pickup) -> dict:
    out = PickupOut(
        id=pickup.id,
        lot_id=pickup.lot_id,
        collector_id=pickup.collector_id,
        recycler_id=pickup.recycler_id,
        status=pickup.status,
        pickup_location=LocationOut(latitude=pickup.pickup_latitude, longitude=pickup.pickup_longitude),
        created_at=pickup.created_at,
        updated_at=pickup.updated_at,
    )
    return out.model_dump(mode="json")


@router.post("", status_code=201)
def create_pickup(
    payload: PickupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COLLECTOR)),
):
    pickup = pickup_service.create_pickup(db, current_user, payload)
    return success_response(_serialize_pickup(pickup))


@router.get("")
def list_pickups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pickups = pickup_service.list_pickups_for_user(db, current_user)
    return success_response([_serialize_pickup(p) for p in pickups])


@router.get("/{pickup_id}")
def get_pickup(
    pickup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pickup = pickup_service.get_pickup_with_authorization(db, pickup_id, current_user)
    return success_response(_serialize_pickup(pickup))


@router.patch("/{pickup_id}/status")
def update_pickup_status(
    pickup_id: str,
    payload: PickupStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pickup = pickup_service.update_status(db, pickup_id, payload.status, current_user)
    return success_response(_serialize_pickup(pickup))
