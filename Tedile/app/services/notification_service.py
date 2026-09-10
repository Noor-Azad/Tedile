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
