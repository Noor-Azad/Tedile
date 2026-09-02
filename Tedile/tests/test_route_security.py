import pytest
import json

from app.extensions import db
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.service import Service
from app.models.user import User
from app.models.review import Review
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


def test_profile_is_authenticated_and_self_scoped(app, client):
    account = user("profile@example.com", "customer")
    set_session(client, account)

    response = client.get("/profile")

    assert response.status_code == 200
    assert b"profile@example.com" in response.data
    assert b"Customer" in response.data
    assert b"password_hash" not in response.data
    assert b"password123" not in response.data
    assert b"otp_challenge" not in response.data
    assert client.get("/profile/1").status_code == 404


def test_profile_requires_authentication(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_customer_dashboard_contains_location_provider_search_form(app, client):
    account = user("customer-search-ui@example.com", "customer")
    set_session(client, account)
    page = client.get("/customer/dashboard")
    assert page.status_code == 200
    assert b'id="hero-search-form"' in page.data
    assert b'id="hero-location"' in page.data
    assert b'id="hero-keyword"' in page.data
    assert b'id="hero-status"' in page.data
    assert b'id="use-current-location"' in page.data
    script = client.get("/static/customer.js").data
    assert b"navigator.geolocation.getCurrentPosition" in script
    assert b"Location access was denied." in script
    assert b"sessionStorage.setItem(SEARCH_LOCATION_STORAGE_KEY" in script
    assert b"sessionStorage.setItem(BOOKING_LOCATION_STORAGE_KEY" in script
    assert b"restoreLocations();" in script


def test_provider_profile_loads_current_location_aware_customer_script(app, client):
    page = client.get("/providers/PROFILE-LOCATION")
    assert page.status_code in (200, 404)
    if page.status_code == 200:
        assert b"customer.js?v=20260829-6" in page.data


def test_provider_profile_has_customer_navigation_and_neutral_avatar_fallback(app, client):
    anonymous = client.get("/providers/PROFILE-LOCATION")
    assert b'href="/customer/dashboard#results"' in anonymous.data
    assert b'href="/customer/dashboard"' not in anonymous.data
    assert b'action="/logout"' not in anonymous.data
    script = client.get("/static/customer.js").data
    assert b"providerInitials" in script
    assert b"role=\"img\" aria-label=\"Provider avatar\"" in script
    assert b">?</div>" not in script

    account = user("profile-customer@example.com", "customer")
    set_session(client, account)
    authenticated = client.get("/providers/PROFILE-LOCATION")
    assert b'href="/customer/dashboard#results"' in authenticated.data
    assert b'href="/customer/dashboard"' in authenticated.data
    assert b'method="POST" action="/logout"' in authenticated.data
    assert b'name="csrf_token"' in authenticated.data


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


@pytest.mark.parametrize(
    "query",
    [
        {"latitude": "not-a-number"},
        {"longitude": "not-a-number"},
        {"radius": "not-a-number"},
        {"radius": "-1"},
        {"radius": "NaN"},
        {"radius": "Infinity"},
        {"latitude": "NaN", "longitude": "0"},
        {"latitude": "Infinity", "longitude": "0"},
        {"latitude": "0", "longitude": "-Infinity"},
        {"limit": "not-an-integer"},
        {"offset": "-1"},
    ],
)
def test_provider_search_rejects_invalid_numeric_input(client, query):
    response = client.get("/api/search/providers", query_string=query)
    assert response.status_code == 400
    assert response.status_code != 500
    assert b"Traceback" not in response.data
    assert b"ValueError" not in response.data


def test_provider_search_accepts_existing_valid_request(client):
    response = client.get(
        "/api/search/providers",
        query_string={"latitude": "0", "longitude": "0", "radius": "50", "limit": "20", "offset": "0"},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] is True


def test_provider_search_preserves_radius_compatibility(app, client, monkeypatch):
    captured = []

    def fake_search_providers(**kwargs):
        captured.append(kwargs["radius_km"])
        return [], 0

    monkeypatch.setattr("app.routes.api.search_providers", fake_search_providers)

    assert client.get("/api/search/providers").status_code == 200
    assert captured[-1] == app.config["DEFAULT_SEARCH_RADIUS_KM"]

    assert client.get("/api/search/providers?radius=0").status_code == 200
    assert captured[-1] == app.config["DEFAULT_SEARCH_RADIUS_KM"]

    assert client.get("/api/search/providers?radius=25").status_code == 200
    assert captured[-1] == 25

    assert client.get("/api/search/providers?radius=501").status_code == 200
    assert captured[-1] == 501


def test_booking_rejects_malformed_datetime_and_oversized_notes(app, client):
    with app.app_context():
        customer = user("validation-customer@example.com", "customer")
        record = provider("VALIDATION-PROVIDER")
        service = service_for(record)
        profile_code = record.profile_code
        service_slug = service.slug

    token = set_session(client, customer)
    invalid_datetime = client.post(
        "/customer/bookings",
        data={
            "csrf_token": token,
            "provider_profile_code": profile_code,
            "service_slug": service_slug,
            "scheduled_at": "not-a-datetime",
        },
    )
    assert invalid_datetime.status_code == 400
    assert b"Invalid scheduled_at" in invalid_datetime.data
    assert b"Traceback" not in invalid_datetime.data
    assert b"ValueError" not in invalid_datetime.data

    oversized_notes = client.post(
        "/customer/bookings",
        data={
            "csrf_token": token,
            "provider_profile_code": profile_code,
            "service_slug": service_slug,
            "notes": "x" * 5001,
        },
    )
    assert oversized_notes.status_code == 400
    assert b"Notes are too long" in oversized_notes.data

    valid = client.post(
        "/customer/bookings",
        data={
            "csrf_token": token,
            "provider_profile_code": profile_code,
            "service_slug": service_slug,
            "scheduled_at": "2026-08-20T10:30:00",
            "notes": "Please call first",
        },
    )
    assert valid.status_code == 201


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


@pytest.mark.parametrize(
    ("availability", "message"),
    [
        ("busy", "This provider is currently busy and cannot accept new bookings."),
        ("offline", "This provider is currently offline and cannot accept new bookings."),
    ],
)
def test_booking_rejects_unavailable_provider_without_creating_booking(app, client, availability, message):
    customer, record, service, _ = _booking_setup(app)
    with app.app_context():
        db.session.get(Provider, record.id).availability = availability
        db.session.commit()
        before = Booking.query.count()
    token = set_session(client, customer)
    response = _create_booking(client, customer, record.profile_code, service.slug, token)
    assert response.status_code == 409
    assert response.get_json()["error"] == message
    with app.app_context():
        assert Booking.query.count() == before


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


def test_customer_dashboard_contains_service_catalogue_and_reuses_services_api(app, client):
    with app.app_context():
        account = user("catalogue@example.com", "customer")
        db.session.add(Service(name="Electrician", slug="electrician", display_order=1))
        db.session.commit()
    set_session(client, account)

    dashboard = client.get("/customer/dashboard")
    assert dashboard.status_code == 200
    assert b'id="services"' in dashboard.data
    assert b'id="popular-services"' in dashboard.data
    assert b'id="service-groups"' in dashboard.data
    assert b'href="#services"' in dashboard.data

    services = client.get("/api/services")
    assert services.status_code == 200
    assert services.get_json()["data"][0]["slug"] == "electrician"


def test_customer_dashboard_remains_protected(client):
    assert client.get("/customer/dashboard").status_code == 302


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


@pytest.mark.parametrize(
    ("initial", "target", "expected_status"),
    [
        ("pending", "confirmed", 302),
        ("pending", "cancelled", 302),
        ("confirmed", "completed", 302),
        ("confirmed", "cancelled", 400),
        ("confirmed", "pending", 400),
        ("cancelled", "confirmed", 400),
        ("cancelled", "completed", 400),
        ("completed", "confirmed", 400),
        ("completed", "cancelled", 400),
    ],
)
def test_provider_booking_status_transitions_are_enforced(app, client, initial, target, expected_status):
    account = user(f"transition-{initial}-{target}@example.com", "provider")
    record = provider(f"TRANSITION-{initial}-{target}", user_id=account.id)
    service = service_for(record)
    customer = user(f"transition-customer-{initial}-{target}@example.com", "customer")
    booking = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status=initial)
    db.session.add(booking)
    db.session.commit()
    reference = booking.public_reference
    booking_id = booking.id
    token = set_session(client, account)

    response = client.post(
        f"/provider/bookings/{reference}/status",
        data={"csrf_token": token, "status": target},
    )

    assert response.status_code == expected_status
    with app.app_context():
        assert db.session.get(Booking, booking_id).status == (target if expected_status == 302 else initial)


