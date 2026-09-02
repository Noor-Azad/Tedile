"""Create deterministic synthetic data for Tedile UAT.

This module is intentionally separate from ``seed.py`` and ``seed_dev.py``.
It is fail-closed: it can run only when the process explicitly identifies a
remote PostgreSQL UAT database.  It never deletes, truncates, or rewrites
records outside the clearly synthetic UAT namespace.

This file is code-only preparation.  Execute it only after independently
verifying the UAT target and applying migrations.
"""
from datetime import datetime, timezone
import math
import os
from urllib.parse import urlparse

from app import create_app
from app.extensions import db
from app.models.booking import Booking
from app.models.location import Location
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.review import Review
from app.models.service import Service
from app.models.user import User
from sqlalchemy import text


UAT_PASSWORD = "Test@1234"
UAT_MAPPING_MARKER = "__tedile_uat_seed__"

# These are synthetic reference points within the South Dinajpur test area.
# They deliberately cover Daulatpur, Buniadpur, Gangarampur, and Balurghat so
# UAT can exercise multiple progressive search-radius bands.
UAT_LOCATIONS = [
    ("Daulatpur", "South Dinajpur", 25.3300, 88.5250),
    ("Buniadpur", "South Dinajpur", 25.3990, 88.6200),
    ("Gangarampur", "South Dinajpur", 25.4000, 88.5250),
    ("Balurghat", "South Dinajpur", 25.2373, 88.7831),
]
# Conservative bounding box for the selected South Dinajpur test points.
SOUTH_DINAJPUR_BOUNDS = (25.15, 25.50, 88.30, 88.90)

UAT_SERVICES = (
    ("Plumber", "plumber"),
    ("Electrician", "electrician"),
    ("Welder", "welder"),
    ("AC/Fridge Repair", "ac-repair"),
)

UAT_PROVIDERS = (
    ("UAT-PLUMBER-01", "uat.plumber01@tedile.com", "UAT Plumber 1", "plumber", 25.3300, 88.5250),
    ("UAT-ELECTRICIAN-01", "uat.electrician01@tedile.com", "UAT Electrician 1", "electrician", 25.3990, 88.6200),
    ("UAT-WELDER-01", "uat.welder01@tedile.com", "UAT Welder 1", "welder", 25.4000, 88.5250),
    ("UAT-AC-REPAIR-01", "uat.acrepair01@tedile.com", "UAT AC/Fridge Repair 1", "ac-repair", 25.2373, 88.7831),
)

UAT_CUSTOMERS = (
    ("uat.customer01@tedile.com", "UAT Customer 1"),
    ("uat.customer02@tedile.com", "UAT Customer 2"),
    ("uat.customer03@tedile.com", "UAT Customer 3"),
)


def _assert_uat_target(app):
    """Refuse every target that is not positively identified as UAT."""
    if app.config.get("APP_ENV") != "uat":
        raise RuntimeError("seed_uat.py requires APP_ENV=uat")

    database_url = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    parsed = urlparse(database_url)
    database_name = parsed.path.lstrip("/")
    expected_name = app.config.get("UAT_DATABASE_NAME") or os.getenv("UAT_DATABASE_NAME")

    if parsed.scheme not in {"postgresql", "postgres"}:
        raise RuntimeError("seed_uat.py requires a PostgreSQL UAT database")
    lowered_name = database_name.lower()
    if not expected_name or database_name != expected_name or "uat" not in lowered_name:
        raise RuntimeError("seed_uat.py requires an explicitly named UAT database")
    if any(marker in lowered_name for marker in ("dev", "development", "prod", "production")):
        raise RuntimeError("seed_uat.py refuses the Development database")
    if parsed.username == "tedile_local":
        raise RuntimeError("seed_uat.py refuses the Development database user")
    if not parsed.hostname or parsed.hostname.lower() in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("seed_uat.py refuses a local or ambiguous database host")


def _assert_connected_database(app, actual_database_name):
    """Verify the database identity returned by PostgreSQL, not just the URL."""
    expected_name = app.config.get("UAT_DATABASE_NAME") or os.getenv("UAT_DATABASE_NAME")
    if not actual_database_name or actual_database_name != expected_name:
        raise RuntimeError("connected database does not match the explicitly named UAT database")


