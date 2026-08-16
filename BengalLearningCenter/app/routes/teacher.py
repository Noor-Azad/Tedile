from flask import Blueprint, render_template, session

teacher_bp = Blueprint("teacher", __name__)


@teacher_bp.route("/teacher")
def teacher_dashboard():
    user = session.get("user")
    if not user:
        return render_template("index.html", error="Please log in first.")
    return render_template("dashboard.html", user=user, role="Teacher", data={})
