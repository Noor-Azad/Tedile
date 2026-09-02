import pytest
import app as app_module

from app.extensions import db, limiter
from app.models.user import User
from config import ProductionConfig
from tests.conftest import create_isolated_test_app


@pytest.fixture
def app():
    flask_app = create_isolated_test_app()
    flask_app.config.update(RATELIMIT_STORAGE_URI="memory://", RATELIMIT_ENABLED=True)
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


def make_user(email, role="customer"):
    user = User(email=email, name=role.title(), role=role)
    user.set_password("correct-password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


def begin_login(client, email="onboard@example.com", role="customer"):
    return client.post("/signup", data={"csrf_token": csrf_token(client), "email": email, "name": "Onboard User", "password": "correct-password", "phone": "9876543210", "role": role})


def test_homepage_is_auth_only(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Log in" in response.data and b"Register" in response.data
    assert b"Search providers" not in response.data
    assert b"popular-services" not in response.data


def test_otp_is_server_verified_expiring_and_not_in_session_or_response(app, client, monkeypatch):
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)

    assert begin_login(client).headers["Location"].endswith("/otp")
    with client.session_transaction() as sess:
        challenge = dict(sess["otp_challenge"])
        assert "otp" not in challenge
        assert sent["otp"] not in repr(dict(sess))
    invalid = client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": "000000"})
    assert invalid.status_code == 400
    assert sent["otp"].encode() not in invalid.data
    with client.session_transaction() as sess:
        challenge = dict(sess["otp_challenge"])
        challenge["expires_at"] = 0
        sess["otp_challenge"] = challenge
    expired = client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]})
    assert expired.status_code == 400


def test_valid_otp_enters_location_then_existing_role_flow(app, client, monkeypatch):
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    begin_login(client, "provider-onboard@example.com", "provider")
    response = client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/onboarding/location")
    assert client.get("/onboarding/location").status_code == 200


def test_location_grant_and_denial_continue_without_persisting_coordinates(app, client, monkeypatch):
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    begin_login(client, "location@example.com")
    client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]})
    granted = client.post("/onboarding/location", json={"latitude": 25.0, "longitude": 88.0}, headers={"X-CSRFToken": csrf_token(client)})
    assert granted.status_code == 200
    with client.session_transaction() as sess:
        assert sess["onboarding"]["location_status"] == "granted"
        assert "latitude" not in repr(dict(sess))
    assert client.post("/onboarding/complete", data={"csrf_token": csrf_token(client)}).status_code == 302
    with app.app_context():
        assert User.query.filter_by(email="location@example.com").one().onboarding_completed is True


