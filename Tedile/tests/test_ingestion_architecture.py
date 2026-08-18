import json

import pytest
from sqlalchemy import text

from app.extensions import db
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.service import Service
from app.models.user import User
from database.import_providers import import_paths, import_records
from tests.conftest import create_isolated_test_app


@pytest.fixture
def app():
    flask_app = create_isolated_test_app()
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_token(client):
    client.get("/")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def create_user(email, role):
    account = User(email=email, name=role.title(), role=role, phone="+910000000000")
    account.set_password("password123")
    db.session.add(account)
    db.session.commit()
    db.session.refresh(account)
    db.session.expunge(account)
    return account


def set_user_session(client, account):
    token = csrf_token(client)
    with client.session_transaction() as sess:
        sess["user"] = account.to_session_dict()
    return token


def test_import_source_is_not_served_as_static(client):
    response = client.get("/data/imports/providers/2026-08-18/providers.json")
    assert response.status_code == 404


def test_importer_accepts_arbitrary_path_and_is_idempotent(app, tmp_path):
    input_path = tmp_path / "future" / "providers.json"
    input_path.parent.mkdir()
    input_path.write_text(json.dumps({
        "providers": [{
            "profile_code": "IMPORT-ONE",
            "first_name": "Imported",
            "last_name": "Provider",
            "service": "plumber",
            "extracted_service_value": "plumber",
            "phone": "+910000000001",
            "whatsapp": "+910000000001",
            "city": "Malda",
            "state": "West Bengal",
            "latitude": 25.0,
            "longitude": 88.1,
            "hourly_rate": 300,
            "experience": "3-5",
            "is_available": True,
            "sub_services": "pipe-repair",
            "profile_photo": "https://example.test/provider.jpg",
        }]
    }))

    with app.app_context():
        db.session.add(Service(name="Plumber", slug="plumber"))
        db.session.commit()
        first = import_records(input_path)
        second = import_records(input_path)

        assert first["providers_inserted"] == 1
        assert first["provider_services_inserted"] == 1
        assert second["providers_inserted"] == 0
        assert second["providers_updated"] == 1
        assert second["provider_services_inserted"] == 0
        assert second["duplicates_skipped"] == 1
        assert Provider.query.filter_by(profile_code="IMPORT-ONE").count() == 1
        assert ProviderService.query.count() == 1
        provider = Provider.query.filter_by(profile_code="IMPORT-ONE").one()
        assert provider.phone == "+910000000001"
        assert provider.whatsapp == "+910000000001"
        assert provider.profile_photo_url == "https://example.test/provider.jpg"
        raw_phone = db.session.execute(
            text("SELECT phone FROM providers WHERE id = :id"),
            {"id": provider.id},
        ).scalar()
        assert raw_phone != "+910000000001"


def write_import_file(path, profile_code, service_slug, sub_services=None):
    path.write_text(json.dumps({
        "providers": [{
            "profile_code": profile_code,
            "first_name": "Imported",
            "last_name": "Provider",
            "service": service_slug,
            "extracted_service_value": service_slug,
            "phone": "+910000000001",
            "whatsapp": "+910000000001",
            "city": "Malda",
            "state": "West Bengal",
            "latitude": 25.0,
            "longitude": 88.1,
            "hourly_rate": 300,
            "experience": "3-5",
            "is_available": True,
            "sub_services": sub_services or [],
        }]
    }))


def test_multiple_files_share_one_provider_and_create_multiple_services(app, tmp_path):
    plumber_path = tmp_path / "plumber.json"
    electrician_path = tmp_path / "electrician.json"
    write_import_file(plumber_path, "MULTI-PROVIDER", "plumber", ["pipe-repair"])
    write_import_file(electrician_path, "MULTI-PROVIDER", "electrician", ["wiring"])

    with app.app_context():
        db.session.add_all([
            Service(name="Plumber", slug="plumber"),
            Service(name="Electrician", slug="electrician"),
        ])
        db.session.commit()
        report = import_paths([plumber_path, electrician_path])

        assert report["providers_inserted"] == 1
        assert report["unique_providers_processed"] == 1
        assert report["provider_services_inserted"] == 2
        assert Provider.query.filter_by(profile_code="MULTI-PROVIDER").count() == 1
        assert ProviderService.query.count() == 2


