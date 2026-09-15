"""
services/price_service.py
--------------------------
Business logic for prices. Also exposes `get_current_price()`, a small
helper other services will reuse — most importantly the LOT creation
service in Phase 5, which needs to look up "what's the current price of
this material?" to calculate `estimated_value` on the BACKEND (never
trusting a price the frontend might send).
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.price import Price
from app.models.material import Material
from app.utils.errors import AppError


def get_all_prices(db: Session) -> list[Price]:
    """Returns every material's current price, ordered by material_id."""
    return db.query(Price).order_by(Price.material_id).all()


def get_price_by_material(db: Session, material_id: str) -> Price:
    """
    Returns the Price row for one material.

    Raises AppError if the material_id doesn't correspond to a real
    material (or has no price set) — using the "INVALID_MATERIAL" code
    from the spec's error list, since that's the closest match for
    "this material_id isn't valid."
    """
    price = db.query(Price).filter(Price.material_id == material_id).first()
    if not price:
        raise AppError(
            code="INVALID_MATERIAL",
            message=f"No material found with id '{material_id}'.",
            status_code=404,
        )
    return price


def get_current_price(db: Session, material_id: str) -> Decimal:
    """
    Convenience helper for OTHER services (e.g. lot creation in Phase 5)
    that just need the current price as a number, not the full Price
    object. Reuses get_price_by_material() so the "material not found"
    validation only lives in one place.
    """
    price = get_price_by_material(db, material_id)
    return price.current_price