def test_provider_dashboard_only_shows_current_booking_actions_and_cancel_confirmation(app, client):
    account = user("transition-ui@example.com", "provider")
    record = provider("TRANSITION-UI", user_id=account.id)
    service = service_for(record)
    customer = user("transition-ui-customer@example.com", "customer")
    pending = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status="pending")
    confirmed = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status="confirmed")
    cancelled = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status="cancelled")
    completed = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status="completed")
    db.session.add_all([pending, confirmed, cancelled, completed])
    db.session.commit()

    set_session(client, account)
    page = client.get("/provider/dashboard")

    assert page.status_code == 200
    assert b"onsubmit=" not in page.data
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert b"addEventListener('submit'" in script.data
    assert b"form.elements.status.value === 'cancelled'" in script.data
    assert b"window.confirm('Are you sure you want to cancel this booking?')" in script.data
    assert page.data.count(b"Complete") == 1
    assert page.data.count(b"Confirm") == 1


def test_provider_dashboard_handles_availability_update_without_raw_json(app, client):
    account = user("availability-ui@example.com", "provider")
    record = provider("AVAILABILITY-UI", user_id=account.id)
    set_session(client, account)
    page = client.get("/provider/dashboard")
    script = client.get("/static/app.js")
    assert b'class="availability-form"' in page.data
    assert b"availability-message" in page.data
    assert b"event.preventDefault()" in script.data
    assert b"Availability updated to ${label}." in script.data
    assert client.post("/provider/availability", data={"csrf_token": csrf_token(client), "availability": "offline"}).status_code == 200
    with app.app_context():
        assert db.session.get(Provider, record.id).availability == "offline"


