import pytest

from app.extensions import db
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


def login_customer(client, app):
    with app.app_context():
        customer = User(email="bike-ui@example.com", name="Bike Customer", role="customer")
        customer.set_password("password123")
        db.session.add(customer)
        db.session.commit()
        customer_session = customer.to_session_dict()

    with client.session_transaction() as session:
        session["user"] = customer_session


def test_customer_dashboard_exposes_bike_ride_entry_points(app, client):
    login_customer(client, app)

    response = client.get("/customer/dashboard")

    assert response.status_code == 200
    assert b"VILLAGE BIKE RIDE" in response.data
    assert b"Book a Ride" in response.data
    assert b"Become a Rider" in response.data
    assert b"/customer/rides/new" in response.data
    assert b"/customer/rider/apply" in response.data


@pytest.mark.parametrize(
    "path, heading",
    [
        ("/customer/rides/new", b"Book a Ride"),
        ("/customer/rider/apply", b"Become a Rider"),
    ],
)
def test_bike_ride_entry_pages_are_customer_only(app, client, path, heading):
    login_customer(client, app)

    response = client.get(path)

    assert response.status_code == 200
    assert heading in response.data
    if path == "/customer/rides/new":
        assert b"Request Ride" in response.data
    else:
        assert b"Submit application" in response.data


@pytest.mark.parametrize("path", ["/customer/rides/new", "/customer/rider/apply"])
def test_bike_ride_entry_pages_require_customer_login(client, path):
    response = client.get(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_bike_ride_booking_page_requires_csrf_for_post(app, client):
    login_customer(client, app)

    assert client.post("/customer/rides/new").status_code == 400
