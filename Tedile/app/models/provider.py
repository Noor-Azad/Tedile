from datetime import datetime, timezone

from app.crypto import EncryptedString
from app.extensions import db


class Provider(db.Model):
    """A local service provider (plumber, electrician, tutor, etc.).

    See docs/DATA_ACCESS_POLICY.md for which fields are public, authenticated,
    or private, and which routes are allowed to return them.
    """

    __tablename__ = "providers"

    id = db.Column(db.Integer, primary_key=True)
    profile_code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120))
    phone = db.Column(EncryptedString())  # encrypted at rest; private field, see to_contact_dto()
    whatsapp = db.Column(EncryptedString())  # encrypted at rest; private field, see to_contact_dto()

    city = db.Column(db.String(120), index=True)
    state = db.Column(db.String(120), index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    hourly_rate = db.Column(db.Numeric(10, 2))
    experience_years = db.Column(db.Integer, default=0)
    jobs_completed = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    reviews_count = db.Column(db.Integer, default=0)

    verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    blocked_at = db.Column(db.DateTime)
    blocked_reason = db.Column(db.Text)
    availability = db.Column(db.String(80), default="available")  # available | busy | offline
    profile_photo_url = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def to_public_dto(self):
        """Public/discovery response for search & browse endpoints.

        Deliberately excludes: internal `id`, phone, whatsapp, and exact
        latitude/longitude. `id` here is the public `profile_code`, not the
        database primary key.
        """
        return {
            "id": self.profile_code,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "hourly_rate": float(self.hourly_rate) if self.hourly_rate is not None else None,
            "experience_years": self.experience_years,
            "jobs_completed": self.jobs_completed,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "verified": self.verified,
            "availability": self.availability,
            "profile_photo_url": self.profile_photo_url,
        }

    def to_contact_dto(self):
        """Private contact details. Only return this after an authorization
        check (e.g. an existing confirmed/completed booking) — see
        app/routes/customer.py::provider_contact.
        """
        return {"name": self.name, "phone": self.phone, "whatsapp": self.whatsapp}

    def to_provider_owner_dto(self):
        """Provider's own profile; never used by public endpoints."""
        return {
            "profile_code": self.profile_code,
            "name": self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "city": self.city,
            "state": self.state,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly_rate": float(self.hourly_rate) if self.hourly_rate is not None else None,
            "experience_years": self.experience_years,
            "jobs_completed": self.jobs_completed,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "verified": self.verified,
            "is_active": self.is_active,
            "blocked_at": self.blocked_at.isoformat() if self.blocked_at else None,
            "blocked_reason": self.blocked_reason,
            "availability": self.availability,
            "profile_photo_url": self.profile_photo_url,
        }

    def to_admin_dto(self):
        """Administrative provider view; only admin routes may return this."""
        return {
            "id": self.id,
            "profile_code": self.profile_code,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "phone": self.phone,
            "whatsapp": self.whatsapp,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "hourly_rate": float(self.hourly_rate) if self.hourly_rate is not None else None,
            "experience_years": self.experience_years,
            "jobs_completed": self.jobs_completed,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "verified": self.verified,
            "is_active": self.is_active,
            "blocked_at": self.blocked_at.isoformat() if self.blocked_at else None,
            "blocked_reason": self.blocked_reason,
            "availability": self.availability,
            "profile_photo_url": self.profile_photo_url,
        }
