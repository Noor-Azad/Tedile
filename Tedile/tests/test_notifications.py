from datetime import date, timedelta
from decimal import Decimal

import pytest
from flask import url_for

from app.extensions import db
from app.models.bike_ride import BikeRide
from app.models.notification import Notification
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


def make_requested_ride(customer):
    ride = BikeRide(
        customer_id=customer.id,
        pickup_address="Notification Pickup",
        pickup_latitude=25.0,
        pickup_longitude=88.0,
        destination_address="Notification Destination",
        destination_latitude=25.1,
        destination_longitude=88.1,
        estimated_fare=Decimal("75.00"),
        pricing_base_fare=Decimal("75.00"),
        pricing_version="v2",
        fare_currency="INR",
    )
    db.session.add(ride)
    db.session.commit()
    return ride


def test_lifecycle_notifications_are_recipient_scoped_and_idempotent(app, client):
    customer = make_user("notifications-customer@example.com")
    rider_user = make_user("notifications-rider@example.com")
    rider = make_rider(rider_user)
    ride = make_requested_ride(customer)

    token = login(client, rider_user)
    assert client.post(f"/rider/rides/{ride.id}/accept", data={"csrf_token": token}).status_code == 302
    assert client.post(f"/rider/rides/{ride.id}/start", data={"csrf_token": token}).status_code == 302
    assert client.post(f"/rider/rides/{ride.id}/complete", data={"csrf_token": token}).status_code == 302

    customer_events = Notification.query.filter_by(user_id=customer.id, bike_ride_id=ride.id).all()
    assert {notification.event_type for notification in customer_events} == {
        NotificationServiceName.RIDE_ACCEPTED,
        NotificationServiceName.RIDE_STARTED,
        NotificationServiceName.RIDE_COMPLETED,
    }
    assert all(notification.is_read is False for notification in customer_events)
    assert Notification.query.filter_by(user_id=rider_user.id, bike_ride_id=ride.id).count() == 0

    # Replaying the event helper does not create a second record.
    from app.services.notification_service import NotificationService

    NotificationService.notify_customer(
        ride,
        NotificationService.RIDE_COMPLETED,
        "Ride completed",
        "Your village bike ride is complete.",
    )
    db.session.commit()
    assert Notification.query.filter_by(
        user_id=customer.id,
        bike_ride_id=ride.id,
        event_type=NotificationService.RIDE_COMPLETED,
    ).count() == 1


class NotificationServiceName:
    RIDE_ACCEPTED = "RIDE_ACCEPTED"
    RIDE_STARTED = "RIDE_STARTED"
    RIDE_COMPLETED = "RIDE_COMPLETED"


def test_new_request_notifies_only_approved_riders_and_persists(app, client):
    customer = make_user("new-request-customer@example.com")
    approved_user = make_user("approved-notification-rider@example.com")
    pending_user = make_user("pending-notification-rider@example.com")
    rejected_user = make_user("rejected-notification-rider@example.com")
    approved = make_rider(approved_user, Rider.APPROVED)
    pending = make_rider(pending_user, Rider.PENDING)
    rejected = make_rider(rejected_user, Rider.REJECTED)

    token = login(client, customer)
    response = client.post(
        "/customer/rides/new",
        data={
            "csrf_token": token,
            "pickup_address": "Village market",
            "pickup_latitude": "25.0",
            "pickup_longitude": "88.0",
            "destination_address": "Station",
            "destination_latitude": "25.1",
            "destination_longitude": "88.1",
        },
    )
    assert response.status_code == 302
    ride = BikeRide.query.one()
    assert Notification.query.filter_by(user_id=approved_user.id, bike_ride_id=ride.id).count() == 1
    assert Notification.query.filter_by(user_id=pending_user.id, bike_ride_id=ride.id).count() == 0
    assert Notification.query.filter_by(user_id=rejected_user.id, bike_ride_id=ride.id).count() == 0
    assert Notification.query.filter_by(user_id=customer.id, bike_ride_id=ride.id).count() == 0


def test_notification_list_and_mark_read_require_auth_csrf_and_ownership(app, client):
    customer = make_user("list-notification-customer@example.com")
    other = make_user("other-notification-user@example.com")
    ride = make_requested_ride(customer)
    from app.services.notification_service import NotificationService

    notification = NotificationService.notify_customer(
        ride,
        NotificationService.RIDE_ACCEPTED,
        "Ride accepted",
        "A Rider accepted your ride request.",
    )
    db.session.commit()

    assert client.get("/notifications").status_code == 302
    token = login(client, other)
    assert b"Ride accepted" not in client.get("/notifications").data
    assert client.post(
        f"/notifications/{notification.id}/read", data={"csrf_token": token}
    ).status_code == 404

    token = login(client, customer)
    response = client.get("/notifications")
    assert response.status_code == 200
    assert b"Ride accepted" in response.data
    assert client.post(f"/notifications/{notification.id}/read").status_code == 400
    assert client.post(
        f"/notifications/{notification.id}/read", data={"csrf_token": token}
    ).status_code == 302
    db.session.refresh(notification)
    assert notification.is_read is True
    assert notification.read_at is not None


def test_customer_dashboard_renders_notification_entry_point(app, client):
    customer = make_user("dashboard-notification-customer@example.com")
    token = login(client, customer)

    response = client.get("/customer/dashboard")

    assert response.status_code == 200
    assert b'href="/notifications"' in response.data
    assert b">Notifications<" in response.data
    assert client.get("/notifications").status_code == 200
    assert token


def test_notification_endpoint_is_registered_in_the_application_factory(app):
    assert "notifications" in app.blueprints
    rules = {
        rule.endpoint: str(rule)
        for rule in app.url_map.iter_rules()
        if "notification" in rule.endpoint
    }
    assert rules["notifications.list_notifications"] == "/notifications"
    with app.test_request_context():
        assert url_for("notifications.list_notifications") == "/notifications"


def test_rider_cancellation_notifies_customer_and_retains_history(app, client):
    customer = make_user("rider-cancel-notification-customer@example.com")
    rider_user = make_user("rider-cancel-notification-rider@example.com")
    rider = make_rider(rider_user)
    ride = make_requested_ride(customer)
    ride.rider_id = rider.id
    ride.transition_to(BikeRide.ACCEPTED)
    db.session.commit()

    token = login(client, rider_user)
    assert client.post(f"/rider/rides/{ride.id}/cancel", data={"csrf_token": token}).status_code == 302
    db.session.refresh(ride)
    assert ride.status == BikeRide.CANCELLED
    assert Notification.query.filter_by(
        user_id=customer.id,
        bike_ride_id=ride.id,
        event_type="RIDE_CANCELLED_BY_RIDER",
    ).count() == 1

    login(client, customer)
    response = client.get("/notifications")
    assert b"The assigned Rider cancelled your ride" in response.data
