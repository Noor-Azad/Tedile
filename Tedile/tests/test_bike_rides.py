from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.bike_ride import BikeRide
from app.models.rider import Rider
from app.models.user import User
from app.models.fare_configuration import FareConfiguration
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


def login(client, user):
    client.get("/")
    with client.session_transaction() as session:
        session["user"] = user.to_session_dict()


def csrf(client):
    client.get("/")
    with client.session_transaction() as session:
        return session["csrf_token"]


def ride_data(token):
    return {
        "csrf_token": token,
        "pickup_address": "Malda Station",
        "pickup_latitude": "25.0057",
        "pickup_longitude": "88.1398",
        "destination_address": "Malda College",
        "destination_latitude": "25.0100",
        "destination_longitude": "88.1450",
        "customer_note": "Please call on arrival.",
    }


def create_ride(customer):
    ride = BikeRide(
        customer_id=customer.id,
        pickup_address="Pickup",
        pickup_latitude=25.0,
        pickup_longitude=88.0,
        destination_address="Destination",
        destination_latitude=25.1,
        destination_longitude=88.1,
    )
    db.session.add(ride)
    db.session.commit()
    return ride


def create_rider(user, status=Rider.APPROVED):
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


def test_customer_can_request_and_view_own_ride(app, client):
    customer = make_user("ride-customer@example.com")
    login(client, customer)

    response = client.post("/customer/rides/new", data=ride_data(csrf(client)))

    assert response.status_code == 302
    ride = BikeRide.query.one()
    assert ride.status == BikeRide.REQUESTED
    assert ride.estimated_fare == Decimal("50.00")
    assert ride.fare_currency == "INR"
    assert ride.pricing_version == "v1"
    assert ride.customer_id == customer.id
    assert client.get("/customer/rides").status_code == 200
    assert b"Malda Station" in client.get(f"/customer/rides/{ride.id}").data


def test_customer_ride_request_requires_login_and_csrf(client):
    assert client.get("/customer/rides/new").status_code == 302


def test_customer_sees_default_fare_before_submitting(app, client):
    customer = make_user("fare-preview@example.com")
    login(client, customer)

    response = client.get("/customer/rides/new")

    assert response.status_code == 200
    assert b"INR 50.00" in response.data


def test_customer_cannot_view_or_cancel_another_customers_ride(app, client):
    owner = make_user("ride-owner@example.com")
    other = make_user("ride-other@example.com")
    ride = create_ride(owner)
    login(client, other)

    assert client.get(f"/customer/rides/{ride.id}").status_code == 404
    assert client.post(f"/customer/rides/{ride.id}/cancel", data={"csrf_token": csrf(client)}).status_code == 404


@pytest.mark.parametrize("blocked_status", [BikeRide.ACCEPTED, BikeRide.IN_PROGRESS, BikeRide.COMPLETED])
def test_customer_can_cancel_requested_but_not_other_lifecycle_states(app, client, blocked_status):
    customer = make_user("ride-cancel@example.com")
    ride = create_ride(customer)
    login(client, customer)

    response = client.post(f"/customer/rides/{ride.id}/cancel", data={"csrf_token": csrf(client)})
    assert response.status_code == 302
    assert db.session.get(BikeRide, ride.id).status == BikeRide.CANCELLED

    blocked = create_ride(customer)
    rider_user = make_user(f"cancel-rider-{blocked_status.lower()}@example.com")
    rider = create_rider(rider_user)
    blocked.rider_id = rider.id
    if blocked_status in (BikeRide.ACCEPTED, BikeRide.IN_PROGRESS, BikeRide.COMPLETED):
        blocked.transition_to(BikeRide.ACCEPTED)
    if blocked_status in (BikeRide.IN_PROGRESS, BikeRide.COMPLETED):
        blocked.transition_to(BikeRide.IN_PROGRESS)
    if blocked_status == BikeRide.COMPLETED:
        blocked.transition_to(BikeRide.COMPLETED)
    db.session.commit()
    assert client.post(f"/customer/rides/{blocked.id}/cancel", data={"csrf_token": csrf(client)}).status_code == 409
    assert db.session.get(BikeRide, blocked.id).status == blocked_status


