from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
import math
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from urllib.parse import quote

from app.extensions import db
from app.models.booking import Booking
from app.models.provider import Provider
from app.models.service import Service
from app.models.user import User
from app.models.review import Review
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
            dto = booking.to_provider_dto(service, customer)
            review = Review.query.filter_by(booking_id=booking.id, reviewer_id=user["id"]).first()
            dto["review"] = {"rating": review.rating, "comment": review.comment} if review else None
            booking_dtos.append(dto)
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
    allowed_transitions = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"completed"},
        "cancelled": set(),
        "completed": set(),
    }
    if status not in allowed_transitions.get(booking.status, set()):
        return jsonify({
            "error": f"Invalid booking status transition: {booking.status} -> {status or 'missing status'}."
        }), 400

    booking.status = status
    db.session.commit()
    return redirect(url_for("provider.provider_dashboard"))


@provider_bp.route("/bookings/<booking_reference>/review", methods=["POST"])
@login_required(role="provider")
@csrf_protect
def review_booking(booking_reference):
    user = session["user"]
    provider = Provider.query.filter_by(user_id=user["id"]).first()
    booking = next((b for b in Booking.query.filter_by(provider_id=provider.id).all()
                    if b.public_reference == booking_reference), None) if provider else None
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
    db.session.add(Review(provider_id=booking.provider_id, customer_id=booking.customer_id,
                           booking_id=booking.id, reviewer_id=user["id"], reviewer_role="provider",
                           rating=rating, comment=comment or None))
    db.session.commit()
    return jsonify({"message": "Review submitted."}), 201


@provider_bp.route("/bookings/<booking_reference>/directions", methods=["GET", "POST"])
@login_required(role="provider")
@csrf_protect
def customer_directions(booking_reference):
    user = session["user"]
    provider = Provider.query.filter_by(user_id=user["id"]).first()
    booking = next((b for b in Booking.query.filter_by(provider_id=provider.id).all()
                    if b.public_reference == booking_reference), None) if provider else None
    if not booking:
        return jsonify({"error": "Booking not found"}), 404
    if request.method == "GET":
        return render_template("provider_directions.html", booking_reference=booking_reference)
    if booking.customer_latitude is None or booking.customer_longitude is None:
        return jsonify({"error": "The customer's booking location is unavailable."}), 404
    origin_lat = request.form.get("latitude", type=float)
    origin_lon = request.form.get("longitude", type=float)
    if origin_lat is None or origin_lon is None:
        origin_lat, origin_lon = provider.latitude, provider.longitude
    if origin_lat is None or origin_lon is None or not all(math.isfinite(v) for v in (origin_lat, origin_lon)) or not (-90 <= origin_lat <= 90 and -180 <= origin_lon <= 180):
        return jsonify({"error": "Your current location could not be obtained."}), 400
    response = {
        "provider": {"latitude": origin_lat, "longitude": origin_lon},
        "customer": {"latitude": booking.customer_latitude, "longitude": booking.customer_longitude, "label": booking.customer_location_label},
    }
    route_base = current_app.config["ROUTING_SERVICE_URL"].rstrip("/")
    route_url = route_base + "/route/v1/driving/" + quote(
        f"{origin_lon},{origin_lat};{booking.customer_longitude},{booking.customer_latitude}", safe=",;.-"
    ) + "?overview=full&geometries=geojson&steps=true"
    try:
        with urlopen(route_url, timeout=8) as route_response:
            route_payload = json.load(route_response)
        route = (route_payload.get("routes") or [None])[0]
        if route_payload.get("code") != "Ok" or not route:
            raise ValueError("No route")
        steps = [step for leg in route.get("legs", []) for step in leg.get("steps", [])]
        geometry_coordinates = (route.get("geometry") or {}).get("coordinates", [])
        response["route"] = {
            "distance_meters": route.get("distance"),
            "duration_seconds": route.get("duration"),
            "geometry": route.get("geometry"),
            "steps": steps,
        }
    except HTTPError:
        response["route"] = {"available": False}
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError, KeyError):
        response["route"] = {"available": False}
    return jsonify(response)
