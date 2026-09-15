"""
routers/recyclers.py
----------------------
GET /api/recyclers               -> list all recyclers (public directory info)
GET /api/recyclers/{recycler_id}  -> one recycler's details
GET /api/recyclers/match          -> deterministic matches for a given lot

IMPORTANT: the /match route is defined BEFORE /{recycler_id} below.
FastAPI matches routes in the order they're registered, and "/match"
would otherwise be swallowed by "/{recycler_id}" (which would treat
the literal word "match" as a recycler_id). This ordering is required,
not stylistic.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.recycler import RecyclerMatchOut
from app.services import recycler_service, lot_service
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.utils.errors import success_response

router = APIRouter()


@router.get("/match")
def match_recyclers(
    lot_id: str = Query(..., description="The lot to find matching recyclers for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Finds and ranks recyclers eligible to take a given lot. Restricted
    to the lot's own collector (or an admin) -- same ownership rule as
    viewing the lot itself, since match results reveal details about
    the lot (its material/location).
    """
    lot = lot_service.get_lot_with_authorization(db, lot_id, current_user)
    matches = recycler_service.match_recyclers_for_lot(db, lot)
    data = [RecyclerMatchOut(**m).model_dump(mode="json") for m in matches]
    return success_response(data)


@router.get("")
def list_recyclers(db: Session = Depends(get_db)):
    recyclers = recycler_service.list_recyclers(db)
    return success_response([recycler_service.serialize_recycler(r) for r in recyclers])


@router.get("/{recycler_id}")
def get_recycler(recycler_id: str, db: Session = Depends(get_db)):
    recycler = recycler_service.get_recycler_or_404(db, recycler_id)
    return success_response(recycler_service.serialize_recycler(recycler))