def test_provider_customer_directions_is_owner_scoped_and_safe(app, client):
    provider_user = user("directions-provider@example.com", "provider")
    other_provider_user = user("directions-other-provider@example.com", "provider")
    customer = user("directions-customer@example.com", "customer")
    record = provider("DIRECTIONS-OWNER", user_id=provider_user.id)
    other_record = provider("DIRECTIONS-OTHER", user_id=other_provider_user.id)
    service = service_for(record)
    booking = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id,
                      customer_latitude=25.005, customer_longitude=88.14,
                      customer_location_label="Malda")
    db.session.add(booking)
    db.session.commit()
    reference = booking.public_reference

    token = set_session(client, provider_user)
    response = client.post(f"/provider/bookings/{reference}/directions",
                           data={"csrf_token": token, "latitude": "25.1", "longitude": "88.2"})
    assert response.status_code == 200
    assert response.get_json()["provider"] == {"latitude": 25.1, "longitude": 88.2}
    assert response.get_json()["customer"] == {"latitude": 25.005, "longitude": 88.14, "label": "Malda"}
    directions_page = client.get(f"/provider/bookings/{reference}/directions")
    assert directions_page.status_code == 200
    assert directions_page.headers.get("Location") is None
    assert directions_page.is_json is False
    assert b'provider_directions.js?v=20260829-5' in directions_page.data
    assert b'provider-marker' in directions_page.data or b'directions-map' in directions_page.data
    assert b"google.com/maps" not in directions_page.data
    assert b"maps.google" not in directions_page.data
    assert client.post(f"/provider/bookings/{reference}/directions",
                       data={"csrf_token": token, "latitude": "91", "longitude": "88"}).status_code == 400

    token = set_session(client, other_provider_user)
    assert client.post(f"/provider/bookings/{reference}/directions",
                       data={"csrf_token": token}).status_code == 404
    set_session(client, provider_user)
    dashboard = client.get("/provider/dashboard").data
    assert f'href="/provider/bookings/{reference}/directions"'.encode() in dashboard
    assert b'<a class="button button-quiet full-button customer-directions"' in dashboard
    assert b'onclick=' not in dashboard
    assert b'javascript:' not in dashboard
    assert b"google.com/maps" not in dashboard
    assert b"maps.google" not in dashboard
    assert b"window.location" not in client.get("/static/app.js").data
    assert b"window.open" not in client.get("/static/app.js").data


