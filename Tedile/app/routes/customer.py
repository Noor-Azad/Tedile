from functools import wraps
from datetime import datetime
import math

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.service import Service
from app.models.provider_service import ProviderService
from app.models.rider import Rider
from app.models.bike_ride import BikeRide
from app.models.user import User
from app.models.fare_configuration import FareConfiguration
from app.services.notification_service import NotificationService
from app.security import csrf_protect

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


def login_required(role=None):
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapped(*args, **kwargs):
            user = session.get("user")
            if not user:
                return redirect(url_for("auth.login_page"))
            if role and user.get("role") != role:
                abort(403)
            return view_fn(*args, **kwargs)
        return wrapped
    return decorator


@customer_bp.route("/dashboard")
@login_required(role="customer")
def dashboard():
    user = session["user"]
    bookings = Booking.query.filter_by(customer_id=user["id"]).order_by(Booking.created_at.desc()).all()
    booking_dtos = []
    for booking in bookings:
        provider = Provider.query.get(booking.provider_id)
        service = Service.query.get(booking.service_id)
        if provider and service:
            booking_dtos.append(booking.to_customer_dto(provider, service))
    rider = Rider.query.filter_by(user_id=user["id"]).first()
    active_ride = BikeRide.query.filter(
        BikeRide.customer_id == user["id"],
        BikeRide.status.in_((BikeRide.REQUESTED, BikeRide.ACCEPTED, BikeRide.IN_PROGRESS)),
    ).order_by(BikeRide.created_at.desc()).first()
    return render_template("customer_dashboard.html", user=user, bookings=booking_dtos, rider=rider, active_ride=active_ride)


@customer_bp.route("/rides/new", methods=["GET", "POST"])
@login_required(role="customer")
@csrf_protect
def new_ride():
    if request.method == "GET":
        return render_template(
            "ride_request.html",
            user=session["user"],
            fare_configuration=FareConfiguration.current_snapshot(),
        )

    def coordinate(name, minimum, maximum):
        value = request.form.get(name, "").strip()
        if not value:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"Enter a valid {name.replace('_', ' ')}.")
        if not math.isfinite(parsed) or not minimum <= parsed <= maximum:
            raise ValueError(f"Enter a valid {name.replace('_', ' ')}.")
        return parsed

    pickup_address = request.form.get("pickup_address", "").strip()
    destination_address = request.form.get("destination_address", "").strip()
    customer_note = request.form.get("customer_note", "").strip()
    if not pickup_address or not destination_address:
        return render_template("ride_request.html", user=session["user"], fare_configuration=FareConfiguration.current_snapshot(), error="Pickup and destination are required."), 400
    if len(pickup_address) > 500 or len(destination_address) > 500 or len(customer_note) > 2000:
        return render_template("ride_request.html", user=session["user"], fare_configuration=FareConfiguration.current_snapshot(), error="Ride details are too long."), 400
    try:
        pickup_latitude = coordinate("pickup_latitude", -90, 90)
        pickup_longitude = coordinate("pickup_longitude", -180, 180)
        destination_latitude = coordinate("destination_latitude", -90, 90)
        destination_longitude = coordinate("destination_longitude", -180, 180)
    except ValueError as exc:
        return render_template("ride_request.html", user=session["user"], fare_configuration=FareConfiguration.current_snapshot(), error=str(exc)), 400

    fare = FareConfiguration.current_snapshot()
    ride = BikeRide(
        customer_id=session["user"]["id"],
        pickup_address=pickup_address,
        pickup_latitude=pickup_latitude,
        pickup_longitude=pickup_longitude,
        destination_address=destination_address,
        destination_latitude=destination_latitude,
        destination_longitude=destination_longitude,
        customer_note=customer_note or None,
        estimated_fare=fare["base_fare"],
        fare_currency=fare["currency"],
        pricing_version=fare["pricing_version"],
        pricing_base_fare=fare["base_fare"],
    )
    db.session.add(ride)
    db.session.flush()
    NotificationService.notify_approved_riders(ride)
    db.session.commit()
    return redirect(url_for("customer.rides"))


def _customer_ride(ride_id):
    ride = BikeRide.query.filter_by(id=ride_id, customer_id=session["user"]["id"]).first()
    if not ride:
        abort(404)
    return ride


@customer_bp.route("/rides")
@login_required(role="customer")
def rides():
    ride_list = BikeRide.query.filter_by(customer_id=session["user"]["id"]).order_by(BikeRide.created_at.desc()).all()
    return render_template("customer_rides.html", user=session["user"], rides=ride_list)


@customer_bp.route("/rides/<int:ride_id>")
@login_required(role="customer")
def ride_detail(ride_id):
    ride = _customer_ride(ride_id)
    rider = Rider.query.get(ride.rider_id) if ride.rider_id else None
    rider_user = User.query.get(rider.user_id) if rider else None
    return render_template(
        "customer_ride_detail.html",
        user=session["user"],
        ride=ride,
        rider=rider,
        rider_user=rider_user,
    )


