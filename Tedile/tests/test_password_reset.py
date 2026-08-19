import pytest

from app.extensions import db, limiter
from app.models.user import User
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


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter.reset()
    yield
    limiter.reset()


def csrf_token(client):
    client.get("/")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def make_user():
    user = User(email="reset@example.com", name="Reset User", role="customer", phone="+919876543210")
    user.set_password("old-password")
    db.session.add(user)
    db.session.commit()
    return user


def request_reset(client, phone="9876543210"):
    return client.post("/forgot-password/request", data={"csrf_token": csrf_token(client), "phone": phone})


def test_forgot_password_link_and_page(client):
    assert b"Forgot Password?" in client.get("/").data
    page = client.get("/forgot-password")
    assert page.status_code == 200
    assert b'href="/login"' in page.data


@pytest.mark.parametrize("phone", [None, ""])
def test_registration_requires_mobile_number(client, phone):
    data = {"csrf_token": csrf_token(client), "email": "new@example.com", "name": "New User", "password": "password123"}
    if phone is not None:
        data["phone"] = phone
    response = client.post("/signup", data=data)
    assert response.status_code == 400


@pytest.mark.parametrize("phone", ["abc1234567", "123", "1" * 16, "5123456789", "+919876543210"])
def test_registration_rejects_invalid_mobile_number(client, phone):
    response = client.post("/signup", data={"csrf_token": csrf_token(client), "email": "new@example.com", "name": "New User", "password": "password123", "phone": phone})
    assert response.status_code == 400


def test_invalid_registration_does_not_create_user(app, client):
    response = client.post("/signup", data={"csrf_token": csrf_token(client), "email": "atomic@example.com", "name": "Atomic User", "password": "password123", "phone": "5123456789"})

    assert response.status_code == 400
    with app.app_context():
        assert User.query.filter_by(email="atomic@example.com").count() == 0


def test_invalid_registration_can_retry_same_email_with_valid_phone(app, client, monkeypatch):
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: True)
    invalid = client.post("/signup", data={"csrf_token": csrf_token(client), "email": "retry@example.com", "name": "Retry User", "password": "password123", "phone": "123"})
    valid = client.post("/signup", data={"csrf_token": csrf_token(client), "email": "retry@example.com", "name": "Retry User", "password": "password123", "phone": "9876543210"})

    assert invalid.status_code == 400
    assert valid.status_code == 302
    with app.app_context():
        assert User.query.filter_by(email="retry@example.com").count() == 1


def test_valid_formatted_indian_phone_registration_is_normalized(app, client, monkeypatch):
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    response = client.post("/signup", data={"csrf_token": csrf_token(client), "email": "new@example.com", "name": "New User", "password": "password123", "phone": "987-654-3210", "role": "customer"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/otp")
    assert sent["otp"].isdigit()
    with app.app_context():
        assert User.query.filter_by(email="new@example.com").one().phone == "+919876543210"


def test_known_and_unknown_phone_have_same_generic_reset_response(app, client, monkeypatch):
    with app.app_context():
        make_user()
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: True)
    known = request_reset(client)
    unknown = request_reset(client, "9876543211")
    assert known.status_code == unknown.status_code == 302
    assert b"If an account is associated" in client.get(unknown.headers["Location"]).data


def test_password_reset_otp_flow_is_secure_and_changes_password(app, client, monkeypatch):
    with app.app_context():
        make_user()
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    response = request_reset(client)
    assert response.headers["Location"].endswith("/forgot-password/otp")
    with client.session_transaction() as sess:
        assert "otp" not in repr(dict(sess))
        assert sent["otp"] not in repr(dict(sess))
    assert sent["otp"].encode() not in client.get("/forgot-password/otp").data
    invalid = client.post("/forgot-password/otp/verify", data={"csrf_token": csrf_token(client), "otp": "000000"})
    assert invalid.status_code == 400
    verified = client.post("/forgot-password/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]})
    assert verified.status_code == 302
    mismatch = client.post("/reset-password", data={"csrf_token": csrf_token(client), "password": "new-password", "password_confirmation": "different"})
    assert mismatch.status_code == 400
    changed = client.post("/reset-password", data={"csrf_token": csrf_token(client), "password": "new-password", "password_confirmation": "new-password"})
    assert changed.status_code == 302
    assert client.post("/login", data={"csrf_token": csrf_token(client), "email": "reset@example.com", "password": "old-password"}).status_code == 401
    assert client.post("/login", data={"csrf_token": csrf_token(client), "email": "reset@example.com", "password": "new-password"}).status_code == 302
    assert client.post("/forgot-password/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]}).status_code == 302


def test_password_reset_expiry_attempt_and_resend_limits(app, client, monkeypatch):
    with app.app_context():
        make_user()
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    request_reset(client)
    for _ in range(5):
        assert client.post("/forgot-password/otp/verify", data={"csrf_token": csrf_token(client), "otp": "999999"}).status_code == 400
    assert client.post("/forgot-password/otp/verify", data={"csrf_token": csrf_token(client), "otp": "999999"}).status_code == 429
    limiter.reset()
    for _ in range(3):
        assert client.post("/forgot-password/otp/resend", data={"csrf_token": csrf_token(client)}).status_code == 302
    assert client.post("/forgot-password/otp/resend", data={"csrf_token": csrf_token(client)}).status_code == 429


def test_password_reset_otp_expires(app, client, monkeypatch):
    with app.app_context():
        make_user()
    sent = {}
    monkeypatch.setattr("app.routes.auth.deliver_otp", lambda destination, otp: sent.update(otp=otp) or True)
    request_reset(client)
    with client.session_transaction() as sess:
        challenge = dict(sess["password_reset_challenge"])
        challenge["expires_at"] = 0
        sess["password_reset_challenge"] = challenge
    response = client.post("/forgot-password/otp/verify", data={"csrf_token": csrf_token(client), "otp": sent["otp"]})
    assert response.status_code == 400


def test_password_reset_csrf_is_required(client):
    assert client.post("/forgot-password/request", data={"phone": "9876543210"}).status_code == 400
