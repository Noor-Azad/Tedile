from flask import Blueprint, redirect, render_template, request, session, url_for

from app.services.auth_service import authenticate_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def login_page():
    user = session.get("user")
    if not user:
        return render_template("index.html")

    if user.get("role") == "Admin":
        return redirect(url_for("admin.admin_dashboard"))
    if user.get("role") == "Teacher":
        return redirect(url_for("teacher.teacher_dashboard"))
    return redirect(url_for("parent.dashboard"))


@auth_bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")

    user = authenticate_user(email, password, role)
    if not user:
        return render_template("index.html", error="Invalid email, password, or selected role.")

    session["user"] = {
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "phone": user.phone,
    }

    if user.role == "Admin":
        return redirect(url_for("admin.admin_dashboard"))
    if user.role == "Teacher":
        return redirect(url_for("teacher.teacher_dashboard"))
    return redirect(url_for("parent.dashboard"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
