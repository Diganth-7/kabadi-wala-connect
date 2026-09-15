"""
services/notification_service.py
------------------------------------
Notifications are never created directly by users -- they're generated
by OTHER services (pickup_service, handover_service, payment_service)
in response to real events. `create_notification()` here is the one
shared helper all of them call, so notification-creation logic (and
its DB commit) lives in exactly one place.

DESIGN DECISION: all notifications in this app go to the COLLECTOR,
not the recycler. The events listed in the spec (pickup accepted/
rejected/arriving, handover completed, payment recorded) are all
things that affect the collector's lot or money -- consistent with
how earlier phases already treat the collector as the primary "end
user" being kept informed (e.g. GET /api/earnings is collector-only).
A recycler-facing notification stream could be added the same way
later without restructuring anything here.
"""

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.utils.errors import AppError


def create_notification(db: Session, user_id: str, title: str, message: str, type: str) -> Notification:
    """Creates and saves a notification. Commits independently, since
    this always runs after the triggering action has already succeeded
    and committed -- a notification failing shouldn't be able to roll
    back the real business event that caused it."""
    notification = Notification(user_id=user_id, title=title, message=message, type=type)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def list_notifications_for_user(db: Session, current_user: User) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


def mark_as_read(db: Session, notification_id: str, current_user: User) -> Notification:
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise AppError(code="NOTIFICATION_NOT_FOUND", message="Notification not found.", status_code=404)

    if notification.user_id != current_user.id:
        raise AppError(code="FORBIDDEN", message="You do not have permission to modify this notification.", status_code=403)

    notification.read = True
    db.commit()
    db.refresh(notification)
    return notification
