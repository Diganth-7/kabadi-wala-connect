"""
routers/notifications.py
----------------------------
GET   /api/notifications                    -> list your own notifications
PATCH /api/notifications/{notification_id}/read -> mark one as read

Notifications are generated automatically by other services (pickup,
handover, payment) -- there's no POST endpoint here, by design.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.notification import NotificationOut
from app.services import notification_service
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.utils.errors import success_response

router = APIRouter()


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications = notification_service.list_notifications_for_user(db, current_user)
    data = [NotificationOut.model_validate(n).model_dump(mode="json") for n in notifications]
    return success_response(data)


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = notification_service.mark_as_read(db, notification_id, current_user)
    return success_response(NotificationOut.model_validate(notification).model_dump(mode="json"))
