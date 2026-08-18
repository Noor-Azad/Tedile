from flask import Blueprint, jsonify, render_template, request, session

from app.extensions import db
from app.models.provider import Provider
from app.routes.customer import login_required
from app.security import csrf_protect

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required(role="admin")
def admin_dashboard():
    user = session["user"]
    providers = Provider.query.order_by(Provider.created_at.desc()).all()
    return render_template("dashboard.html", user=user, providers=[p.to_admin_dto() for p in providers])


@admin_bp.route("/providers/<int:provider_id>/verify", methods=["POST"])
@login_required(role="admin")
@csrf_protect
def verify_provider(provider_id):
    provider = Provider.query.get(provider_id)
    if not provider:
        return jsonify({"error": "Provider not found"}), 404

    provider.verified = bool(request.form.get("verified", "true").lower() == "true")
    db.session.commit()
    return jsonify(provider.to_admin_dto())
