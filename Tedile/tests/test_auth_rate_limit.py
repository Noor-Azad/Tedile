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
        limiter.reset()
        yield flask_app
        limiter.reset()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def csrf_token(client):
    client.get("/")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def create_user(email, role="customer"):
    account = User(email=email, name=role.title(), role=role, phone="+910000000000")
    account.set_password("correct-password")
    db.session.add(account)
    db.session.commit()
    return account


def login(client, email, password):
    return client.post(
        "/login",
        data={"csrf_token": csrf_token(client), "email": email, "password": password},
    )


def test_failed_login_attempts_are_throttled_without_email_disclosure(app, client):
    with app.app_context():
        create_user("known@example.com")

    unknown = login(client, "unknown@example.com", "wrong-password")
    incorrect = login(client, "known@example.com", "wrong-password")
    assert unknown.status_code == 401
    assert incorrect.status_code == 401
    assert b"Invalid email or password." in unknown.data
    assert b"Invalid email or password." in incorrect.data
    assert b"known@example.com" not in unknown.data
    assert b"unknown@example.com" not in incorrect.data

    for _ in range(4):
        response = login(client, "known@example.com", "wrong-password")
        assert response.status_code == 401

    throttled = login(client, "known@example.com", "wrong-password")
    assert throttled.status_code == 429
    assert b"wrong-password" not in throttled.data


def test_successful_login_and_role_redirects_are_preserved(app, client):
    with app.app_context():
        create_user("customer@example.com", "customer")
        create_user("provider@example.com", "provider")
        create_user("admin@example.com", "admin")

    response = login(client, "customer@example.com", "correct-password")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/customer/dashboard")
    assert client.get("/api/session").get_json()["user"]["role"] == "customer"

    client.post("/logout", data={"csrf_token": csrf_token(client)})
    response = login(client, "provider@example.com", "correct-password")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/provider/dashboard")
    assert client.get("/api/session").get_json()["user"]["role"] == "provider"

    client.post("/logout", data={"csrf_token": csrf_token(client)})
    response = login(client, "admin@example.com", "correct-password")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")
    assert client.get("/api/session").get_json()["user"]["role"] == "admin"


def test_csrf_is_checked_before_login_authentication(client):
    response = client.post(
        "/login", data={"email": "unknown@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 400
    assert b"Invalid email or password." not in response.data


def test_invalid_csrf_does_not_consume_login_rate_limit_quota(client):
    invalid_csrf = client.post(
        "/login", data={"email": "quota@example.com", "password": "wrong-password"}
    )
    assert invalid_csrf.status_code == 400
    assert b"Missing or invalid CSRF token." in invalid_csrf.data

    for _ in range(5):
        assert login(client, "quota@example.com", "wrong-password").status_code == 401
    assert login(client, "quota@example.com", "wrong-password").status_code == 429


def test_different_email_keys_do_not_share_email_limit(client):
    for email in ("first@example.com", "second@example.com"):
        for _ in range(5):
            response = login(client, email, "wrong-password")
            assert response.status_code == 401


def test_limiter_reset_clears_failed_login_state(client):
    for _ in range(5):
        assert login(client, "reset@example.com", "wrong-password").status_code == 401
    assert login(client, "reset@example.com", "wrong-password").status_code == 429

    limiter.reset()
    assert login(client, "reset@example.com", "wrong-password").status_code == 401
