from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models.rider import Rider
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
    with client.session_transaction() as session:
        return session["csrf_token"]


def create_user(email, role="customer"):
    user = User(email=email, name=role.title(), role=role, phone="+910000000000")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def login_as(client, user):
    csrf_token(client)
    with client.session_transaction() as session:
        session["user"] = user.to_session_dict()


def application_data(token):
    return {
        "csrf_token": token,
        "bike_make_model": "Hero Splendor",
        "bike_registration_number": "WB12AB1234",
        "license_number": "DL-1234567890",
        "license_expiry_date": (date.today() + timedelta(days=365)).isoformat(),
    }


def test_unauthenticated_user_cannot_submit_application(client):
    response = client.post("/customer/rider/apply", data={})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_authenticated_customer_can_open_application(app, client):
    customer = create_user("rider-form@example.com")
    login_as(client, customer)

    response = client.get("/customer/rider/apply")

    assert response.status_code == 200
    assert b"Bike make and model" in response.data
    assert b"Driving licence number" in response.data
    assert b'action="/customer/rider/apply"' in response.data


def test_valid_application_creates_pending_rider(app, client):
    customer = create_user("rider-submit@example.com")
    login_as(client, customer)
    response = client.post("/customer/rider/apply", data=application_data(csrf_token(client)))

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/customer/rider/apply")
    with app.app_context():
        rider = Rider.query.one()
        assert rider.user_id == customer.id
        assert rider.status == Rider.PENDING
        assert rider.bike_make_model == "Hero Splendor"
        assert rider.bike_registration_number == "WB12AB1234"
        assert rider.license_number == "DL-1234567890"


@pytest.mark.parametrize(
    "field,value",
    [
        ("bike_make_model", ""),
        ("license_expiry_date", "not-a-date"),
        ("license_expiry_date", (date.today() - timedelta(days=1)).isoformat()),
    ],
)
def test_invalid_application_is_rejected(client, field, value):
    customer = create_user(f"invalid-{field}-{value}@example.com")
    login_as(client, customer)
    data = application_data(csrf_token(client))
    data[field] = value

    response = client.post("/customer/rider/apply", data=data)

    assert response.status_code == 400
    assert b"rider application" in response.data.lower() or b"licence" in response.data.lower()
    assert Rider.query.count() == 0


def test_duplicate_application_is_prevented_and_status_is_displayed(app, client):
    customer = create_user("rider-duplicate@example.com")
    login_as(client, customer)
    token = csrf_token(client)
    first = client.post("/customer/rider/apply", data=application_data(token))
    duplicate = client.post("/customer/rider/apply", data=application_data(token))

    assert first.status_code == 302
    assert duplicate.status_code == 409
    assert b"already have a rider application" in duplicate.data
    status_page = client.get("/customer/rider/apply")
    assert b"under review" in status_page.data
    dashboard = client.get("/customer/dashboard")
    assert dashboard.status_code == 200
    assert b"Application under review" in dashboard.data
    with app.app_context():
        assert Rider.query.count() == 1


def test_admin_can_view_and_approve_rider(app, client):
    customer = create_user("rider-approval@example.com")
    login_as(client, customer)
    client.post("/customer/rider/apply", data=application_data(csrf_token(client)))
    rider = Rider.query.one()
    admin = create_user("rider-admin@example.com", "admin")
    login_as(client, admin)

    listing = client.get("/admin/riders")
    approve = client.post(f"/admin/riders/{rider.id}/approve", data={"csrf_token": csrf_token(client)})

    assert listing.status_code == 200
    assert b"rider-approval@example.com" in listing.data
    assert approve.status_code == 302
    with app.app_context():
        assert db.session.get(Rider, rider.id).status == Rider.APPROVED
    login_as(client, customer)
    assert b"approved" in client.get("/customer/rider/apply").data.lower()


def test_admin_can_reject_rider_and_non_admin_cannot_change_status(app, client):
    customer = create_user("rider-rejection@example.com")
    login_as(client, customer)
    client.post("/customer/rider/apply", data=application_data(csrf_token(client)))
    rider = Rider.query.one()

    assert client.post(f"/admin/riders/{rider.id}/approve", data={"csrf_token": csrf_token(client)}).status_code == 403
    with app.app_context():
        assert db.session.get(Rider, rider.id).status == Rider.PENDING

    admin = create_user("rider-reject-admin@example.com", "admin")
    login_as(client, admin)
    response = client.post(f"/admin/riders/{rider.id}/reject", data={"csrf_token": csrf_token(client)})

    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Rider, rider.id).status == Rider.REJECTED
    login_as(client, customer)
    assert b"rejected" in client.get("/customer/rider/apply").data.lower()


def test_customer_dashboard_remains_functional(app, client):
    customer = create_user("rider-dashboard@example.com")
    login_as(client, customer)

    response = client.get("/customer/dashboard")

    assert response.status_code == 200
    assert b"Find help for your next task" in response.data
    assert b"Book a Ride" in response.data
