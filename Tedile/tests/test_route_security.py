import pytest

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


def csrf_token(client):
    client.get("/")
    with client.session_transaction() as sess:
        return sess["csrf_token"]


def user(email, role):
    account = User(email=email, name=role.title(), role=role, phone="+910000000000")
    account.set_password("password123")
    db.session.add(account)
    db.session.commit()
    db.session.refresh(account)
    db.session.expunge(account)
    return account


def provider(profile_code, user_id=None):
    record = Provider(
        profile_code=profile_code,
        user_id=user_id,
        first_name="Test",
        last_name="Provider",
        phone="+910000000001",
        whatsapp="+910000000001",
        city="Malda",
        state="West Bengal",
        latitude=25.0057449,
        longitude=88.1398483,
        hourly_rate=300,
        verified=True,
        rating=4.5,
    )
    db.session.add(record)
    db.session.commit()
    db.session.refresh(record)
    db.session.expunge(record)
    return record


def service_for(record):
    service = Service(name="Plumber", slug="plumber")
    db.session.add(service)
    db.session.commit()
    db.session.add(ProviderService(provider_id=record.id, service_id=service.id))
    db.session.commit()
    db.session.refresh(service)
    db.session.expunge(service)
    return service


def set_session(client, account):
    token = csrf_token(client)
    with client.session_transaction() as sess:
        sess["user"] = account.to_session_dict()
    return token