def test_completed_user_login_skips_otp_and_onboarding(app, client):
    with app.app_context():
        account = make_user("completed@example.com")
        account.onboarding_completed = True
        db.session.commit()
    response = client.post("/login", data={"csrf_token": csrf_token(client), "email": "completed@example.com", "password": "correct-password"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/customer/dashboard")
    assert client.get("/otp").status_code == 302


def test_incomplete_existing_user_login_enters_location_without_otp(app, client):
    with app.app_context():
        make_user("legacy@example.com")
    response = client.post("/login", data={"csrf_token": csrf_token(client), "email": "legacy@example.com", "password": "correct-password"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/onboarding/location")
    with client.session_transaction() as sess:
        assert "otp_challenge" not in sess


def test_authenticated_activity_refreshes_and_enforces_idle_timeout(app, client, monkeypatch):
    with app.app_context():
        user = make_user("idle@example.com")
        user.onboarding_completed = True
        db.session.commit()
        user_session = user.to_session_dict()

    current_time = [1000.0]
    monkeypatch.setattr(app_module.time, "time", lambda: current_time[0])
    with client.session_transaction() as sess:
        sess["user"] = user_session
        sess["last_activity"] = 1000.0

    assert client.get("/customer/dashboard").status_code == 200
    current_time[0] = 1500.0
    assert client.get("/customer/dashboard").status_code == 200
    current_time[0] = 3301.0
    response = client.get("/customer/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user" not in sess


def test_unauthenticated_requests_are_not_idle_timed_out(app, client, monkeypatch):
    monkeypatch.setattr(app_module.time, "time", lambda: 10_000.0)
    response = client.get("/")
    assert response.status_code == 200


def test_location_denial_stays_on_location_step(client):
    response = client.get("/onboarding/location")
    assert response.status_code == 302


@pytest.mark.parametrize("payload", [
    {},
    {"latitude": 25.0},
    {"longitude": 88.0},
    {"latitude": 91.0, "longitude": 88.0},
    {"latitude": -91.0, "longitude": 88.0},
    {"latitude": 25.0, "longitude": 181.0},
    {"latitude": 25.0, "longitude": -181.0},
    {"latitude": "NaN", "longitude": 88.0},
    {"latitude": 25.0, "longitude": "Infinity"},
])
def test_location_rejects_invalid_coordinates(client, payload):
    with client.session_transaction() as sess:
        sess["user"] = {"id": 1, "name": "Customer", "role": "customer"}
        sess["onboarding"] = {"stage": "location"}
    client.get("/onboarding/location")
    response = client.post("/onboarding/location", json=payload, headers={"X-CSRFToken": csrf_token(client)})
    assert response.status_code == 400


def test_location_requires_authentication_and_csrf(client):
    assert client.post("/onboarding/location", json={"latitude": 25, "longitude": 88}).status_code == 302
    with client.session_transaction() as sess:
        sess["user"] = {"id": 1, "name": "Customer", "role": "customer"}
        sess["onboarding"] = {"stage": "location"}
    client.get("/onboarding/location")
    response = client.post("/onboarding/location", json={"latitude": 25, "longitude": 88})
    assert response.status_code == 400
    assert b"Missing or invalid CSRF token." in response.data


def test_location_frontend_handles_denial_and_retry(client):
    with client.session_transaction() as sess:
        sess["user"] = {"id": 1, "name": "Customer", "role": "customer"}
        sess["onboarding"] = {"stage": "location"}
    assert client.get("/onboarding/location").status_code == 200
    script = client.get("/static/onboarding.js").data
    assert b"Try Again" in script
    assert b"permission was denied" in script
    assert b"timed out" in script
    assert b"unavailable" in script


def test_otp_attempts_and_resends_are_rate_limited(app, client, monkeypatch):
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    begin_login(client, "otp-limits@example.com")
    for _ in range(5):
        assert client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": "999999"}).status_code == 400
    assert client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": "999999"}).status_code == 429
    for _ in range(3):
        assert client.post("/otp/resend", data={"csrf_token": csrf_token(client)}).status_code == 302
    assert client.post("/otp/resend", data={"csrf_token": csrf_token(client)}).status_code == 429


def test_console_otp_is_only_emitted_to_server_logs(app, client, caplog):
    app.config["APP_ENV"] = "development"
    app.config["OTP_DELIVERY_PROVIDER"] = "console"
    with caplog.at_level("INFO", logger="app"):
        response = begin_login(client, "console-otp@example.com")
    message = next(record.getMessage() for record in caplog.records if "UAT OTP generated" in record.getMessage())
    otp = message.rsplit(": ", 1)[1]
    assert response.status_code == 302
    assert otp.isdigit() and len(otp) == 6
    assert otp.encode() not in response.data
    with client.session_transaction() as sess:
        assert otp not in repr(dict(sess))
    assert otp not in client.get("/otp").get_data(as_text=True)


@pytest.mark.parametrize("provider, message", [("console", "not allowed"), ("unconfigured", "must be configured")])
def test_production_rejects_unsafe_or_missing_otp_provider(monkeypatch, provider, message):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ENCRYPTION_KEY", "test-encryption-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/tedile")
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", "postgresql://user:pass@localhost/tedile")
    monkeypatch.setattr(ProductionConfig, "OTP_DELIVERY_PROVIDER", provider)
    with pytest.raises(RuntimeError, match=message):
        ProductionConfig()
