from functools import wraps
from datetime import datetime

from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.service import Service
from app.models.provider_service import ProviderService
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
