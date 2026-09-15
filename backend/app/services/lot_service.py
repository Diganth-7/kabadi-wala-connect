"""
services/lot_service.py
-------------------------
Business logic for Scrap Lots.

The most important function here is `create_lot()`, which calculates
`estimated_value` itself (estimated_weight × current_price) — this is
the actual enforcement of "the backend is the source of truth for
price," not just a documentation comment. Nothing about this
calculation can be influenced by what the client sends.
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.lot import Lot, LotStatus
from app.models.user import User, UserRole
from app.schemas.lot import LotCreateRequest, LotOut, LocationOut
from app.services import price_service
from app.utils.errors import AppError


def create_lot(db: Session, collector: User, payload: LotCreateRequest) -> Lot:
    """
    Creates a new lot for the given collector.

    Validation order matters a little here: we check the weight first
    (cheap, no DB query needed) before looking up the material's price
    (a DB query) — fail fast on the cheapest check first.
    """
    if payload.estimated_weight <= 0:
        raise AppError(code="INVALID_WEIGHT", message="Weight must be greater than zero.", status_code=400)

    # Raises AppError(INVALID_MATERIAL) itself if material_id isn't real.
    current_price = price_service.get_current_price(db, payload.material_id)

    # Decimal(str(...)) avoids floating-point precision issues when
    # converting the incoming float weight into a Decimal for money math.
    estimated_value = Decimal(str(payload.estimated_weight)) * current_price

    lot = Lot(
        collector_id=collector.id,
        material_id=payload.material_id,
        estimated_weight=payload.estimated_weight,
        condition=payload.condition,
        estimated_value=estimated_value,
        status=LotStatus.CREATED,
        latitude=payload.location.latitude,
        longitude=payload.location.longitude,
        photo_url=payload.photo_url,
    )
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot


def get_lot_or_404(db: Session, lot_id: str) -> Lot:
    lot = db.query(Lot).filter(Lot.id == lot_id).first()
    if not lot:
        raise AppError(code="LOT_NOT_FOUND", message="Lot not found.", status_code=404)
    return lot


def get_lot_with_authorization(db: Session, lot_id: str, current_user: User) -> Lot:
    """
    Fetches a single lot AND checks the requester is allowed to see it.

    Rule: a collector can only see their OWN lots; an admin can see any
    lot. (Recyclers don't get generic lot access yet — in Phase 6/7
    they'll see lots through the recycler-matching and pickup-request
    flow instead, which is a more deliberate, narrower form of access
    than "any recycler can look up any lot by ID.")
    """
    lot = get_lot_or_404(db, lot_id)

    is_owner = current_user.role == UserRole.COLLECTOR and lot.collector_id == current_user.id
    is_admin = current_user.role == UserRole.ADMIN

    if not (is_owner or is_admin):
        raise AppError(code="FORBIDDEN", message="You do not have permission to view this lot.", status_code=403)

    return lot


def list_lots_for_user(db: Session, current_user: User) -> list[Lot]:
    """
    Role-based listing:
    - COLLECTOR -> only their own lots
    - ADMIN     -> every lot
    - RECYCLER  -> none yet via this generic endpoint (see note above)
    """
    query = db.query(Lot).order_by(Lot.created_at.desc())

    if current_user.role == UserRole.COLLECTOR:
        return query.filter(Lot.collector_id == current_user.id).all()

    if current_user.role == UserRole.ADMIN:
        return query.all()

    raise AppError(
        code="FORBIDDEN",
        message="Recyclers cannot browse all lots directly yet.",
        status_code=403,
    )


def serialize_lot(lot: Lot) -> dict:
    """
    Converts a Lot ORM object into the exact response shape the spec
    wants — most notably, nesting flat latitude/longitude columns into
    a `location: {latitude, longitude}` object.
    """
    out = LotOut(
        id=lot.id,
        collector_id=lot.collector_id,
        material_id=lot.material_id,
        estimated_weight=lot.estimated_weight,
        actual_weight=lot.actual_weight,
        condition=lot.condition,
        estimated_value=lot.estimated_value,
        status=lot.status,
        location=LocationOut(latitude=lot.latitude, longitude=lot.longitude),
        photo_url=lot.photo_url,
        created_at=lot.created_at,
        updated_at=lot.updated_at,
    )
    return out.model_dump(mode="json")
