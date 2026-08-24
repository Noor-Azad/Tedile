from datetime import datetime, timezone

from app.crypto import EncryptedString
from app.extensions import db


class Rider(db.Model):
    """A customer's rider application and approved rider profile."""

    __tablename__ = "riders"

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True)
    bike_make_model = db.Column(db.String(160), nullable=False)
    bike_registration_number = db.Column(EncryptedString(), nullable=False)
    license_number = db.Column(EncryptedString(), nullable=False)
    license_expiry_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=PENDING, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_admin_dto(self, user):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "bike_make_model": self.bike_make_model,
            "bike_registration_number": self.bike_registration_number,
            "license_number": self.license_number,
            "license_expiry_date": self.license_expiry_date.isoformat(),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
