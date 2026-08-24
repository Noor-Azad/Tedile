from decimal import Decimal, InvalidOperation
import re

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.extensions import db
from app.models.provider import Provider
from app.models.rider import Rider
from app.models.bike_ride import BikeRide
from app.models.user import User
from app.models.fare_configuration import FareConfiguration
from app.routes.customer import login_required
from app.security import csrf_protect

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required(role="admin")
def admin_dashboard():
    user = session["user"]
    providers = Provider.query.order_by(Provider.created_at.desc()).all()
    return render_template("dashboard.html", user=user, providers=[p.to_admin_dto() for p in providers])


@admin_bp.route("/pricing", methods=["GET", "POST"])
@login_required(role="admin")
@csrf_protect
def pricing():
    configuration = FareConfiguration.current()
    if not configuration:
        configuration = FareConfiguration.ensure_default()
        db.session.commit()

    if request.method == "POST":
        try:
            base_fare = Decimal((request.form.get("base_fare") or "").strip()).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return render_template("admin_pricing.html", user=session["user"], configuration=configuration, error="Enter a valid fare amount."), 400
        currency = (request.form.get("currency") or "").strip().upper()
        if not base_fare.is_finite() or base_fare <= 0 or base_fare > Decimal("99999999.99"):
            return render_template("admin_pricing.html", user=session["user"], configuration=configuration, error="Enter a valid positive fare amount."), 400
        if not re.fullmatch(r"[A-Z]{3}", currency):
            return render_template("admin_pricing.html", user=session["user"], configuration=configuration, error="Currency must be a three-letter code."), 400

        new_configuration = FareConfiguration(base_fare=base_fare, currency=currency, pricing_version="pending")
        db.session.add(new_configuration)
        db.session.flush()
        new_configuration.pricing_version = f"v{new_configuration.id}"
        db.session.commit()
        return redirect(url_for("admin.pricing"))

    return render_template("admin_pricing.html", user=session["user"], configuration=configuration)


@admin_bp.route("/providers/<int:provider_id>/verify", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def verify_provider(provider_id):
    provider = Provider.query.get(provider_id)
    if not provider:
        return jsonify({"error": "Provider not found"}), 404

    provider.verified = bool(request.form.get("verified", "true").lower() == "true")
    db.session.commit()
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/riders")
@login_required(role="admin")
def riders():
    applications = []
    for rider in Rider.query.order_by(Rider.created_at.desc()).all():
        user = User.query.get(rider.user_id)
        if user:
            applications.append(rider.to_admin_dto(user))
    return render_template("rider_admin.html", user=session["user"], applications=applications)


def _update_rider_status(rider_id, status):
    rider = Rider.query.get(rider_id)
    if not rider:
        return jsonify({"error": "Rider application not found"}), 404
    rider.status = status
    db.session.commit()
    return redirect(url_for("admin.riders"))


@admin_bp.route("/riders/<int:rider_id>/approve", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def approve_rider(rider_id):
    return _update_rider_status(rider_id, Rider.APPROVED)


@admin_bp.route("/riders/<int:rider_id>/reject", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def reject_rider(rider_id):
    return _update_rider_status(rider_id, Rider.REJECTED)


@admin_bp.route("/rides")
@login_required(role="admin")
def rides():
    ride_rows = []
    for ride in BikeRide.query.order_by(BikeRide.created_at.desc()).all():
        customer = User.query.get(ride.customer_id)
        rider = Rider.query.get(ride.rider_id) if ride.rider_id else None
        rider_user = User.query.get(rider.user_id) if rider else None
        ride_rows.append({"ride": ride, "customer": customer, "rider": rider_user})
    return render_template("ride_admin.html", user=session["user"], rides=ride_rows)