def test_public_profile_contains_only_public_fields(app, client):
    with app.app_context():
        record = provider("PROFILE-1")
        service = Service(name="Plumber", slug="plumber")
        db.session.add(service)
        db.session.commit()
        db.session.add(ProviderService(provider_id=record.id, service_id=service.id))
        db.session.commit()
        profile_code = record.profile_code

    response = client.get(f"/api/providers/{profile_code}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["id"] == profile_code
    for forbidden in ("phone", "whatsapp", "email", "latitude", "longitude", "user_id"):
        assert forbidden not in payload


def test_services_api_excludes_database_ids(app, client):
    with app.app_context():
        db.session.add(Service(name="Plumber", slug="plumber"))
        db.session.commit()

    response = client.get("/api/services")
    assert response.status_code == 200
    assert response.get_json()["data"] == [{
        "name": "Plumber",
        "slug": "plumber",
        "display_order": 0,
        "display_group": None,
        "icon_key": None,
    }]


def test_booking_response_excludes_internal_ids(app, client):
    with app.app_context():
        customer = user("customer@example.com", "customer")
        record = provider("BOOKING-PROVIDER")
        service = service_for(record)

    token = set_session(client, customer)
    response = client.post(
        "/customer/bookings",
        data={
            "csrf_token": token,
            "provider_profile_code": record.profile_code,
            "service_slug": service.slug,
            "notes": "Please call before arrival",
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert set(payload) == {"reference", "provider", "service", "status", "scheduled_at", "notes"}
    assert payload["provider"]["id"] == record.profile_code
    for forbidden in ("customer_id", "provider_id", "service_id", "id"):
        assert forbidden not in payload


def _booking_setup(app):
    with app.app_context():
        customer = user("booking-active-customer@example.com", "customer")
        record = provider("BOOKING-ACTIVE")
        service = service_for(record)
        relation = ProviderService.query.filter_by(
            provider_id=record.id, service_id=service.id
        ).one()
        ids = (customer, record, service, relation)
    return ids


def _create_booking(client, customer, profile_code, service_slug, token):
    set_session(client, customer)
    return client.post(
        "/customer/bookings",
        data={
            "csrf_token": token,
            "provider_profile_code": profile_code,
            "service_slug": service_slug,
        },
    )


def test_booking_requires_all_related_records_to_be_active(app, client):
    customer, record, service, relation = _booking_setup(app)
    token = set_session(client, customer)
    profile_code = record.profile_code
    service_slug = service.slug
    provider_id = record.id
    service_id = service.id
    relation_id = relation.id

    response = _create_booking(client, customer, profile_code, service_slug, token)
    assert response.status_code == 201

    with app.app_context():
        record = db.session.get(Provider, provider_id)
        record.is_active = False
        db.session.commit()
    assert _create_booking(client, customer, profile_code, service_slug, token).status_code == 404

    with app.app_context():
        record = db.session.get(Provider, provider_id)
        record.is_active = True
        service = db.session.get(Service, service_id)
        service.is_active = False
        db.session.commit()
    assert _create_booking(client, customer, profile_code, service_slug, token).status_code == 404

    with app.app_context():
        service = db.session.get(Service, service_id)
        service.is_active = True
        relation = db.session.get(ProviderService, relation_id)
        relation.is_active = False
        db.session.commit()
    assert _create_booking(client, customer, profile_code, service_slug, token).status_code == 400


def test_role_boundaries_reject_wrong_dashboard(app, client):
    with app.app_context():
        customer = user("customer@example.com", "customer")
        provider_user = user("provider@example.com", "provider")

    set_session(client, customer)
    assert client.get("/provider/dashboard").status_code == 403
    assert client.get("/admin/dashboard").status_code == 403

    set_session(client, provider_user)
    assert client.get("/customer/dashboard").status_code == 403
    assert client.get("/admin/dashboard").status_code == 403


def test_customer_cannot_view_another_customers_bookings_or_contact(app, client):
    with app.app_context():
        customer_a = user("customer-a@example.com", "customer")
        customer_b = user("customer-b@example.com", "customer")
        record = provider("CUSTOMER-ISOLATION")
        service = service_for(record)
        booking_a = Booking(customer_id=customer_a.id, provider_id=record.id, service_id=service.id)
        booking_b = Booking(
            customer_id=customer_b.id,
            provider_id=record.id,
            service_id=service.id,
            status="confirmed",
        )
        db.session.add_all([booking_a, booking_b])
        db.session.commit()
        reference_a = booking_a.public_reference
        reference_b = booking_b.public_reference
        profile_code = record.profile_code
        booking_b_id = booking_b.id
        customer_a_session = customer_a.to_session_dict()

    token = csrf_token(client)
    with client.session_transaction() as sess:
        sess["user"] = customer_a_session
    dashboard = client.get("/customer/dashboard")
    assert dashboard.status_code == 200
    assert reference_a.encode() in dashboard.data
    assert reference_b.encode() not in dashboard.data

    contact = client.get(f"/customer/providers/{profile_code}/contact")
    assert contact.status_code == 403

    assert client.post(f"/customer/bookings/{reference_b}/cancel").status_code == 404
    with app.app_context():
        assert db.session.get(Booking, booking_b_id).status == "confirmed"


def test_provider_cannot_access_or_modify_another_providers_resources(app, client):
    with app.app_context():
        provider_user_a = user("provider-a-isolation@example.com", "provider")
        provider_user_b = user("provider-b-isolation@example.com", "provider")
        provider("PROVIDER-ISOLATION-A", user_id=provider_user_a.id)
        provider_b = provider("PROVIDER-ISOLATION-B", user_id=provider_user_b.id)
        service = service_for(provider_b)
        customer = user("provider-isolation-customer@example.com", "customer")
        booking = Booking(customer_id=customer.id, provider_id=provider_b.id, service_id=service.id)
        db.session.add(booking)
        db.session.commit()
        provider_b_id = provider_b.id
        booking_id = booking.id
        booking_reference = booking.public_reference
        service_slug = service.slug
        provider_b_profile_code = provider_b.profile_code
        provider_a_session = provider_user_a.to_session_dict()

    token = csrf_token(client)
    with client.session_transaction() as sess:
        sess["user"] = provider_a_session
    assert client.get("/provider/dashboard").status_code == 200
    assert booking_reference.encode() not in client.get("/provider/dashboard").data

    response = client.patch(
        f"/api/providers/{provider_b_profile_code}",
        json={"city": "Unauthorized"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 403

    response = client.post(
        f"/api/providers/{provider_b_profile_code}/services",
        json={"service_slug": service_slug},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/api/providers/{provider_b_profile_code}/services/{service_slug}",
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 403

    response = client.post(
        f"/provider/bookings/{booking_reference}/status",
        data={"csrf_token": token, "status": "confirmed"},
    )
    assert response.status_code == 302

    response = client.post(
        "/provider/availability",
        data={"csrf_token": token, "availability": "busy"},
    )
    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Provider, provider_b_id).availability == "available"
        assert db.session.get(Booking, booking_id).status == "pending"


def test_unauthenticated_users_cannot_access_admin_api(client):
    assert client.get("/admin/dashboard").status_code == 302
    assert client.post("/api/admin/services").status_code == 302


def test_csrf_required_for_signup_and_login(client):
    assert client.post("/signup", data={"email": "x@example.com", "name": "X", "password": "password123"}).status_code == 400
    assert client.post("/login", data={"email": "x@example.com", "password": "password123"}).status_code == 400


def test_http_redirect_preserves_path_and_query(app, client):
    app.config["DEBUG"] = False

    response = client.get("/providers?service=electrician", base_url="http://localhost")

    assert response.status_code == 301
    assert response.headers["Location"] == "https://localhost/providers?service=electrician"


def test_https_request_is_not_redirected(app, client):
    app.config["DEBUG"] = False

    response = client.get("/health", base_url="https://localhost")

    assert response.status_code in (200, 503)
    assert response.status_code != 301


def test_untrusted_host_cannot_control_https_redirect(app, client):
    app.config["DEBUG"] = False

    response = client.get("/providers?next=1", base_url="http://attacker.example")

    assert response.status_code == 400
    assert "attacker.example" not in response.headers.get("Location", "")


def test_health_hides_database_exception_details(app, client, monkeypatch):
    class FailingSession:
        def execute(self, statement):
            raise RuntimeError("internal database host, SQL, and password")

        def rollback(self):
            pass

    monkeypatch.setattr(db, "session", FailingSession())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.get_json() == {
        "status": "degraded",
        "app": "Tedile",
        "error": "Database unavailable",
    }


def test_csrf_required_for_logout(client):
    with client.session_transaction() as sess:
        sess["user"] = {"id": 1, "name": "Customer", "role": "customer"}
    assert client.post("/logout").status_code == 400


def test_csrf_required_for_customer_booking(app, client):
    with app.app_context():
        customer = user("customer@example.com", "customer")
        record = provider("CSRF-CUSTOMER")
        service = service_for(record)
    set_session(client, customer)

    response = client.post(
        "/customer/bookings",
        data={"provider_profile_code": record.profile_code, "service_slug": service.slug},
    )
    assert response.status_code == 400


def test_csrf_required_for_provider_mutations(app, client):
    with app.app_context():
        account = user("provider@example.com", "provider")
        record = provider("CSRF-PROVIDER", user_id=account.id)
        service = service_for(record)
        booking = Booking(customer_id=user("customer@example.com", "customer").id, provider_id=record.id, service_id=service.id)
        db.session.add(booking)
        db.session.commit()
        booking_reference = booking.public_reference
    set_session(client, account)

    assert client.post("/provider/availability", data={"availability": "busy"}).status_code == 400
    assert client.post(f"/provider/bookings/{booking_reference}/status", data={"status": "confirmed"}).status_code == 400


def test_csrf_required_for_admin_verification(app, client):
    with app.app_context():
        account = user("admin@example.com", "admin")
        record = provider("CSRF-ADMIN")
    set_session(client, account)

    response = client.post(f"/admin/providers/{record.id}/verify", data={"verified": "true"})
    assert response.status_code == 400


def test_provider_cannot_update_another_providers_booking(app, client):
    with app.app_context():
        provider_account = user("provider-a@example.com", "provider")
        provider_a = provider("PROVIDER-A", user_id=provider_account.id)
        provider_b = provider("PROVIDER-B")
        service = service_for(provider_b)
        customer = user("booking-customer@example.com", "customer")
        booking = Booking(customer_id=customer.id, provider_id=provider_b.id, service_id=service.id)
        db.session.add(booking)
        db.session.commit()
        booking_reference = booking.public_reference
    token = set_session(client, provider_account)

    response = client.post(
        f"/provider/bookings/{booking_reference}/status",
        data={"csrf_token": token, "status": "confirmed"},
    )
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Booking, booking.id).status == "pending"
