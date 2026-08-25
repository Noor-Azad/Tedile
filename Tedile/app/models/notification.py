from datetime import datetime, timezone

from app.extensions import db


class Notification(db.Model):
    """Persistent in-app notification owned by one authenticated User."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    bike_ride_id = db.Column(db.Integer, db.ForeignKey("bike_rides.id"), nullable=True, index=True)
    event_type = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    read_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "bike_ride_id",
            "event_type",
            name="uq_notification_user_ride_event",
        ),
    )

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.now(timezone.utc)
