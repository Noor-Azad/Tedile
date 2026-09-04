from functools import wraps
from datetime import datetime

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.service import Service
from app.models.provider_service import ProviderService
from app.models.review import Review
from app.security import csrf_protect

customer_bp = Blueprint("customer", __name__, url_prefix="/customer")


def _customer_booking_access(view_fn):
    """Hide bookings outside the logged-in customer's scope before mutation checks."""
    @wraps(view_fn)
    def wrapped(*args, **kwargs):
        user = session["user"]
        booking_id = kwargs.get("booking_id")
        booking_reference = kwargs.get("booking_reference")
        if booking_id is not None:
            booking = Booking.query.filter_by(id=booking_id, customer_id=user["id"]).first()
        else:
            booking = next((booking for booking in Booking.query.filter_by(customer_id=user["id"]).all()
                            if booking.public_reference == booking_reference), None)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404
        return view_fn(*args, **kwargs)
    return wrapped


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
            dto = booking.to_customer_dto(provider, service)
            review = Review.query.filter_by(booking_id=booking.id, reviewer_id=user["id"]).first()
            dto["review"] = {"rating": review.rating, "comment": review.comment} if review else None
            booking_dtos.append(dto)
    return render_template("customer_dashboard.html", user=user, bookings=booking_dtos)


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
    customer_latitude = request.form.get("customer_latitude", type=float)
    customer_longitude = request.form.get("customer_longitude", type=float)
    customer_location_label = (request.form.get("customer_location_label") or "").strip() or None
    if len(profile_code) > 64 or len(service_slug) > 160:
        return jsonify({"error": "Invalid booking input"}), 400
    if request.form.get("service_id") not in (None, "") and service_id is None:
        return jsonify({"error": "Invalid service_id"}), 400
    if service_id is not None and service_id <= 0:
        return jsonify({"error": "Invalid service_id"}), 400
    if len(notes) > 5000:
        return jsonify({"error": "Notes are too long"}), 400
    if (customer_latitude is None) != (customer_longitude is None):
        return jsonify({"error": "Customer location coordinates must be provided together"}), 400
    if customer_latitude is not None and not (-90 <= customer_latitude <= 90 and -180 <= customer_longitude <= 180):
        return jsonify({"error": "Invalid customer location coordinates"}), 400
    try:
        scheduled_at = datetime.fromisoformat(scheduled_at_value) if scheduled_at_value else None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid scheduled_at"}), 400

    provider = Provider.query.filter_by(profile_code=profile_code).first()
    if not provider or not provider.is_active:
        return jsonify({"error": "Provider not found"}), 404
    if provider.availability == "busy":
        return jsonify({"error": "This provider is currently busy and cannot accept new bookings."}), 409
    if provider.availability == "offline":
        return jsonify({"error": "This provider is currently offline and cannot accept new bookings."}), 409

    service = Service.query.filter_by(slug=service_slug).first() if service_slug else Service.query.get(service_id)
    if not service or not service.is_active:
        return jsonify({"error": "Service not found"}), 404

    offered = ProviderService.query.filter_by(
        provider_id=provider.id, service_id=service.id, is_active=True
    ).first()
    if not offered:
        return jsonify({"error": "Provider does not offer this service"}), 400
    if scheduled_at:
        existing = Booking.query.filter(
            Booking.customer_id == user["id"],
            Booking.provider_id == provider.id,
            Booking.service_id == service.id,
            Booking.status.in_(("pending", "confirmed")),
            Booking.scheduled_at == scheduled_at,
        ).first()

        if existing:
            return jsonify({
                "error": "You already have an active booking for this provider and service at this time."
            }), 409

    booking = Booking(
        customer_id=user["id"],
        provider_id=provider.id,
        service_id=service.id,
        notes=notes,
        scheduled_at=scheduled_at,
        status="pending",
        customer_latitude=customer_latitude,
        customer_longitude=customer_longitude,
        customer_location_label=customer_location_label[:160] if customer_location_label else None,
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify(booking.to_customer_dto(provider, service)), 201


@customer_bp.route("/bookings/<booking_reference>/cancel", methods=["POST"])
@customer_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required(role="customer")
@_customer_booking_access
@csrf_protect
def cancel_booking(booking_reference=None, booking_id=None):
    user = session["user"]
    if booking_id is not None:
        booking = Booking.query.filter_by(id=booking_id, customer_id=user["id"]).first()
    else:
        booking = next((booking for booking in Booking.query.filter_by(customer_id=user["id"]).all()
                        if booking.public_reference == booking_reference), None)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if booking.status not in ("pending", "confirmed"):
        return jsonify({"error": "This booking cannot be cancelled."}), 400

    booking.status = "cancelled"
    db.session.commit()
    return jsonify({"message": "Booking cancelled.", "status": booking.status})


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


@customer_bp.route("/bookings/<booking_reference>/review", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def review_booking(booking_reference):
    user = session["user"]
    booking = next((b for b in Booking.query.filter_by(customer_id=user["id"]).all()
                    if b.public_reference == booking_reference), None)
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if booking.status != "completed":
        return jsonify({"error": "Only completed bookings can be rated."}), 400
    rating = request.form.get("rating", type=int)
    comment = request.form.get("comment", "").strip()
    if rating not in range(1, 6):
        return jsonify({"error": "Rating must be between 1 and 5."}), 400
    if len(comment) > 2000:
        return jsonify({"error": "Review text is too long."}), 400
    if Review.query.filter_by(booking_id=booking.id, reviewer_id=user["id"]).first():
        return jsonify({"error": "You have already rated this booking."}), 409
    review = Review(provider_id=booking.provider_id, customer_id=booking.customer_id,
                    booking_id=booking.id, reviewer_id=user["id"], reviewer_role="customer",
                    rating=rating, comment=comment or None)
    provider = Provider.query.get(booking.provider_id)
    customer_reviews = Review.query.filter_by(provider_id=provider.id, reviewer_role="customer").all()
    provider.reviews_count = len(customer_reviews) + 1
    provider.rating = (sum(r.rating for r in customer_reviews) + rating) / provider.reviews_count
    db.session.add(review)
    db.session.commit()
    return jsonify({"message": "Review submitted."}), 201