def test_pending_rider_cannot_accept(app, client):
    customer = make_user("pending-rider@example.com")
    rider = create_rider(customer, Rider.PENDING)
    owner = make_user("pending-ride-owner@example.com")
    ride = create_ride(owner)
    login(client, customer)

    assert client.post(f"/rider/rides/{ride.id}/accept", data={"csrf_token": csrf(client)}).status_code == 403
    assert db.session.get(BikeRide, ride.id).status == BikeRide.REQUESTED


@pytest.mark.parametrize("status", [BikeRide.ACCEPTED, BikeRide.IN_PROGRESS, BikeRide.COMPLETED, BikeRide.CANCELLED])
def test_approved_rider_cannot_accept_non_requested_ride(app, client, status):
    rider_user = make_user(f"non-requested-rider-{status.lower()}@example.com")
    rider = create_rider(rider_user)
    customer = make_user(f"non-requested-owner-{status.lower()}@example.com")
    ride = create_ride(customer)
    ride.rider_id = rider.id if status != BikeRide.CANCELLED else None
    if status in (BikeRide.ACCEPTED, BikeRide.IN_PROGRESS, BikeRide.COMPLETED):
        ride.transition_to(BikeRide.ACCEPTED)
    if status in (BikeRide.IN_PROGRESS, BikeRide.COMPLETED):
        ride.transition_to(BikeRide.IN_PROGRESS)
    if status == BikeRide.COMPLETED:
        ride.transition_to(BikeRide.COMPLETED)
    if status == BikeRide.CANCELLED:
        ride.transition_to(BikeRide.CANCELLED)
    db.session.commit()
    login(client, rider_user)

    assert client.post(f"/rider/rides/{ride.id}/accept", data={"csrf_token": csrf(client)}).status_code == 302
    assert db.session.get(BikeRide, ride.id).status == status


def test_approved_rider_completes_lifecycle(app, client):
    rider_user = make_user("approved-rider@example.com")
    rider = create_rider(rider_user)
    customer = make_user("approved-ride-owner@example.com")
    ride = create_ride(customer)
    login(client, rider_user)

    assert client.get("/rider/dashboard").status_code == 200
    assert b"Pickup" in client.get("/rider/dashboard").data
    assert client.post(f"/rider/rides/{ride.id}/accept", data={"csrf_token": csrf(client)}).status_code == 302
    assert db.session.get(BikeRide, ride.id).status == BikeRide.ACCEPTED
    assert client.post(f"/rider/rides/{ride.id}/start", data={"csrf_token": csrf(client)}).status_code == 302
    assert db.session.get(BikeRide, ride.id).status == BikeRide.IN_PROGRESS
    assert client.post(f"/rider/rides/{ride.id}/complete", data={"csrf_token": csrf(client), "estimated_fare": "1.00"}).status_code == 302
    completed = db.session.get(BikeRide, ride.id)
    assert completed.status == BikeRide.COMPLETED
    assert completed.final_fare == Decimal("50.00")


def test_only_one_approved_rider_can_accept_and_other_rider_cannot_manage_it(app, client):
    first_user = make_user("first-rider@example.com")
    first = create_rider(first_user)
    second_user = make_user("second-rider@example.com")
    create_rider(second_user)
    customer = make_user("single-accept-owner@example.com")
    ride = create_ride(customer)

    login(client, first_user)
    assert client.post(f"/rider/rides/{ride.id}/accept", data={"csrf_token": csrf(client)}).status_code == 302
    login(client, second_user)
    assert client.post(f"/rider/rides/{ride.id}/accept", data={"csrf_token": csrf(client)}).status_code == 302
    assert client.post(f"/rider/rides/{ride.id}/start", data={"csrf_token": csrf(client)}).status_code == 404
    assert client.post(f"/rider/rides/{ride.id}/complete", data={"csrf_token": csrf(client)}).status_code == 404
    assert db.session.get(BikeRide, ride.id).rider_id == first.id


def test_atomic_claim_allows_only_one_rider_before_commit(app):
    first_user = make_user("atomic-first@example.com")
    first = create_rider(first_user)
    second_user = make_user("atomic-second@example.com")
    second = create_rider(second_user)
    customer = make_user("atomic-owner@example.com")
    ride = create_ride(customer)

    assert BikeRide.claim(ride.id, first.id) is True
    assert BikeRide.claim(ride.id, second.id) is False
    db.session.commit()
    assert db.session.get(BikeRide, ride.id).rider_id == first.id


