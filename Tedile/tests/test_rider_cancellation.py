from datetime import date, timedelta
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
        bike_registration_number=f"WB12AB{user.id:04d}",
        license_number=f"DL-{user.id:010d}",
        license_expiry_date=date.today() + timedelta(days=365),
        status=status,
    )
    db.session.add(rider)
    db.session.commit()
    return rider


def login(client, user):
    client.get("/")
    with client.session_transaction() as session:
        session["user"] = user.to_session_dict()
        return session["csrf_token"]


def make_ride(customer, rider, status=BikeRide.ACCEPTED):
    ride = BikeRide(
        customer_id=customer.id,
        rider_id=rider.id,
        pickup_address="Cancellation Pickup",
        pickup_latitude=25.0,
        pickup_longitude=88.0,
        destination_address="Cancellation Destination",
        destination_latitude=25.1,
        destination_longitude=88.1,
        estimated_fare=Decimal("75.00"),
        fare_currency="INR",
        pricing_version="v2",
        pricing_base_fare=Decimal("75.00"),
    )
    db.session.add(ride)
    db.session.commit()
    if status == BikeRide.ACCEPTED:
        ride.transition_to(BikeRide.ACCEPTED)
    elif status == BikeRide.IN_PROGRESS:
        ride.transition_to(BikeRide.ACCEPTED)
        ride.transition_to(BikeRide.IN_PROGRESS)
    elif status == BikeRide.COMPLETED:
        ride.transition_to(BikeRide.ACCEPTED)
        ride.transition_to(BikeRide.IN_PROGRESS)
        ride.transition_to(BikeRide.COMPLETED)
    elif status == BikeRide.CANCELLED:
        ride.transition_to(BikeRide.CANCELLED)
    db.session.commit()
    return ride


def test_approved_assigned_rider_can_cancel_accepted_ride_and_preserve_fare(app, client):
    rider_user = make_user("br06-rider@example.com")
    rider = make_rider(rider_user)
    customer = make_user("br06-customer@example.com")
    ride = make_ride(customer, rider)
    fare_snapshot = (ride.estimated_fare, ride.fare_currency, ride.pricing_version, ride.pricing_base_fare)
    token = login(client, rider_user)

    response = client.post(f"/rider/rides/{ride.id}/cancel", data={"csrf_token": token})

    assert response.status_code == 302
    db.session.refresh(ride)
    assert ride.status == BikeRide.CANCELLED
    assert (ride.estimated_fare, ride.fare_currency, ride.pricing_version, ride.pricing_base_fare) == fare_snapshot
    assert client.get("/rider/rides/history").status_code == 200
    assert b"CANCELLED" in client.get("/rider/rides/history").data
    login(client, customer)
    assert b"CANCELLED" in client.get(f"/customer/rides/{ride.id}").data


@pytest.mark.parametrize("status", [BikeRide.REQUESTED, BikeRide.IN_PROGRESS, BikeRide.COMPLETED, BikeRide.CANCELLED])
def test_rider_cannot_cancel_prohibited_statuses(app, client, status):
    rider_user = make_user(f"br06-{status.lower()}@example.com")
    rider = make_rider(rider_user)
    customer = make_user(f"br06-{status.lower()}-customer@example.com")
    ride = make_ride(customer, rider, status)
    token = login(client, rider_user)

    response = client.post(f"/rider/rides/{ride.id}/cancel", data={"csrf_token": token})

    assert response.status_code == 302
    db.session.refresh(ride)
    assert ride.status == status


def test_rider_cancellation_requires_assignment_approval_login_and_csrf(app, client):
    customer = make_user("br06-security-customer@example.com")
    assigned_user = make_user("br06-assigned@example.com")
    other_user = make_user("br06-other@example.com")
    pending_user = make_user("br06-pending@example.com")
    assigned = make_rider(assigned_user)
    other = make_rider(other_user)
    pending = make_rider(pending_user, Rider.PENDING)
    ride = make_ride(customer, assigned)

    other_token = login(client, other_user)
    assert client.post(f"/rider/rides/{ride.id}/cancel", data={"csrf_token": other_token}).status_code == 404
    db.session.refresh(ride)
    assert ride.status == BikeRide.ACCEPTED
    assert other.id != assigned.id

    login(client, pending_user)
    with client.session_transaction() as session:
        token = session["csrf_token"]
    assert client.post(f"/rider/rides/{ride.id}/cancel", data={"csrf_token": token}).status_code == 403
    assert client.post(f"/rider/rides/{ride.id}/cancel", data={}).status_code == 400

    client.get(f"/rider/rides/{ride.id}/cancel")
    assert client.get(f"/rider/rides/{ride.id}/cancel").status_code == 405
    with client.session_transaction() as session:
        session.clear()
    assert client.post(f"/rider/rides/{ride.id}/cancel", data={}).status_code == 302


def test_rider_dashboard_shows_cancel_only_for_accepted_rides(app, client):
    rider_user = make_user("br06-dashboard@example.com")
    rider = make_rider(rider_user)
    customer = make_user("br06-dashboard-customer@example.com")
    accepted = make_ride(customer, rider, BikeRide.ACCEPTED)
    in_progress = make_ride(customer, rider, BikeRide.IN_PROGRESS)
    token = login(client, rider_user)

    response = client.get("/rider/dashboard")

    assert response.status_code == 200
    assert f"/rider/rides/{accepted.id}/cancel".encode() in response.data
    assert f"/rider/rides/{in_progress.id}/cancel".encode() not in response.data
    assert token
