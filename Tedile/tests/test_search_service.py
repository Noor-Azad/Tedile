import ast
from pathlib import Path

import pytest

from app.extensions import db
from app.models.provider import Provider
from app.models.service import Service
from app.models.provider_service import ProviderService
from app.services.search_service import search_providers
from tests.conftest import create_isolated_test_app


@pytest.fixture
def app():
    flask_app = create_isolated_test_app()

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


def _make_provider(city, lat, lon, rate=300, verified=True, attach_service=True):
    provider = Provider(
        profile_code=f"P-{city}",
        first_name="Test",
        last_name=city,
        city=city,
        state="West Bengal",
        latitude=lat,
        longitude=lon,
        hourly_rate=rate,
        verified=verified,
        rating=4.5,
        phone="+911234567890",
    )
    db.session.add(provider)
    db.session.commit()
    if attach_service:
        service = Service.query.filter_by(slug="plumber").first()
        if service is None:
            service = Service(name="Plumber", slug="plumber")
            db.session.add(service)
            db.session.commit()
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id))
        db.session.commit()
    return provider


def test_search_filters_by_radius(app):
    with app.app_context():
        near = _make_provider("Malda", 25.0057449, 88.1398483)
        far = _make_provider("Delhi", 28.6139, 77.2090)

        results = search_providers(latitude=25.0057449, longitude=88.1398483, radius_km=50)

        codes = {r["id"] for r in results}
        assert near.profile_code in codes
        assert far.profile_code not in codes


def test_search_response_excludes_sensitive_fields(app):
    with app.app_context():
        provider = _make_provider("Malda", 25.0057449, 88.1398483)

        results = search_providers(latitude=25.0057449, longitude=88.1398483, radius_km=50)

        assert len(results) == 1
        record = results[0]
        assert record["id"] == provider.profile_code
        for forbidden_field in ("phone", "whatsapp", "latitude", "longitude", "profile_code", "distance_km"):
            assert forbidden_field not in record
        assert record["distance_bucket"] == "under_5km"


def test_search_filters_by_service(app):
    with app.app_context():
        service = Service.query.filter_by(slug="plumber").first()
        if service is None:
            service = Service(name="Plumber", slug="plumber")
            db.session.add(service)
            db.session.commit()

        provider = _make_provider("Kolkata", 22.5726, 88.3639)
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id))
        db.session.commit()

        other = _make_provider("Durgapur", 23.5204, 87.3119, attach_service=False)

        results = search_providers(service_slug="plumber")
        codes = {r["id"] for r in results}
        assert provider.profile_code in codes
        assert other.profile_code not in codes


def test_search_keyword_matches_service_name(app):
    with app.app_context():
        service = Service.query.filter_by(slug="electrician").first()
        if service is None:
            service = Service(name="Electrician", slug="electrician")
            db.session.add(service)
            db.session.commit()

        provider = _make_provider("Kolkata", 22.5726, 88.3639, attach_service=False)
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id))
        db.session.commit()

        results = search_providers(keyword="Electrician")

        assert provider.profile_code in {record["id"] for record in results}


def test_synthetic_ac_repair_provider_is_discoverable_from_kolkata(app):
    with app.app_context():
        service = Service.query.filter_by(slug="ac-repair").first()
        if service is None:
            service = Service(name="AC/Fridge Repair", slug="ac-repair")
            db.session.add(service)
            db.session.commit()

        provider = _make_provider("Kolkata", 22.5726, 88.3639, attach_service=False)
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id))
        db.session.commit()

        results = search_providers(
            latitude=22.5726,
            longitude=88.3639,
            service_slug="ac-repair",
            radius_km=50,
            radius_bands_km=[5, 10, 25, 50],
        )

        assert provider.profile_code in {record["id"] for record in results}


def test_synthetic_provider_seed_shape_supports_provider_service_lookup(app):
    with app.app_context():
        service = Service(name="AC/Fridge Repair", slug="ac-repair")
        provider = _make_provider("Kolkata", 22.5726, 88.3639, attach_service=False)
        db.session.add(service)
        db.session.commit()
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id, is_active=True))
        db.session.commit()
        assert ProviderService.query.filter_by(provider_id=provider.id, service_id=service.id, is_active=True).first()


def test_dev_smoke_seed_defines_four_canonical_provider_mappings():
    seed_path = Path(__file__).parents[1] / "database" / "seed_dev.py"
    if not seed_path.exists():
        pytest.skip("database/seed_dev.py is a local-only Development fixture")

    module = ast.parse(seed_path.read_text(encoding="utf-8"))
    assignment = next(
        node for node in module.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "SYNTHETIC_PROVIDERS" for target in node.targets)
    )
    synthetic_providers = ast.literal_eval(assignment.value)

    mappings = {profile: (email, slug) for profile, email, _name, slug, _lat, _lon in synthetic_providers}
    assert mappings == {
        "DEV-PLUMBER-01": ("dev.plumber01@tedile.test", "plumber"),
        "DEV-ELECTRICIAN-01": ("dev.electrician01@tedile.test", "electrician"),
        "DEV-WELDER-SMOKE-01": ("dev.welder01@tedile.test", "welder"),
        "DEV-AC-REPAIR-SMOKE-01": ("dev.acrepair01@tedile.test", "ac-repair"),
    }


def test_search_verified_only(app):
    with app.app_context():
        verified = _make_provider("Kolkata", 22.5726, 88.3639, verified=True)
        unverified = _make_provider("Siliguri", 26.7271, 88.3953, verified=False)

        results = search_providers(verified_only=True)
        codes = {r["id"] for r in results}
        assert verified.profile_code in codes
        assert unverified.profile_code not in codes