def test_all_ride_mutations_require_csrf(app, client):
    customer = make_user("csrf-ride-customer@example.com")
    login(client, customer)
    assert client.post("/customer/rides/new", data={}).status_code == 400
    ride = create_ride(customer)
    assert client.post(f"/customer/rides/{ride.id}/cancel", data={}).status_code == 400

    rider_user = make_user("csrf-ride-rider@example.com")
    rider = create_rider(rider_user)
    login(client, rider_user)
    assert client.post(f"/rider/rides/{ride.id}/accept", data={}).status_code == 400
    ride.rider_id = rider.id
    ride.transition_to(BikeRide.ACCEPTED)
    db.session.commit()
    assert client.post(f"/rider/rides/{ride.id}/start", data={}).status_code == 400
    ride.transition_to(BikeRide.IN_PROGRESS)
    db.session.commit()
    assert client.post(f"/rider/rides/{ride.id}/complete", data={}).status_code == 400


def test_customer_fare_input_cannot_override_server_snapshot(app, client):
    customer = make_user("fare-tamper@example.com")
    login(client, customer)
    data = ride_data(csrf(client))
    data["estimated_fare"] = "999999.99"

    assert client.post("/customer/rides/new", data=data).status_code == 302
    ride = BikeRide.query.one()
    assert ride.estimated_fare == Decimal("50.00")
    assert ride.pricing_base_fare == Decimal("50.00")


def test_admin_can_create_new_pricing_version_without_changing_existing_rides(app, client):
    customer = make_user("historical-fare@example.com")
    login(client, customer)
    first = client.post("/customer/rides/new", data=ride_data(csrf(client)))
    assert first.status_code == 302
    old_ride = BikeRide.query.one()

    admin = make_user("fare-admin@example.com", "admin")
    login(client, admin)
    assert b"INR" in client.get("/admin/pricing").data
    update = client.post("/admin/pricing", data={"csrf_token": csrf(client), "base_fare": "75.00", "currency": "INR"})
    assert update.status_code == 302
    configuration = FareConfiguration.current()
    assert configuration.base_fare == Decimal("75.00")
    assert configuration.pricing_version != old_ride.pricing_version

    login(client, customer)
    second = client.post("/customer/rides/new", data=ride_data(csrf(client)))
    assert second.status_code == 302
    rides = BikeRide.query.order_by(BikeRide.id).all()
    assert rides[0].estimated_fare == Decimal("50.00")
    assert rides[1].estimated_fare == Decimal("75.00")
    assert rides[0].pricing_version != rides[1].pricing_version


def test_non_admin_cannot_change_pricing_and_pricing_change_requires_csrf(app, client):
    customer = make_user("non-admin-fare@example.com")
    login(client, customer)
    assert client.get("/admin/pricing").status_code == 403

    admin = make_user("csrf-fare-admin@example.com", "admin")
    login(client, admin)
    assert client.post("/admin/pricing", data={"base_fare": "80.00", "currency": "INR"}).status_code == 400


def test_cancelled_ride_retains_fare_snapshot_without_final_fare(app, client):
    customer = make_user("cancelled-fare@example.com")
    login(client, customer)
    assert client.post("/customer/rides/new", data=ride_data(csrf(client))).status_code == 302
    ride = BikeRide.query.one()
    assert client.post(f"/customer/rides/{ride.id}/cancel", data={"csrf_token": csrf(client)}).status_code == 302
    cancelled = db.session.get(BikeRide, ride.id)
    assert cancelled.status == BikeRide.CANCELLED
    assert cancelled.estimated_fare == Decimal("50.00")
    assert cancelled.final_fare is None


def test_invalid_transitions_are_rejected_by_model(app):
    customer = make_user("transition-owner@example.com")
    ride = create_ride(customer)
    with pytest.raises(ValueError):
        ride.transition_to(BikeRide.COMPLETED)
    ride.status = BikeRide.COMPLETED
    with pytest.raises(ValueError):
        ride.transition_to(BikeRide.ACCEPTED)


def test_admin_can_view_rides_and_non_admin_cannot(app, client):
    customer = make_user("admin-ride-customer@example.com")
    create_ride(customer)
    non_admin = make_user("ride-non-admin@example.com")
    login(client, non_admin)
    assert client.get("/admin/rides").status_code == 403

    admin = make_user("ride-admin@example.com", "admin")
    login(client, admin)
    response = client.get("/admin/rides")
    assert response.status_code == 200
    assert b"Pickup" in response.data