@customer_bp.route("/rides/<int:ride_id>/cancel", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def cancel_ride(ride_id):
    ride = _customer_ride(ride_id)
    if ride.status != BikeRide.REQUESTED:
        return jsonify({"error": "Only requested rides can be cancelled."}), 409
    ride.transition_to(BikeRide.CANCELLED)
    NotificationService.notify_assigned_rider_of_customer_cancellation(ride)
    db.session.commit()
    return redirect(url_for("customer.rides"))


@customer_bp.route("/rider/apply")
@login_required(role="customer")
def rider_application():
    rider = Rider.query.filter_by(user_id=session["user"]["id"]).first()
    return render_template("rider_application.html", user=session["user"], rider=rider)


@customer_bp.route("/rider/apply", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def submit_rider_application():
    user = session["user"]
    existing = Rider.query.filter_by(user_id=user["id"]).first()
    if existing:
        return render_template("rider_application.html", user=user, rider=existing, error="You already have a rider application."), 409

    bike_make_model = (request.form.get("bike_make_model") or "").strip()
    bike_registration_number = (request.form.get("bike_registration_number") or "").strip()
    license_number = (request.form.get("license_number") or "").strip()
    license_expiry_value = (request.form.get("license_expiry_date") or "").strip()

    if not all((bike_make_model, bike_registration_number, license_number, license_expiry_value)):
        return render_template("rider_application.html", user=user, error="All rider application fields are required."), 400
    if len(bike_make_model) > 160 or len(bike_registration_number) > 80 or len(license_number) > 80:
        return render_template("rider_application.html", user=user, error="One or more rider application fields are too long."), 400

    try:
        license_expiry_date = datetime.fromisoformat(license_expiry_value).date()
    except ValueError:
        return render_template("rider_application.html", user=user, error="Enter a valid licence expiry date."), 400
    if license_expiry_date < datetime.now().date():
        return render_template("rider_application.html", user=user, error="The driving licence must not be expired."), 400

    rider = Rider(
        user_id=user["id"],
        bike_make_model=bike_make_model,
        bike_registration_number=bike_registration_number,
        license_number=license_number,
        license_expiry_date=license_expiry_date,
        status=Rider.PENDING,
    )
    db.session.add(rider)
    db.session.commit()
    return redirect(url_for("customer.rider_application"))


@customer_bp.route("/bookings", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def create_booking():
    user = session["user"]
    profile_code = request.form.get("provider_profile_code", "")
    service_slug = request.form.get("service_slug", "")
    service_id = request.form.get("service_id", type=int)
    notes = request.form.get("notes", "")
    scheduled_at_value = request.form.get("scheduled_at") or None
    if len(profile_code) > 64 or len(service_slug) > 160:
        return jsonify({"error": "Invalid booking input"}), 400
    if request.form.get("service_id") not in (None, "") and service_id is None:
        return jsonify({"error": "Invalid service_id"}), 400
    if service_id is not None and service_id <= 0:
        return jsonify({"error": "Invalid service_id"}), 400
    if len(notes) > 5000:
        return jsonify({"error": "Notes are too long"}), 400
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_value) if scheduled_at_value else None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid scheduled_at"}), 400

    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider or not provider.is_active:
        return jsonify({"error": "Provider not found"}), 404

    service = Service.query.filter_by(slug=service_slug).first() if service_slug else Service.query.get(service_id)
    if not service or not service.is_active:
        return jsonify({"error": "Service not found"}), 404

    offered = ProviderService.query.filter_by(
        provider_id=provider.id, service_id=service.id, is_active=True
    ).first()
    if not offered:
        return jsonify({"error": "Provider does not offer this service"}), 400

    booking = Booking(
        customer_id=user["id"],
        provider_id=provider.id,
        service_id=service.id,
        notes=notes,
        scheduled_at=scheduled_at,
        status="pending",
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify(booking.to_customer_dto(provider, service)), 201


@customer_bp.route("/providers/<profile_code>/contact")
@login_required(role="customer")
def provider_contact(profile_code):
    """Reveal a provider's phone/whatsapp only after an authorized booking.

    Authorization rule: the logged-in customer must have a confirmed or
    completed booking with this provider. See docs/DATA_ACCESS_POLICY.md.
    """
    user = session["user"]
    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider:
        return jsonify({"error": "Provider not found"}), 404

    authorized = Booking.query.filter(
        Booking.customer_id == user["id"],
        Booking.provider_id == provider.id,
        Booking.status.in_(("confirmed", "completed")),
    ).first()
    if not authorized:
        return jsonify({"error": "Contact details are available after a confirmed booking."}), 403

    return jsonify(provider.to_contact_dto())
