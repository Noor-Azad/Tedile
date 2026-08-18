import json

from app.extensions import db


class ProviderService(db.Model):
    """Join table: one row per provider/service relationship (many-to-many)."""

    __tablename__ = "provider_services"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("providers.id"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id"), nullable=False, index=True)
    sub_services = db.Column(db.Text)  # JSON-encoded list, kept as text for SQLite/Postgres portability
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    blocked_at = db.Column(db.DateTime)
    blocked_reason = db.Column(db.Text)

    def get_sub_services(self):
        if not self.sub_services:
            return []
        try:
            return json.loads(self.sub_services)
        except (TypeError, ValueError):
            return []

    def set_sub_services(self, values):
        self.sub_services = json.dumps(list(values or []))

    def to_public_dto(self, service):
        return {
            "service": service.to_public_dto(),
            "sub_services": self.get_sub_services(),
        }

    def to_admin_dto(self, provider, service):
        return {
            "provider_profile_code": provider.profile_code,
            "service": service.to_admin_dto(),
            "sub_services": self.get_sub_services(),
            "is_active": self.is_active,
            "blocked_at": self.blocked_at.isoformat() if self.blocked_at else None,
            "blocked_reason": self.blocked_reason,
        }