def test_provider_directions_uses_configured_routing_service(app, client, monkeypatch):
    provider_user = user("routing-provider@example.com", "provider")
    record = provider("ROUTING-OWNER", user_id=provider_user.id)
    service = service_for(record)
    customer = user("routing-customer@example.com", "customer")
    booking = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id,
                      customer_latitude=17.385, customer_longitude=78.4867,
                      customer_location_label="Hyderabad")
    db.session.add(booking)
    db.session.commit()
    requested = []

    class FakeResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({"code": "Ok", "routes": [{
                "distance": 1550000, "duration": 72000,
                "geometry": {"type": "LineString", "coordinates": [[88.1, 22.5], [78.4, 17.4]]},
                "legs": [{"steps": [{"name": "NH route", "distance": 1550000}]}],
            }]}).encode()

    def fake_urlopen(url, timeout):
        requested.append((url, timeout))
        return FakeResponse()

    monkeypatch.setattr("app.routes.provider.urlopen", fake_urlopen)
    app.config["ROUTING_SERVICE_URL"] = "http://routing.test:5050"
    token = set_session(client, provider_user)
    response = client.post(f"/provider/bookings/{booking.public_reference}/directions", data={"csrf_token": token})
    payload = response.get_json()
    assert response.status_code == 200
    assert requested[0][0].startswith("http://routing.test:5050/route/v1/driving/")
    assert "router.project-osrm.org" not in requested[0][0]
    assert payload["route"]["distance_meters"] == 1550000
    assert payload["route"]["duration_seconds"] == 72000
    assert len(payload["route"]["geometry"]["coordinates"]) == 2
    assert len(payload["route"]["steps"]) == 1


def test_provider_directions_routing_failure_is_controlled(app, client, monkeypatch):
    provider_user = user("routing-failure-provider@example.com", "provider")
    record = provider("ROUTING-FAILURE", user_id=provider_user.id)
    service = service_for(record)
    customer = user("routing-failure-customer@example.com", "customer")
    booking = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id,
                      customer_latitude=17.385, customer_longitude=78.4867)
    db.session.add(booking)
    db.session.commit()
    def fail_urlopen(url, timeout):
        raise URLError("unavailable")
    from urllib.error import URLError
    monkeypatch.setattr("app.routes.provider.urlopen", fail_urlopen)
    token = set_session(client, provider_user)
    response = client.post(f"/provider/bookings/{booking.public_reference}/directions", data={"csrf_token": token})
    assert response.status_code == 200
    assert response.get_json()["route"] == {"available": False}


def test_completed_booking_supports_one_rating_per_party_and_updates_provider_aggregate(app, client):
    customer = user("review-customer@example.com", "customer")
    provider_user = user("review-provider@example.com", "provider")
    record = provider("REVIEW-PROVIDER", user_id=provider_user.id)
    service = service_for(record)
    booking = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status="completed")
    db.session.add(booking)
    db.session.commit()
    reference = booking.public_reference

    token = set_session(client, customer)
    response = client.post(f"/customer/bookings/{reference}/review", data={"csrf_token": token, "rating": "5"})
    assert response.status_code == 201
    assert client.post(f"/customer/bookings/{reference}/review", data={"csrf_token": token, "rating": "4"}).status_code == 409

    token = set_session(client, provider_user)
    assert client.post(f"/provider/bookings/{reference}/review", data={"csrf_token": token, "rating": "4"}).status_code == 201
    with app.app_context():
        refreshed = db.session.get(Provider, record.id)
        assert refreshed.reviews_count == 1
        assert refreshed.rating == 5
        assert Review.query.filter_by(booking_id=booking.id).count() == 2


@pytest.mark.parametrize("status", ["pending", "confirmed", "cancelled"])
def test_non_completed_booking_cannot_be_rated(app, client, status):
    customer = user(f"review-blocked-{status}@example.com", "customer")
    provider_user = user(f"review-blocked-provider-{status}@example.com", "provider")
    record = provider(f"REVIEW-BLOCKED-{status}", user_id=provider_user.id)
    service = service_for(record)
    booking = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status=status)
    db.session.add(booking)
    db.session.commit()
    token = set_session(client, customer)
    response = client.post(f"/customer/bookings/{booking.public_reference}/review", data={"csrf_token": token, "rating": "5"})
    assert response.status_code == 400


def test_review_requires_valid_rating_and_ownership(app, client):
    customer = user("review-owner@example.com", "customer")
    other = user("review-other@example.com", "customer")
    provider_user = user("review-owner-provider@example.com", "provider")
    record = provider("REVIEW-OWNER", user_id=provider_user.id)
    service = service_for(record)
    booking = Booking(customer_id=customer.id, provider_id=record.id, service_id=service.id, status="completed")
    db.session.add(booking)
    db.session.commit()
    token = set_session(client, other)
    assert client.post(f"/customer/bookings/{booking.public_reference}/review", data={"csrf_token": token, "rating": "5"}).status_code == 404
    token = set_session(client, customer)
    assert client.post(f"/customer/bookings/{booking.public_reference}/review", data={"csrf_token": token, "rating": "6"}).status_code == 400


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
