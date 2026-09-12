from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.notification import Notification


def notify_once(user_id, event_key, message, booking_id=None):
    if Notification.query.filter_by(event_key=event_key).first():
        return
    db.session.add(Notification(
        user_id=user_id,
        booking_id=booking_id,
        event_key=event_key,
        message=message,
    ))
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()


def mark_booking_request_read(booking_id, user_id):
    """Mark the original provider booking request as read, if it exists."""
    notification = Notification.query.filter_by(
        user_id=user_id,
        booking_id=booking_id,
        event_key=f"booking:{booking_id}:requested",
    ).first()
    if notification:
        notification.is_read = True
