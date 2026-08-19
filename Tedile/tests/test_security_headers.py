import pytest

from app.extensions import db
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.service import Service
from app.models.user import User
from tests.conftest import create_isolated_test_app


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


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
    return account


def login_as(client, account):
    token = csrf_token(client)
    with client.session_transaction() as sess:
        sess["user"] = account.to_session_dict()
    return token


def test_html_response_has_low_risk_security_headers(client):
    response = client.get("/")
    assert {name: response.headers[name] for name in SECURITY_HEADERS} == SECURITY_HEADERS


def test_api_response_has_low_risk_security_headers(client):
    response = client.get("/api/session")
    assert response.status_code == 401
    assert {name: response.headers[name] for name in SECURITY_HEADERS} == SECURITY_HEADERS
    assert "Content-Security-Policy" not in response.headers
    assert "Strict-Transport-Security" not in response.headers
    assert "Cross-Origin-Resource-Policy" not in response.headers


def test_public_provider_profile_is_cacheable_for_anonymous_and_authenticated_users(app, client):
    with app.app_context():
        account = create_user("provider@example.com", "provider")
        provider = Provider(
            profile_code="HEADER-PROVIDER",
            user_id=account.id,
            first_name="Header",
            last_name="Provider",
        )
        service = Service(name="Plumber", slug="plumber")
        db.session.add_all([provider, service])
        db.session.commit()
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id))
        db.session.commit()
        account_session = account.to_session_dict()

    response = client.get("/api/providers/HEADER-PROVIDER")
    assert response.status_code == 200
    assert "Cache-Control" not in response.headers

    token = csrf_token(client)
    with client.session_transaction() as sess:
        sess["user"] = account_session
    response = client.get("/api/providers/HEADER-PROVIDER")
    assert response.status_code == 200
    assert "Cache-Control" not in response.headers


def test_authenticated_management_and_session_responses_are_not_cached(client):
    account = create_user("provider-management@example.com", "provider")
    token = login_as(client, account)

    response = client.post(
        "/api/providers",
        json={"first_name": "Managed", "last_name": "Provider"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/api/session").headers["Cache-Control"] == "no-store"


def test_sensitive_path_matching_avoids_prefix_collisions(client):
    account = create_user("prefix@example.com", "customer")
    login_as(client, account)

    for path in ("/api/providersfoo", "/loginfoo", "/signupfoo"):
        response = client.get(path)
        assert response.status_code == 404
        assert "Cache-Control" not in response.headers


@pytest.mark.parametrize(
    ("role", "path"),
    [
        ("customer", "/customer/dashboard"),
        ("provider", "/provider/dashboard"),
        ("admin", "/admin/dashboard"),
    ],
)
def test_authenticated_dashboards_are_not_cached(client, role, path):
    account = create_user(f"{role}@example.com", role)
    login_as(client, account)

    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"


def test_public_static_resource_retains_existing_cache_behavior(client):
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-cache"
    assert "Content-Security-Policy" not in response.headers


def test_health_behavior_and_security_headers_are_preserved(client):
    response = client.get("/health")
    assert response.status_code in (200, 503)
    assert response.get_json()["app"] == "Tedile"
    assert {name: response.headers[name] for name in SECURITY_HEADERS} == SECURITY_HEADERS
    assert "Cache-Control" not in response.headers
