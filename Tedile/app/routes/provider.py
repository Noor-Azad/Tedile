from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.service import Service
from app.models.user import User
from app.routes.customer import login_required
from app.security import csrf_protect

provider_bp = Blueprint("provider", __name__, url_prefix="/provider")


@provider_bp.route("/dashboard")
@login_required(role="provider")
def provider_dashboard():
    user = session["user"]
    provider = Provider.query.filter_by(user_id=user["id"]).first()
    bookings = []
    if provider:
        bookings = (
            Booking.query.filter_by(provider_id=provider.id)
            .order_by(Booking.created_at.desc())
            .all()
        )
    booking_dtos = []
    for booking in bookings:
        service = Service.query.get(booking.service_id)
        customer = User.query.get(booking.customer_id)
        if service and customer:
            booking_dtos.append(booking.to_provider_dto(service, customer))
    return render_template(
        "dashboard.html",
        user=user,
        provider=provider.to_provider_owner_dto() if provider else None,
        bookings=booking_dtos,
    )


@provider_bp.route("/availability", methods=["POST"])
@login_required(role="provider")
@csrf_protect
def update_availability():
    user = session["user"]
    provider = Provider.query.filter_by(user_id=user["id"]).first()
    if not provider:
        return jsonify({"error": "Provider profile not found"}), 404

    availability = request.form.get("availability", "available")
    if availability not in ("available", "busy", "offline"):
        return jsonify({"error": "Invalid availability value"}), 400

    provider.availability = availability
    db.session.commit()
    return jsonify(provider.to_provider_owner_dto())


@provider_bp.route("/bookings/<booking_reference>/status", methods=["POST"])
@login_required(role="provider")
@csrf_protect
def update_booking_status(booking_reference):
    user = session["user"]
    provider = Provider.query.filter_by(user_id=user["id"]).first()
    booking = next(
        (
            candidate
            for candidate in Booking.query.filter_by(provider_id=provider.id).all()
            if candidate.public_reference == booking_reference
        ),
        None,
    ) if provider else None

    if not provider or not booking or booking.provider_id != provider.id:
        return redirect(url_for("provider.provider_dashboard"))

    status = request.form.get("status")
    if status not in ("confirmed", "completed", "cancelled"):
        return redirect(url_for("provider.provider_dashboard"))

    booking.status = status
    db.session.commit()
    return redirect(url_for("provider.provider_dashboard"))