def _get_or_create_user(email, name, role):
    user = User.query.filter_by(email=email).first()
    created = user is None
    if user is not None and user.role != role:
        raise RuntimeError(f"UAT account has an unexpected role: {email}")
    if created:
        user = User(email=email, name=name, role=role, phone="+910000000000", onboarding_completed=True)
        user.set_password(UAT_PASSWORD)
        db.session.add(user)
        db.session.flush()
    return user, created


def _get_or_create_service(name, slug):
    service = Service.query.filter_by(slug=slug).first()
    created = service is None
    if service is not None and not service.is_active:
        raise RuntimeError(f"UAT service is inactive: {slug}")
    if created:
        service = Service(name=name, slug=slug, is_active=True)
        db.session.add(service)
        db.session.flush()
    return service, created


def _get_or_create_provider(profile_code, email, name, slug, latitude, longitude):
    account, account_created = _get_or_create_user(email, name, "provider")
    provider = Provider.query.filter_by(profile_code=profile_code).first()
    created = provider is None
    if created:
        provider = Provider(profile_code=profile_code, user_id=account.id, first_name=name,
                            city="Daulatpur", state="South Dinajpur", latitude=latitude,
                            longitude=longitude, hourly_rate=300, experience_years=5,
                            verified=True, is_active=True, availability="available")
        db.session.add(provider)
        db.session.flush()
    else:
        # Only canonical UAT-owned profiles may be normalized by this seed.
        if provider.user_id not in (None, account.id):
            raise RuntimeError(f"UAT provider is linked to an unexpected account: {profile_code}")
        provider.user_id = account.id
        provider.city = provider.city or "Daulatpur"
        provider.state = "South Dinajpur"
        provider.latitude = latitude
        provider.longitude = longitude
        provider.hourly_rate = provider.hourly_rate or 300
        provider.experience_years = provider.experience_years or 5
        provider.verified = True
        provider.is_active = True
        provider.availability = "available"
    return provider, created, account_created


def _get_or_create_booking(marker, customer, provider, service, status, location):
    booking = Booking.query.filter_by(notes=marker).first()
    created = booking is None
    if created:
        booking = Booking(customer_id=customer.id, provider_id=provider.id, service_id=service.id,
                          status=status, notes=marker, customer_latitude=location[2],
                          customer_longitude=location[3], customer_location_label=location[0])
        db.session.add(booking)
    elif (
        booking.customer_id != customer.id
        or booking.provider_id != provider.id
        or booking.service_id != service.id
        or booking.status != status
        or booking.customer_latitude != location[2]
        or booking.customer_longitude != location[3]
        or booking.customer_location_label != location[0]
    ):
        raise RuntimeError(f"UAT booking marker belongs to unexpected data: {marker}")
    return booking, created


def _is_uat_owned_mapping(provider, relation):
    """Only mappings explicitly marked by this seed may be normalized."""
    return (
        str(provider.profile_code).startswith("UAT-")
        and UAT_MAPPING_MARKER in relation.get_sub_services()
    )


def _mapping_plan(provider, active_relations, intended_service_id):
    """Return unknown and seed-owned extras without mutating any relation."""
    extras = [item for item in active_relations if item.service_id != intended_service_id]
    return (
        [item for item in extras if not _is_uat_owned_mapping(provider, item)],
        [item for item in extras if _is_uat_owned_mapping(provider, item)],
    )


def _ensure_provider_service(provider, service):
    """Ensure one intended active mapping without touching unknown mappings."""
    relation = ProviderService.query.filter_by(
        provider_id=provider.id, service_id=service.id
    ).first()
    if relation is None:
        relation = ProviderService(
            provider_id=provider.id, service_id=service.id, is_active=True
        )
        relation.set_sub_services([UAT_MAPPING_MARKER])
        db.session.add(relation)
        db.session.flush()
    else:
        relation.is_active = True

    active_relations = ProviderService.query.filter_by(
        provider_id=provider.id, is_active=True
    ).all()
    unknown, owned_extras = _mapping_plan(provider, active_relations, service.id)
    if unknown:
        service_ids = ", ".join(str(item.service_id) for item in unknown)
        raise RuntimeError(
            f"UAT provider has unexpected active service mapping(s): "
            f"{provider.profile_code} service_id(s) {service_ids}"
        )
    for item in owned_extras:
        item.is_active = False

    remaining = [item for item in active_relations if item.is_active]
    if len(remaining) != 1 or remaining[0].service_id != service.id:
        raise RuntimeError(
            f"UAT provider has an unexpected active service mapping: {provider.profile_code}"
        )
    return relation


