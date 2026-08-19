import pytest

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


def begin_login(client, email="onboard@example.com"):
    return client.post("/login", data={"csrf_token": csrf_token(client), "email": email, "password": "correct-password"})


def test_homepage_is_auth_only(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Log in" in response.data and b"Register" in response.data
    assert b"Search providers" not in response.data
    assert b"popular-services" not in response.data


def test_otp_is_server_verified_expiring_and_not_in_session_or_response(app, client, monkeypatch):
    with app.app_context():
        make_user("onboard@example.com")
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
    with app.app_context():
        make_user("provider-onboard@example.com", "provider")
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    begin_login(client, "provider-onboard@example.com")
    response = client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/onboarding/location")
    assert client.get("/onboarding/location").status_code == 200


def test_location_grant_and_denial_continue_without_persisting_coordinates(app, client, monkeypatch):
    with app.app_context():
        make_user("location@example.com")
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


def test_location_denial_is_allowed(app, client, monkeypatch):
    with app.app_context():
        make_user("denied-location@example.com")
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    begin_login(client, "denied-location@example.com")
    client.post("/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]})
    skipped = client.post("/onboarding/location/skip", headers={"X-CSRFToken": csrf_token(client)})
    assert skipped.status_code == 200
    assert skipped.get_json()["next"].endswith("/onboarding/permissions")


def test_otp_attempts_and_resends_are_rate_limited(app, client, monkeypatch):
    with app.app_context():
        make_user("otp-limits@example.com")
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
    app.config["OTP_DELIVERY_PROVIDER"] = "console"
    with app.app_context():
        make_user("console-otp@example.com")
    with caplog.at_level("INFO", logger="app.services.otp_service"):
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
