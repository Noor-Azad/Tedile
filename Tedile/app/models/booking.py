from datetime import datetime, timezone
import hashlib

from flask import current_app

from app.extensions import db


class Booking(db.Model):
    """A customer's booking request for a provider's service."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False)

    status = db.Column(db.String(40), default="pending")  # pending | confirmed | completed | cancelled
    scheduled_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    customer_latitude = db.Column(db.Float)
    customer_longitude = db.Column(db.Float)
    customer_location_label = db.Column(db.String(160))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def public_reference(self):
        digest = hashlib.sha256(
            f"{current_app.config['SECRET_KEY']}:{self.id}".encode()
        ).hexdigest()
        return f"bk_{digest[:20]}"

    def to_customer_dto(self, provider, service):
        return {
            "reference": self.public_reference,
            "provider": {"id": provider.profile_code, "name": provider.name},
            "service": {"name": service.name, "slug": service.slug},
            "status": self.status,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "notes": self.notes,
        }

    def to_provider_dto(self, service, customer):
        return {
            "reference": self.public_reference,
            "customer_name": customer.name,
            "service": {"name": service.name, "slug": service.slug},
            "status": self.status,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "notes": self.notes,
            "customer_location_label": self.customer_location_label,
            "customer_location_available": self.customer_latitude is not None and self.customer_longitude is not None,
        }
