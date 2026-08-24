from flask import Blueprint, abort, redirect, render_template, session, url_for

from app.extensions import db
from app.models.bike_ride import BikeRide
from app.models.rider import Rider
from app.models.user import User
from app.routes.customer import login_required
from app.security import csrf_protect

rider_bp = Blueprint("rider", __name__, url_prefix="/rider")


def _rider_for_session(require_approved=False):
    rider = Rider.query.filter_by(user_id=session["user"]["id"]).first()
    if not rider:
        abort(403)
    if require_approved and rider.status != Rider.APPROVED:
        abort(403)
    return rider


@rider_bp.route("/dashboard")
@login_required(role="customer")
def dashboard():
    rider = _rider_for_session()
    available = []
    if rider.status == Rider.APPROVED:
        available = BikeRide.query.filter_by(status=BikeRide.REQUESTED).order_by(BikeRide.requested_at.asc()).all()
    assigned = BikeRide.query.filter_by(rider_id=rider.id).filter(
        BikeRide.status.in_((BikeRide.ACCEPTED, BikeRide.IN_PROGRESS))
    ).order_by(BikeRide.created_at.desc()).all()
    return render_template(
        "rider_dashboard.html",
        user=session["user"],
        rider=rider,
        available_rides=available,
        assigned_rides=assigned,
    )


@rider_bp.route("/rides/history")
@login_required(role="customer")
def history():
    rider = _rider_for_session(require_approved=True)
    rides = BikeRide.query.filter(
        BikeRide.rider_id == rider.id,
        BikeRide.status.in_((BikeRide.COMPLETED, BikeRide.CANCELLED)),
    ).order_by(BikeRide.created_at.desc()).all()
    return render_template("rider_ride_history.html", user=session["user"], rides=rides)


@rider_bp.route("/rides/history/<int:ride_id>")
@login_required(role="customer")
def history_detail(ride_id):
    rider = _rider_for_session(require_approved=True)
    ride = BikeRide.query.filter(
        BikeRide.id == ride_id,
        BikeRide.rider_id == rider.id,
        BikeRide.status.in_((BikeRide.COMPLETED, BikeRide.CANCELLED)),
    ).first()
    if not ride:
        abort(404)
    return render_template("rider_ride_detail.html", user=session["user"], ride=ride)


def _owned_ride(rider_id, ride_id):
    ride = BikeRide.query.filter_by(id=ride_id, rider_id=rider_id).first()
    if not ride:
        abort(404)
    return ride


@rider_bp.route("/rides/<int:ride_id>/accept", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def accept_ride(ride_id):
    rider = _rider_for_session(require_approved=True)
    if not BikeRide.claim(ride_id, rider.id):
        db.session.rollback()
        return redirect(url_for("rider.dashboard"))
    db.session.commit()
    return redirect(url_for("rider.dashboard"))


@rider_bp.route("/rides/<int:ride_id>/start", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def start_ride(ride_id):
    rider = _rider_for_session(require_approved=True)
    ride = _owned_ride(rider.id, ride_id)
    try:
        ride.transition_to(BikeRide.IN_PROGRESS)
    except ValueError:
        return redirect(url_for("rider.dashboard"))
    db.session.commit()
    return redirect(url_for("rider.dashboard"))


@rider_bp.route("/rides/<int:ride_id>/complete", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def complete_ride(ride_id):
    rider = _rider_for_session(require_approved=True)
    ride = _owned_ride(rider.id, ride_id)
    try:
        ride.transition_to(BikeRide.COMPLETED)
    except ValueError:
        return redirect(url_for("rider.dashboard"))
    db.session.commit()
    return redirect(url_for("rider.dashboard"))


@rider_bp.route("/rides/<int:ride_id>/cancel", methods=["POST"])
@login_required(role="customer")
@csrf_protect
def cancel_ride(ride_id):
    rider = _rider_for_session(require_approved=True)
    ride = _owned_ride(rider.id, ride_id)
    if ride.status != BikeRide.ACCEPTED:
        return redirect(url_for("rider.dashboard"))
    ride.transition_to(BikeRide.CANCELLED)
    db.session.commit()
    return redirect(url_for("rider.dashboard"))
