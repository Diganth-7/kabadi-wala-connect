"""
routers/lots.py
----------------
POST /api/lots        -> create a lot (COLLECTOR only)
GET  /api/lots         -> list lots (role-based: own for collectors, all for admin)
GET  /api/lots/{lot_id} -> view one lot (owner collector or admin only)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.lot import LotCreateRequest
from app.services import lot_service
from app.auth.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.utils.errors import success_response

router = APIRouter()


@router.post("", status_code=201)
def create_lot(
    payload: LotCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.COLLECTOR)),
):
    """
    Only COLLECTORS can create lots. The lot's collector_id always comes
    from the logged-in user (current_user.id) -- never from the request
    body, so there's no way to create a lot "as" someone else.
    """
    lot = lot_service.create_lot(db, current_user, payload)
    return success_response(lot_service.serialize_lot(lot))


@router.get("")
def list_lots(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lots = lot_service.list_lots_for_user(db, current_user)
    return success_response([lot_service.serialize_lot(lot) for lot in lots])


@router.get("/{lot_id}")
def get_lot(
    lot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lot = lot_service.get_lot_with_authorization(db, lot_id, current_user)
    return success_response(lot_service.serialize_lot(lot))
