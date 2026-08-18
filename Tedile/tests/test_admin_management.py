import pytest
from sqlalchemy import text
from werkzeug.security import check_password_hash

from app.extensions import db
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.service import Service
from app.models.user import User
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
    user = User(email=email, name=role.title(), role=role, phone="+910000000000")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    db.session.expunge(user)
    return user


def login_as(client, user):
    token = csrf_token(client)
    with client.session_transaction() as sess:
        sess["user"] = user.to_session_dict()
    return token


def create_service(slug="plumber", active=True):
    service = Service(name=slug.title(), slug=slug, is_active=active)
    db.session.add(service)
    db.session.commit()
    return service


def create_provider(profile_code="P-ONE", active=True):
    provider = Provider(
        profile_code=profile_code,
        first_name="Existing",
        last_name="Provider",
        phone="+910000000001",
        whatsapp="+910000000001",
        city="Malda",
        state="West Bengal",
        latitude=25.0,
        longitude=88.1,
        is_active=active,
    )
    db.session.add(provider)
    db.session.commit()
    return provider


def test_admin_only_access(client):
    admin = create_user("admin@example.com", "admin")
    customer = create_user("customer@example.com", "customer")
    provider_user = create_user("provider@example.com", "provider")

    login_as(client, admin)
    assert client.get("/admin/dashboard").status_code == 200

    login_as(client, customer)
    assert client.get("/admin/dashboard").status_code == 403

    login_as(client, provider_user)
    assert client.get("/admin/dashboard").status_code == 403


def test_admin_dashboard_verify_redirects_and_shows_verified_provider(app, client):
    admin = create_user("admin@example.com", "admin")
    provider = create_provider(profile_code="P-PENDING")
    token = login_as(client, admin)

    response = client.post(
        f"/admin/providers/{provider.id}/verify",
        data={"csrf_token": token, "verified": "true"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")

    with app.app_context():
        updated_provider = Provider.query.get(provider.id)
        assert updated_provider.verified is True

    dashboard = client.get(response.headers["Location"])
    assert dashboard.status_code == 200
    assert b"Existing Provider" in dashboard.data
    assert b"Verified" in dashboard.data


def test_admin_can_create_update_and_block_provider(app, client):
    admin = create_user("admin@example.com", "admin")
    token = login_as(client, admin)

    response = client.post(
        "/api/admin/providers",
        json={"first_name": "New", "last_name": "Provider", "phone": "+910000000002"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201
    payload = response.get_json()
    profile_code = payload["profile_code"]
    assert profile_code.startswith("TED-")
    assert "id" in payload

    response = client.patch(
        f"/api/admin/providers/{profile_code}",
        json={"phone": "+910000000003", "whatsapp": "+910000000003", "verified": True},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200

    response = client.post(
        f"/api/admin/providers/{profile_code}/block",
        json={"reason": "review required"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200

    with app.app_context():
        provider = Provider.query.filter_by(profile_code=profile_code).one()
        assert provider.is_active is False
        assert provider.verified is True
        assert provider.phone == "+910000000003"
        raw_phone = db.session.execute(
            text("SELECT phone FROM providers WHERE id = :id"), {"id": provider.id}
        ).scalar()
        assert raw_phone != "+910000000003"

def test_admin_can_block_relationship_and_global_service_filters_search(app, client):
    admin = create_user("admin@example.com", "admin")
    service = create_service()
    provider = create_provider()
    relation = ProviderService(provider_id=provider.id, service_id=service.id)
    db.session.add(relation)
    db.session.commit()
    token = login_as(client, admin)

    response = client.patch(
        f"/api/admin/providers/{provider.profile_code}/services/{service.slug}",
        json={"is_active": False, "blocked_reason": "paused"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    with app.app_context():
        assert ProviderService.query.count() == 1

    assert client.get("/api/search/providers").get_json()["count"] == 0

    response = client.patch(
        f"/api/admin/providers/{provider.profile_code}/services/{service.slug}",
        json={"is_active": True},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    response = client.patch(
        f"/api/admin/services/{service.slug}",
        json={"is_active": False},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    assert client.get("/api/search/providers").get_json()["count"] == 0

    response = client.patch(
        f"/api/admin/services/{service.slug}",
        json={"is_active": True},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    assert client.get("/api/search/providers").get_json()["count"] == 1


def test_customer_cannot_modify_services_or_providers(client):
    customer = create_user("customer@example.com", "customer")
    service = create_service()
    token = login_as(client, customer)

    assert client.post(
        "/api/admin/services",
        json={"name": "Blocked", "slug": "blocked"},
        headers={"X-CSRFToken": token},
    ).status_code == 403
    assert client.post(
        "/api/admin/providers",
        json={"first_name": "Blocked"},
        headers={"X-CSRFToken": token},
    ).status_code == 403


def test_provider_cannot_modify_another_provider(client):
    provider_user = create_user("provider@example.com", "provider")
    provider = create_provider()
    token = login_as(client, provider_user)

    response = client.patch(
        f"/api/providers/{provider.profile_code}",
        json={"city": "Kolkata"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 403


def test_admin_provisioning_logic_hashes_password_and_duplicate_is_safe(app):
    from database.create_admin import provision_admin

    with app.app_context():
        result = provision_admin("admin@example.com", "Admin", "secure-password", "secure-password")
        assert result["created"] is True
        user = User.query.filter_by(email="admin@example.com").one()
        assert user.role == "admin"
        assert user.password_hash != "secure-password"
        assert check_password_hash(user.password_hash, "secure-password")
        duplicate = provision_admin("admin@example.com", "Changed", "other", "other")
        assert duplicate["created"] is False
        assert duplicate["role"] == "admin"
        assert User.query.filter_by(email="admin@example.com").count() == 1
