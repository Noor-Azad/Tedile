from app.extensions import db
from app.models.notification import Notification
from app.models.rider import Rider


class NotificationService:
    RIDE_ACCEPTED = "RIDE_ACCEPTED"
    RIDE_STARTED = "RIDE_STARTED"
    RIDE_COMPLETED = "RIDE_COMPLETED"
    RIDE_CANCELLED_BY_RIDER = "RIDE_CANCELLED_BY_RIDER"
    NEW_RIDE_REQUEST = "NEW_RIDE_REQUEST"
    RIDE_CANCELLED_BY_CUSTOMER = "RIDE_CANCELLED_BY_CUSTOMER"

    @classmethod
    def _add_once(cls, user_id, ride, event_type, title, message):
        existing = Notification.query.filter_by(
            user_id=user_id,
            bike_ride_id=ride.id,
            event_type=event_type,
        ).first()
        if existing:
            return existing
        notification = Notification(
            user_id=user_id,
            bike_ride_id=ride.id,
            event_type=event_type,
            title=title,
            message=message,
        )
        db.session.add(notification)
        return notification

    @classmethod
    def notify_customer(cls, ride, event_type, title, message):
        return cls._add_once(ride.customer_id, ride, event_type, title, message)

    @classmethod
    def notify_approved_riders(cls, ride):
        riders = Rider.query.filter_by(status=Rider.APPROVED).all()
        notifications = []
        for rider in riders:
            if rider.user_id == ride.customer_id:
                continue
            notifications.append(
                cls._add_once(
                    rider.user_id,
                    ride,
                    cls.NEW_RIDE_REQUEST,
                    "New ride request",
                    "A new village bike ride request is available.",
                )
            )
        return notifications

    @classmethod
    def notify_assigned_rider_of_customer_cancellation(cls, ride):
        if not ride.rider_id:
            return None
        rider = db.session.get(Rider, ride.rider_id)
        if not rider:
            return None
        return cls._add_once(
            rider.user_id,
            ride,
            cls.RIDE_CANCELLED_BY_CUSTOMER,
            "Ride cancelled",
            "The customer cancelled this ride.",
        )

    @classmethod
    def notify_rider_cancellation(cls, ride):
        return cls.notify_customer(
            ride,
            cls.RIDE_CANCELLED_BY_RIDER,
            "Ride cancelled",
            "The assigned Rider cancelled your ride.",
        )