def seed():
    app = create_app()
    _assert_uat_target(app)
    with app.app_context():
        actual_database_name = db.session.execute(text("SELECT current_database()")).scalar_one_or_none()
        _assert_connected_database(app, actual_database_name)
        location_counts = {"created": 0, "reused": 0}
        for city, state, latitude, longitude in UAT_LOCATIONS:
            location = Location.query.filter_by(city=city, state=state).first()
            if location is None:
                db.session.add(Location(city=city, state=state, latitude=latitude, longitude=longitude))
                location_counts["created"] += 1
            else:
                location_counts["reused"] += 1
        db.session.flush()

        services = {}
        service_counts = {"created": 0, "reused": 0}
        for name, slug in UAT_SERVICES:
            services[slug], created = _get_or_create_service(name, slug)
            service_counts["created" if created else "reused"] += 1

        providers = {}
        provider_counts = {"created": 0, "reused": 0}
        account_counts = {"created": 0, "reused": 0}
        relation_counts = {"created": 0, "reused": 0}
        for profile_code, email, name, slug, latitude, longitude in UAT_PROVIDERS:
            provider, created, account_created = _get_or_create_provider(
                profile_code, email, name, slug, latitude, longitude
            )
            providers[slug] = provider
            provider_counts["created" if created else "reused"] += 1
            account_counts["created" if account_created else "reused"] += 1
            relation = ProviderService.query.filter_by(
                provider_id=provider.id, service_id=services[slug].id
            ).first()
            relation_was_present = relation is not None
            _ensure_provider_service(provider, services[slug])
            relation_counts["reused" if relation_was_present else "created"] += 1

        customers = {}
        customer_counts = {"created": 0, "reused": 0}
        for email, name in UAT_CUSTOMERS:
            customers[email], created = _get_or_create_user(email, name, "customer")
            customer_counts["created" if created else "reused"] += 1

        bookings = []
        booking_counts = {"created": 0, "reused": 0}
        booking_specs = (
            ("[UAT-SEED:pending-plumber]", "uat.customer01@tedile.com", "plumber", "pending", UAT_LOCATIONS[0]),
            ("[UAT-SEED:completed-ac-repair]", "uat.customer02@tedile.com", "ac-repair", "completed", UAT_LOCATIONS[1]),
        )
        for marker, customer_email, slug, status, location in booking_specs:
            booking, created = _get_or_create_booking(
                marker, customers[customer_email], providers[slug], services[slug], status, location
            )
            bookings.append(booking)
            booking_counts["created" if created else "reused"] += 1

        min_lat, max_lat, min_lon, max_lon = SOUTH_DINAJPUR_BOUNDS
        for _profile_code, _email, _name, _slug, latitude, longitude in UAT_PROVIDERS:
            if not (math.isfinite(latitude) and math.isfinite(longitude)):
                raise RuntimeError("UAT provider coordinates must be finite")
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise RuntimeError("UAT provider coordinates are out of range")
            if not (min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon):
                raise RuntimeError("UAT provider coordinates are outside South Dinajpur test coverage")

        # The completed booking is deliberately left unrated so both parties
        # can exercise the real review flow. Existing UAT-owned reviews are
        # never changed or duplicated.
        review_count = Review.query.join(Booking, Review.booking_id == Booking.id).filter(
            Booking.notes.like("[UAT-SEED:%")
        ).count()
        db.session.commit()

        print("UAT synthetic seed complete.")
        print(f"customers: {customer_counts['created']} created, {customer_counts['reused']} reused")
        print(f"providers: {provider_counts['created']} created, {provider_counts['reused']} reused")
        print(f"services: {service_counts['created']} created, {service_counts['reused']} reused")
        print(f"provider-service relationships: {relation_counts['created']} created, {relation_counts['reused']} reused")
        print(f"bookings: {booking_counts['created']} created, {booking_counts['reused']} reused")
        print(f"reviews: {review_count} existing UAT reviews, no reviews created")
        print(f"locations: {location_counts['created']} created, {location_counts['reused']} reused")


if __name__ == "__main__":
    seed()
