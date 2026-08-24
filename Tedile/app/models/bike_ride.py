from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import update

from app.extensions import db


class BikeRide(db.Model):
    """A simple customer-to-rider trip with a controlled lifecycle."""

    __tablename__ = "bike_rides"

    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    rider_id = db.Column(db.Integer, db.ForeignKey("riders.id"), nullable=True, index=True)
    pickup_address = db.Column(db.String(500), nullable=False)
    pickup_latitude = db.Column(db.Float, nullable=False)
    pickup_longitude = db.Column(db.Float, nullable=False)
    destination_address = db.Column(db.String(500), nullable=False)
    destination_latitude = db.Column(db.Float, nullable=False)
    destination_longitude = db.Column(db.Float, nullable=False)
    customer_note = db.Column(db.Text)
    estimated_fare = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("50.00"))
    final_fare = db.Column(db.Numeric(10, 2))
    fare_currency = db.Column(db.String(3), nullable=False, default="INR")
    pricing_version = db.Column(db.String(40), nullable=False, default="v1")
    pricing_base_fare = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal("50.00"))
    status = db.Column(db.String(20), nullable=False, default=REQUESTED, index=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    accepted_at = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    ALLOWED_TRANSITIONS = {
        REQUESTED: {ACCEPTED, CANCELLED},
        ACCEPTED: {IN_PROGRESS, CANCELLED},
        IN_PROGRESS: {COMPLETED},
        COMPLETED: set(),
        CANCELLED: set(),
    }

    def transition_to(self, new_status):
        if new_status not in self.ALLOWED_TRANSITIONS.get(self.status, set()):
            raise ValueError(f"Invalid ride status transition: {self.status} -> {new_status}")
        now = datetime.now(timezone.utc)
        self.status = new_status
        if new_status == self.ACCEPTED:
            self.accepted_at = now
        elif new_status == self.IN_PROGRESS:
            self.started_at = now
        elif new_status == self.COMPLETED:
            self.final_fare = Decimal(self.estimated_fare).quantize(Decimal("0.01"))
            self.completed_at = now
        elif new_status == self.CANCELLED:
            self.cancelled_at = now

    @classmethod
    def claim(cls, ride_id, rider_id):
        """Atomically claim a requested ride for one approved rider."""
        result = db.session.execute(
            update(cls)
            .where(cls.id == ride_id, cls.status == cls.REQUESTED, cls.rider_id.is_(None))
            .values(rider_id=rider_id, status=cls.ACCEPTED, accepted_at=datetime.now(timezone.utc))
        )
        return result.rowcount == 1

    def to_customer_dto(self, rider=None, rider_user=None):
        return {
            "id": self.id,
            "pickup_address": self.pickup_address,
            "destination_address": self.destination_address,
            "status": self.status,
            "customer_note": self.customer_note,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rider": (
                {"name": rider_user.name, "bike_make_model": rider.bike_make_model}
                if rider and rider_user
                else None
            ),
        }
