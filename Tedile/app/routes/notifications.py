from flask import Blueprint, jsonify, session

from app.extensions import db
from app.models.notification import Notification
from app.routes.customer import login_required
from app.security import csrf_protect

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("")
@login_required()
def index():
    user_id = session["user"]["id"]
    records = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(50).all()
    unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({"data": [record.to_dict() for record in records], "unread": unread})


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required()
@csrf_protect
def mark_read(notification_id):
    record = Notification.query.filter_by(id=notification_id, user_id=session["user"]["id"]).first()
    if not record:
        return jsonify({"error": "Notification not found"}), 404
    record.is_read = True
    db.session.commit()
    return jsonify(record.to_dict())
