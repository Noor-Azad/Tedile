import hashlib
import hmac
import secrets
import time
from functools import wraps

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from app.extensions import limiter
from app.services.auth_service import authenticate_user, register_user
from app.security import csrf_protect
from app.services.otp_service import deliver_otp

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


def _otp_key():
    challenge = session.get("otp_challenge", {})
    return f"{request.remote_addr or 'unknown'}:{challenge.get('user_id', 'none')}"


def _begin_otp(user):
    otp = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_urlsafe(16)
    digest = hmac.new(current_app.secret_key.encode(), f"{salt}:{otp}".encode(), hashlib.sha256).hexdigest()
    session.pop("user", None)
    session["otp_challenge"] = {"user_id": user.id, "digest": digest, "salt": salt, "expires_at": int(time.time()) + current_app.config["OTP_EXPIRY_SECONDS"], "attempts": 0}
    deliver_otp(user.email, otp)


def _onboarding_required(view_fn):
    @wraps(view_fn)
    def wrapped(*args, **kwargs):
        if not session.get("user") or session.get("onboarding", {}).get("stage") != "location":
            return redirect(url_for("auth.login_page"))
        return view_fn(*args, **kwargs)
    return wrapped


@auth_bp.route("/")
def login_page():
    if session.get("otp_challenge"):
        return redirect(url_for("auth.otp_page"))
    if session.get("onboarding", {}).get("stage") == "location":
        return redirect(url_for("auth.location_page"))
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

    _begin_otp(user)
    return redirect(url_for("auth.otp_page"))


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

    _begin_otp(user)
    return redirect(url_for("auth.otp_page"))


@auth_bp.route("/otp")
def otp_page():
    if not session.get("otp_challenge"):
        return redirect(url_for("auth.login_page"))
    return render_template("otp.html", error=request.args.get("error"))


@auth_bp.route("/otp/verify", methods=["POST"])
@csrf_protect
@limiter.limit("5 per minute", methods=["POST"], key_func=_otp_key)
def verify_otp():
    challenge = session.get("otp_challenge")
    if not challenge:
        return redirect(url_for("auth.login_page"))
    if time.time() > challenge.get("expires_at", 0):
        session.pop("otp_challenge", None)
        return render_template("otp.html", error="That code has expired."), 400
    code = (request.form.get("otp", "") or "").strip()
    expected = hmac.new(current_app.secret_key.encode(), f"{challenge.get('salt')}:{code}".encode(), hashlib.sha256).hexdigest()
    if challenge.get("attempts", 0) >= current_app.config["OTP_MAX_ATTEMPTS"] or not hmac.compare_digest(expected, challenge.get("digest", "")):
        challenge["attempts"] = challenge.get("attempts", 0) + 1
        session["otp_challenge"] = challenge
        return render_template("otp.html", error="Invalid verification code."), 400
    from app.models.user import User
    user = User.query.get(challenge["user_id"])
    if not user:
        session.pop("otp_challenge", None)
        return redirect(url_for("auth.login_page"))
    session.pop("otp_challenge", None)
    session["user"] = user.to_session_dict()
    session["onboarding"] = {"stage": "location"}
    return redirect(url_for("auth.location_page"))


@auth_bp.route("/otp/resend", methods=["POST"])
@csrf_protect
@limiter.limit("3 per 10 minutes", methods=["POST"], key_func=_otp_key)
def resend_otp():
    challenge = session.get("otp_challenge")
    if not challenge:
        return redirect(url_for("auth.login_page"))
    from app.models.user import User
    user = User.query.get(challenge.get("user_id"))
    if not user:
        session.pop("otp_challenge", None)
        return redirect(url_for("auth.login_page"))
    _begin_otp(user)
    return redirect(url_for("auth.otp_page"))


@auth_bp.route("/onboarding/location")
@_onboarding_required
def location_page():
    return render_template("onboarding_location.html")


@auth_bp.route("/onboarding/location", methods=["POST"])
@_onboarding_required
@csrf_protect
def save_location():
    payload = request.get_json(silent=True) or {}
    try:
        latitude, longitude = float(payload["latitude"]), float(payload["longitude"])
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Invalid location"}), 400
    session["onboarding"] = {"stage": "location", "location_status": "granted"}
    return jsonify({"next": url_for("auth.permissions_page")})


@auth_bp.route("/onboarding/location/skip", methods=["POST"])
@_onboarding_required
@csrf_protect
def skip_location():
    session["onboarding"] = {"stage": "location", "location_status": "denied"}
    return jsonify({"next": url_for("auth.permissions_page")})


@auth_bp.route("/onboarding/permissions")
@_onboarding_required
def permissions_page():
    return render_template("onboarding_permissions.html")


@auth_bp.route("/onboarding/complete", methods=["POST"])
@_onboarding_required
@csrf_protect
def complete_onboarding():
    session.pop("onboarding", None)
    return _redirect_for_role(session["user"]["role"])


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
