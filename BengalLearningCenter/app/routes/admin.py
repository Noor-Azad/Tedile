from flask import Blueprint, render_template, session

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
def admin_dashboard():
    user = session.get("user")
    if not user:
        return render_template("index.html", error="Please log in first.")
    return render_template("dashboard.html", user=user, role="Admin", data={})
