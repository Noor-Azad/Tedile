import pytest
from sqlalchemy import text

from app.crypto import EncryptedString
from app.extensions import db
from app.models.booking import Booking
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


def _create_customer(email="customer@example.com"):
    user = User(email=email, name="Test Customer", role="customer", phone="+911111111111")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def _create_provider():
    provider = Provider(
        profile_code="P-TEST",
        first_name="Ravi",
        last_name="Sharma",
        phone="+912222222222",
        whatsapp="+912222222222",
        city="Kolkata",
        state="West Bengal",
        latitude=22.5726,
        longitude=88.3639,
        hourly_rate=300,
        verified=True,
        rating=4.5,
    )
    db.session.add(provider)
    db.session.commit()
    return provider


def _csrf_token(client):
    client.get("/")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def test_phone_encrypted_at_rest(app):
    with app.app_context():
        provider = _create_provider()
        raw_value = db.session.execute(
            text("SELECT phone FROM providers WHERE id = :id"), {"id": provider.id}
        ).scalar()

        assert raw_value != "+912222222222"
        assert provider.phone == "+912222222222"  # ORM access transparently decrypts


def test_public_search_api_excludes_sensitive_fields(app, client):
    with app.app_context():
        service = Service(name="Plumber", slug="plumber")
        db.session.add(service)
        provider = _create_provider()
        db.session.add(ProviderService(provider_id=provider.id, service_id=service.id))
        db.session.commit()

    response = client.get("/api/search/providers")
    payload = response.get_json()
    assert response.status_code == 200

    providers = payload["data"]["providers"]
    assert len(providers) == 1
    record = providers[0]
    for forbidden_field in ("phone", "whatsapp", "latitude", "longitude", "profile_code"):
        assert forbidden_field not in record
    assert record["id"] == "P-TEST"  # public identifier is profile_code, not the DB primary key


def test_session_cookie_excludes_pii(app, client):
    with app.app_context():
        _create_customer()

    client.post("/login", data={"email": "customer@example.com", "password": "password123", "csrf_token": _csrf_token(client)})

    with client.session_transaction() as sess:
        assert set(sess["user"]) == {"id", "name", "role"}
        assert "password123" not in repr(dict(sess))


def test_contact_details_require_authorized_booking(app, client):
    with app.app_context():
        customer = _create_customer()
        provider = _create_provider()
        provider_id = provider.id
        customer_id = customer.id

    client.post("/login", data={"email": "customer@example.com", "password": "password123", "csrf_token": _csrf_token(client)})
    with client.session_transaction() as sess:
        sess["user"] = {"id": customer_id, "name": "Customer", "role": "customer"}
        sess.pop("otp_challenge", None)

    # No booking yet -> forbidden.
    response = client.get("/customer/providers/P-TEST/contact")
    assert response.status_code == 403

    with app.app_context():
        booking = Booking(customer_id=customer_id, provider_id=provider_id, service_id=1, status="confirmed")
        db.session.add(booking)
        db.session.commit()

    # Confirmed booking exists -> contact details are released.
    response = client.get("/customer/providers/P-TEST/contact")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["phone"] == "+912222222222"


def test_contact_details_require_login(client):
    response = client.get("/customer/providers/P-TEST/contact")
    assert response.status_code in (302, 401, 403)


def test_encrypted_string_refuses_to_store_plaintext_without_cryptography(monkeypatch):
    """There must be no code path where an EncryptedString column stores
    plaintext, even if the cryptography package is missing."""
    monkeypatch.setattr("app.crypto.Fernet", None)

    with pytest.raises(RuntimeError, match="cryptography"):
        EncryptedString()
