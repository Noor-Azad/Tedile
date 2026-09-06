"""Create deterministic, clearly synthetic data for local Development testing.

This script is intentionally separate from the reference catalog seed and is
guarded against non-Development databases. It only creates missing records;
it never deletes or rewrites existing data.

Usage (from Tedile/):
    python -m database.seed_dev
"""
from urllib.parse import urlparse

from app import create_app
from app.extensions import db
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.service import Service
from app.models.user import User


DEV_PASSWORD = "DevOnlyPassword123!"
SYNTHETIC_PROVIDERS = [
    ("DEV-PLUMBER-01", "dev.plumber01@tedile.test", "Dev Plumber 1", "plumber", 22.5726, 88.3639),
    ("DEV-ELECTRICIAN-01", "dev.electrician01@tedile.test", "Dev Electrician 1", "electrician", 22.5958, 88.2636),
    ("DEV-WELDER-SMOKE-01", "dev.welder01@tedile.test", "Dev Welder Smoke 1", "welder", 22.5204, 88.3500),
    ("DEV-AC-REPAIR-SMOKE-01", "dev.acrepair01@tedile.test", "Dev AC/Fridge Repair Smoke 1", "ac-repair", 22.5726, 88.3639),
]


def _assert_local_development(app):
    if app.config.get("APP_ENV", "development") != "development":
        raise RuntimeError("seed_dev.py may run only with APP_ENV=development")
    parsed = urlparse(app.config["SQLALCHEMY_DATABASE_URI"])
    if parsed.scheme not in {"postgresql", "postgres"} or parsed.path.lstrip("/") != "tedile_dev":
        raise RuntimeError("seed_dev.py requires the local PostgreSQL database tedile_dev")
    if parsed.username != "tedile_local" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("seed_dev.py requires local PostgreSQL user tedile_local")


def seed():
    app = create_app()
    _assert_local_development(app)
    with app.app_context():
        services = {}
        for name, slug in (("Plumber", "plumber"), ("Electrician", "electrician"), ("Welder", "welder"), ("AC/Fridge Repair", "ac-repair")):
            service = Service.query.filter_by(slug=slug).first()
            if service is None:
                service = Service(name=name, slug=slug, is_active=True)
                db.session.add(service)
                db.session.flush()
            services[slug] = service

        for profile_code, email, name, slug, latitude, longitude in SYNTHETIC_PROVIDERS:
            provider = Provider.query.filter_by(profile_code=profile_code).first()
            if provider is None:
                account = User.query.filter_by(email=email).first()
                if account is None:
                    account = User(email=email, name=name, role="provider", phone="+910000000000", onboarding_completed=True)
                    account.set_password(DEV_PASSWORD)
                    db.session.add(account)
                    db.session.flush()
                provider = Provider(
                    profile_code=profile_code, user_id=account.id, first_name=name,
                    city="Kolkata", state="West Bengal", latitude=latitude,
                    longitude=longitude, hourly_rate=300, experience_years=5,
                    verified=True, is_active=True, availability="available",
                )
                db.session.add(provider)
                db.session.flush()
            relation = ProviderService.query.filter_by(provider_id=provider.id, service_id=services[slug].id).first()
            if relation is None:
                db.session.add(ProviderService(provider_id=provider.id, service_id=services[slug].id, is_active=True))

        db.session.commit()
        print("Development synthetic seed complete.")


if __name__ == "__main__":
    seed()
