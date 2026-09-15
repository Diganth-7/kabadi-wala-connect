"""
services/recycler_service.py
------------------------------
Business logic for recyclers, including the deterministic recycler
MATCHING algorithm (no AI, per spec).

NOTE ON "buying_price": the spec's Recycler model doesn't include a
per-recycler price field, and Price (Phase 4) is one global price per
material shared by everyone. So for this prototype, every recycler's
"buying_price" for a material is simply that material's current market
price -- there's no per-recycler pricing yet. This is a deliberate
simplification (not a bug): it satisfies the spec's required
`buying_price` output field, and the matching math below is written so
that if per-recycler pricing is added later, the price-scoring logic
doesn't need to change -- only where the price number comes from would.
"""

from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.recycler import Recycler
from app.models.lot import Lot
from app.schemas.recycler import RecyclerOut, LocationOut
from app.services import price_service
from app.utils.errors import AppError
from app.utils.geo import haversine_km

# Match score weights (per spec) -- must add up to 100.
WEIGHT_DISTANCE = 30
WEIGHT_PRICE = 30
WEIGHT_MATERIAL_COMPATIBILITY = 20
WEIGHT_PICKUP_AVAILABILITY = 10
WEIGHT_RELIABILITY = 10

MAX_RELIABILITY_SCORE = 5.0  # reliability_score is stored on a 0-5 scale (see models/recycler.py)


def list_recyclers(db: Session) -> list[Recycler]:
    return db.query(Recycler).options(joinedload(Recycler.accepted_materials)).order_by(Recycler.name).all()


def get_recycler_or_404(db: Session, recycler_id: str) -> Recycler:
    recycler = (
        db.query(Recycler)
        .options(joinedload(Recycler.accepted_materials))
        .filter(Recycler.id == recycler_id)
        .first()
    )
    if not recycler:
        raise AppError(code="RECYCLER_NOT_FOUND", message="Recycler not found.", status_code=404)
    return recycler


def serialize_recycler(recycler: Recycler) -> dict:
    """
    Shared serializer used by both the public recyclers router and the
    admin router, so the response shape for "a recycler" is defined in
    exactly one place.
    """
    out = RecyclerOut(
        id=recycler.id,
        name=recycler.name,
        authorized=recycler.authorized,
        location=LocationOut(latitude=recycler.latitude, longitude=recycler.longitude),
        service_radius_km=recycler.service_radius_km,
        pickup_available=recycler.pickup_available,
        accepted_materials=recycler.accepted_materials,
        reliability_score=recycler.reliability_score,
    )
    return out.model_dump(mode="json")


def _material_score(recycler: Recycler, material_id: str) -> float:
    """
    1.0 if the recycler accepts this material, else 0.0. In practice
    this is always 1.0 for any recycler reaching the scoring step,
    since material compatibility is also used as a hard filter before
    scoring even starts (see match_recyclers_for_lot below) -- but
    keeping it as its own scoring component matches the spec's
    weighting table exactly, and would allow "how well they accept it"
    shades of compatibility to be added later without restructuring.
    """
    accepted_ids = {m.id for m in recycler.accepted_materials}
    return 1.0 if material_id in accepted_ids else 0.0


def match_recyclers_for_lot(db: Session, lot: Lot) -> list[dict]:
    """
    Returns a ranked list of recyclers eligible to take this lot,
    following the spec's deterministic algorithm:

      1. Authorization        -- unauthorized recyclers are excluded entirely
      2. Material compatibility -- must accept the lot's material, or excluded
      3. Distance              -- must be within the recycler's service_radius_km, or excluded
      4. Buying price          -- scored (see note above)
      5. Pickup availability   -- scored
      6. Reliability           -- scored

    Raises AppError(NO_RECYCLER_FOUND) if nobody qualifies.
    """
    current_price = price_service.get_current_price(db, lot.material_id)

    candidates = (
        db.query(Recycler)
        .options(joinedload(Recycler.accepted_materials))
        .filter(Recycler.authorized == True)  # noqa: E712 (explicit == True reads clearly for SQLAlchemy filters)
        .all()
    )

    results = []
    for recycler in candidates:
        # --- Hard filters (disqualify entirely, not just score lower) ---
        if _material_score(recycler, lot.material_id) == 0.0:
            continue

        distance_km = haversine_km(lot.latitude, lot.longitude, recycler.latitude, recycler.longitude)
        if distance_km > recycler.service_radius_km:
            continue

        # --- Weighted scoring (0-100) ---
        distance_score = max(0.0, 1 - (distance_km / recycler.service_radius_km)) * WEIGHT_DISTANCE
        price_score = 1.0 * WEIGHT_PRICE  # every recycler currently offers the same market price -- see module docstring
        material_score = 1.0 * WEIGHT_MATERIAL_COMPATIBILITY  # already passed the hard filter above
        pickup_score = (1.0 if recycler.pickup_available else 0.0) * WEIGHT_PICKUP_AVAILABILITY
        reliability_score = (recycler.reliability_score / MAX_RELIABILITY_SCORE) * WEIGHT_RELIABILITY

        match_score = round(distance_score + price_score + material_score + pickup_score + reliability_score, 2)

        results.append({
            "recycler_id": recycler.id,
            "name": recycler.name,
            "distance_km": round(distance_km, 2),
            "buying_price": float(current_price),
            "pickup_available": recycler.pickup_available,
            "authorized": recycler.authorized,
            "accepted_materials": recycler.accepted_materials,
            "match_score": match_score,
        })

    if not results:
        raise AppError(
            code="NO_RECYCLER_FOUND",
            message="No authorized recycler currently accepts this material within range.",
            status_code=404,
        )

    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results
