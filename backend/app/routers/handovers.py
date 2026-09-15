"""
routers/handovers.py
----------------------
POST /api/handovers -> record a handover (assigned recycler or admin only)

Per spec, only creation is listed for handovers -- no GET endpoints are
required, so none are built here (keeping scope tight to what's asked).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.handover import HandoverCreateRequest, HandoverOut
from app.services import handover_service
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.utils.errors import success_response

router = APIRouter()


@router.post("", status_code=201)
def create_handover(
    payload: HandoverCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    handover = handover_service.create_handover(db, current_user, payload)
    return success_response(HandoverOut.model_validate(handover).model_dump(mode="json"))
