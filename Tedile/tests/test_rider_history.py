from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.bike_ride import BikeRide
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


def make_user(email, role="customer"):
    user = User(email=email, name=email.split("@")[0], role=role, phone="+910000000000")
    user.set_password("password123")
    db.session.add(user)
    db.session.commit()
    return user


def make_rider(user, status=Rider.APPROVED):
    rider = Rider(
        user_id=user.id,
        bike_make_model="Hero Splendor",
        bike_registration_number="WB12AB1234",
        license_number="DL-1234567890",
        license_expiry_date=date.today() + timedelta(days=365),
        status=status,
    )
    db.session.add(rider)
    db.session.commit()
    return rider


def login(client, user):
    with client.session_transaction() as session:
        session["user"] = user.to_session_dict()


def make_ride(customer, rider, status, label="Malda"):
    ride = BikeRide(
        customer_id=customer.id,
        rider_id=rider.id,
        pickup_address=f"{label} Pickup",
        pickup_latitude=25.0,
        pickup_longitude=88.0,
        destination_address=f"{label} Destination",
        destination_latitude=25.1,
        destination_longitude=88.1,
        estimated_fare=Decimal("75.00"),
        fare_currency="INR",
        pricing_version="v2",
        pricing_base_fare=Decimal("75.00"),
    )
    db.session.add(ride)
    db.session.commit()
    if status == BikeRide.COMPLETED:
        ride.transition_to(BikeRide.ACCEPTED)
        ride.transition_to(BikeRide.IN_PROGRESS)
        ride.transition_to(BikeRide.COMPLETED)
    elif status == BikeRide.CANCELLED:
        ride.transition_to(BikeRide.CANCELLED)
    elif status == BikeRide.ACCEPTED:
        ride.transition_to(BikeRide.ACCEPTED)
    db.session.commit()
    return ride


def test_approved_rider_can_view_assigned_completed_and_cancelled_history(app, client):
    rider_user = make_user("history-rider@example.com")
    rider = make_rider(rider_user)
    customer = make_user("history-customer@example.com")
    completed = make_ride(customer, rider, BikeRide.COMPLETED, "Completed")
    cancelled = make_ride(customer, rider, BikeRide.CANCELLED, "Cancelled")
    active = make_ride(customer, rider, BikeRide.ACCEPTED, "Active")
    completed.created_at = datetime(2026, 8, 23, 11, 0, 44, 412694)
    db.session.commit()
    login(client, rider_user)

    response = client.get("/rider/rides/history")

    assert response.status_code == 200
    assert b"Ride History" in response.data
    assert b"COMPLETED" in response.data
    assert b"CANCELLED" in response.data
    assert b"Completed Pickup" in response.data
    assert b"Cancelled Pickup" in response.data
    assert b"Active Pickup" not in response.data
    assert b"INR 75.00" in response.data
    assert b"23 Aug 2026, 11:00 AM" in response.data
    assert b"2026-08-23 11:00:44.412694" not in response.data
    assert client.get(f"/rider/rides/history/{completed.id}").status_code == 200


def test_rider_history_is_ownership_scoped_and_id_tampering_fails(app, client):
    first_user = make_user("history-first@example.com")
    first = make_rider(first_user)
    second_user = make_user("history-second@example.com")
    second = make_rider(second_user)
    customer = make_user("history-owner@example.com")
    other_ride = make_ride(customer, second, BikeRide.COMPLETED, "Other")
    login(client, first_user)

    response = client.get("/rider/rides/history")

    assert response.status_code == 200
    assert b"Other Pickup" not in response.data
    assert client.get(f"/rider/rides/history/{other_ride.id}").status_code == 404


def test_pending_rider_and_unauthenticated_user_cannot_access_history(app, client):
    pending_user = make_user("pending-history@example.com")
    make_rider(pending_user, Rider.PENDING)
    login(client, pending_user)
    assert client.get("/rider/rides/history").status_code == 403

    with client.session_transaction() as session:
        session.clear()
    assert client.get("/rider/rides/history").status_code == 302


def test_rider_history_is_read_only_and_customer_history_remains_available(app, client):
    rider_user = make_user("readonly-history-rider@example.com")
    rider = make_rider(rider_user)
    customer = make_user("readonly-history-customer@example.com")
    ride = make_ride(customer, rider, BikeRide.COMPLETED, "Customer")

    login(client, rider_user)
    assert client.post("/rider/rides/history").status_code == 405

    login(client, customer)
    customer_history = client.get("/customer/rides")
    assert customer_history.status_code == 200
    assert b"Customer Pickup" in customer_history.data
    assert b"INR 75.00" in customer_history.data
