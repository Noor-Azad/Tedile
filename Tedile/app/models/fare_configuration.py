from datetime import datetime, timezone
from decimal import Decimal

from app.extensions import db


class FareConfiguration(db.Model):
    """Versioned flat-fare configuration used to snapshot new rides."""

    __tablename__ = "fare_configurations"

    DEFAULT_BASE_FARE = Decimal("50.00")
    DEFAULT_CURRENCY = "INR"
    DEFAULT_VERSION = "v1"

    id = db.Column(db.Integer, primary_key=True)
    base_fare = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default=DEFAULT_CURRENCY)
    pricing_version = db.Column(db.String(40), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    @classmethod
    def current(cls):
        return cls.query.order_by(cls.id.desc()).first()

    @classmethod
    def default_snapshot(cls):
        return {
            "base_fare": cls.DEFAULT_BASE_FARE,
            "currency": cls.DEFAULT_CURRENCY,
            "pricing_version": cls.DEFAULT_VERSION,
        }

    @classmethod
    def current_snapshot(cls):
        configuration = cls.current()
        if not configuration:
            return cls.default_snapshot()
        return {
            "base_fare": Decimal(configuration.base_fare).quantize(Decimal("0.01")),
            "currency": configuration.currency,
            "pricing_version": configuration.pricing_version,
        }

    @classmethod
    def ensure_default(cls):
        configuration = cls.current()
        if configuration:
            return configuration
        configuration = cls(
            base_fare=cls.DEFAULT_BASE_FARE,
            currency=cls.DEFAULT_CURRENCY,
            pricing_version=cls.DEFAULT_VERSION,
        )
        db.session.add(configuration)
        return configuration
