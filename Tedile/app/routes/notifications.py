from flask import Blueprint, abort, redirect, render_template, session, url_for

from app.extensions import db
from app.models.notification import Notification
from app.routes.customer import login_required
from app.security import csrf_protect


notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("")
@login_required()
def list_notifications():
    notifications = Notification.query.filter_by(user_id=session["user"]["id"]).order_by(
        Notification.created_at.desc(), Notification.id.desc()
    ).all()
    return render_template(
        "notifications.html",
        user=session["user"],
        notifications=notifications,
    )


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required()
@csrf_protect
def mark_notification_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=session["user"]["id"],
    ).first()
    if not notification:
        abort(404)
    notification.mark_read()
    db.session.commit()
    return redirect(url_for("notifications.list_notifications"))
