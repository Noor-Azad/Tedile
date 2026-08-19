from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.extensions import limiter
from app.services.auth_service import authenticate_user, register_user
from app.security import csrf_protect

auth_bp = Blueprint("auth", __name__)


def _login_email_key():
    email = (request.form.get("email", "") or "").strip().lower()
    return f"{request.remote_addr or 'unknown'}:{email}"


def _redirect_for_role(role: str):
    if role == "admin":
        return redirect(url_for("admin.admin_dashboard"))
    if role == "provider":
        return redirect(url_for("provider.provider_dashboard"))
    return redirect(url_for("customer.dashboard"))


@auth_bp.route("/")
def login_page():
    user = session.get("user")
    if not user:
        return render_template("index.html")
    return _redirect_for_role(user.get("role"))


@auth_bp.route("/login", methods=["GET", "POST"])
@csrf_protect
@limiter.limit("10 per minute", methods=["POST"])
@limiter.limit("5 per minute", methods=["POST"], key_func=_login_email_key)
def login():
    if request.method == "GET":
        return render_template("index.html")

    email = request.form.get("email", "")
    password = request.form.get("password", "")

    user = authenticate_user(email, password)
    if not user:
        return render_template("index.html", error="Invalid email or password."), 401

    session["user"] = user.to_session_dict()
    return _redirect_for_role(user.role)


@auth_bp.route("/signup", methods=["POST"])
@csrf_protect
def signup():
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    name = request.form.get("name", "")
    role = request.form.get("role", "customer")
    phone = request.form.get("phone", "")

    if role not in ("customer", "provider"):
        role = "customer"

    try:
        user = register_user(email, password, name, role=role, phone=phone)
    except ValueError as exc:
        return render_template("index.html", error=str(exc)), 400

    session["user"] = user.to_session_dict()
    return _redirect_for_role(user.role)


@auth_bp.route("/api/session")
def session_info():
    user = session.get("user")
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": user})


@auth_bp.route("/providers/<profile_code>")
def provider_profile_page(profile_code):
    return render_template("provider_profile.html", profile_code=profile_code)


@auth_bp.route("/logout", methods=["POST"])
@csrf_protect
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