def test_duplicate_provider_service_is_skipped_across_one_invocation(app, tmp_path):
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    write_import_file(first_path, "DUPLICATE-PAIR", "plumber", ["pipe-repair"])
    write_import_file(second_path, "DUPLICATE-PAIR", "plumber", ["leak-repair"])

    with app.app_context():
        db.session.add(Service(name="Plumber", slug="plumber"))
        db.session.commit()
        report = import_paths([first_path, second_path])

        assert report["providers_inserted"] == 1
        assert report["provider_services_inserted"] == 1
        assert report["duplicates_skipped"] == 1
        assert ProviderService.query.count() == 1
        relation = ProviderService.query.one()
        assert relation.get_sub_services() == ["leak-repair", "pipe-repair"]


def test_failed_record_savepoint_does_not_increment_committed_counters(
    app, tmp_path, monkeypatch
):
    path = tmp_path / "rollback.json"
    payload = {
        "providers": [
            {
                "profile_code": "GOOD-RECORD",
                "first_name": "Good",
                "service": "plumber",
                "extracted_service_value": "plumber",
                "phone": "+910000000001",
                "sub_services": ["pipe-repair"],
            },
            {
                "profile_code": "FAILED-RECORD",
                "first_name": "Failed",
                "service": "plumber",
                "extracted_service_value": "plumber",
                "phone": "+910000000002",
                "sub_services": ["force-savepoint-failure"],
            },
        ]
    }
    path.write_text(json.dumps(payload))

    original_set_sub_services = ProviderService.set_sub_services

    def fail_one_record(self, values):
        if "force-savepoint-failure" in values:
            from sqlalchemy.exc import SQLAlchemyError
            raise SQLAlchemyError("deliberate record failure")
        return original_set_sub_services(self, values)

    monkeypatch.setattr(ProviderService, "set_sub_services", fail_one_record)

    with app.app_context():
        db.session.add(Service(name="Plumber", slug="plumber"))
        db.session.commit()
        report = import_records(path)

        assert report["providers_inserted"] == 1
        assert report["providers_updated"] == 0
        assert report["provider_services_inserted"] == 1
        assert len(report["records_rejected"]) == 1
        assert report["records_rejected"][0]["record_index"] == 1
        assert Provider.query.filter_by(profile_code="GOOD-RECORD").count() == 1
        assert Provider.query.filter_by(profile_code="FAILED-RECORD").count() == 0
        assert ProviderService.query.count() == 1


def test_api_provider_lifecycle_persists_and_encrypts_phone(app, client):
    with app.app_context():
        provider_user = create_user("provider@example.com", "provider")
        customer_user = create_user("customer@example.com", "customer")

    token = set_user_session(client, provider_user)
    response = client.post(
        "/api/providers",
        json={
            "profile_code": "API-PROVIDER",
            "first_name": "API",
            "last_name": "Provider",
            "phone": "+910000000002",
            "whatsapp": "+910000000002",
            "city": "Malda",
            "state": "West Bengal",
        },
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201
    profile_code = response.get_json()["profile_code"]

    with app.app_context():
        provider = Provider.query.filter_by(profile_code=profile_code).one()
        raw_phone = db.session.execute(
            text("SELECT phone FROM providers WHERE id = :id"),
            {"id": provider.id},
        ).scalar()
        assert raw_phone != "+910000000002"
        assert provider.phone == "+910000000002"
        provider_id = provider.id

    response = client.patch(
        f"/api/providers/{profile_code}",
        json={"phone": "+910000000003", "whatsapp": "+910000000003"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200

    with app.app_context():
        provider = db.session.get(Provider, provider_id)
        assert provider.phone == "+910000000003"
        assert provider.whatsapp == "+910000000003"

    set_user_session(client, customer_user)
    response = client.patch(
        f"/api/providers/{profile_code}",
        json={"city": "Kolkata"},
        headers={"X-CSRFToken": csrf_token(client)},
    )
    assert response.status_code == 403


def test_public_provider_api_still_excludes_sensitive_fields(app, client):
    with app.app_context():
        provider_user = create_user("provider-public@example.com", "provider")
    token = set_user_session(client, provider_user)
    response = client.post(
        "/api/providers",
        json={
            "profile_code": "PUBLIC-PROVIDER",
            "first_name": "Public",
            "phone": "+910000000004",
            "latitude": 25.0,
            "longitude": 88.0,
        },
        headers={"X-CSRFToken": token},
    )
    profile_code = response.get_json()["profile_code"]
    with app.app_context():
        service = Service(name="Plumber", slug="plumber")
        provider = Provider.query.filter_by(profile_code=profile_code).one()
        db.session.add(service)
        db.session.commit()
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id))
        db.session.commit()

    response = client.get(f"/api/providers/{profile_code}")
    assert response.status_code == 200
    payload = response.get_json()
    for forbidden in ("phone", "whatsapp", "email", "latitude", "longitude", "user_id"):
        assert forbidden not in payload
