import os

from flask import Flask, jsonify, redirect, request, session
from sqlalchemy import text

from app.extensions import db, limiter, migrate
from app.security import get_csrf_token
from config import DevelopmentConfig, ProductionConfig, UATConfig


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app_env = (os.getenv("APP_ENV") or "development").lower()
    config_classes = {
        "development": DevelopmentConfig,
        "testing": DevelopmentConfig,
        "uat": UATConfig,
        "production": ProductionConfig,
    }
    try:
        config_obj = config_classes[app_env]()
    except KeyError as exc:
        raise RuntimeError(
            f"Unsupported APP_ENV: {app_env}. Use development, uat, or production."
        ) from exc

    app.config.from_object(config_obj)
    app.config.from_prefixed_env()
    app.secret_key = app.config["SECRET_KEY"]
    app.context_processor(lambda: {"csrf_token": get_csrf_token})

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    from app.models.user import User  # noqa: F401
    from app.models.provider import Provider  # noqa: F401
    from app.models.service import Service  # noqa: F401
    from app.models.provider_service import ProviderService  # noqa: F401
    from app.models.location import Location  # noqa: F401
    from app.models.booking import Booking  # noqa: F401
    from app.models.review import Review  # noqa: F401

    # Schema is managed exclusively via Alembic migrations (see migrations/), not db.create_all().

    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.provider import provider_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )

        sensitive_paths = (
            "/customer/dashboard",
            "/customer/bookings",
            "/customer/providers",
            "/provider/dashboard",
            "/provider/availability",
            "/provider/bookings",
            "/admin/dashboard",
            "/admin/providers",
            "/api/session",
            "/api/admin",
            "/login",
            "/signup",
        )
        if session.get("user") and any(
            request.path == path or request.path.startswith(f"{path}/")
            for path in sensitive_paths
        ):
            response.headers["Cache-Control"] = "no-store"
        elif session.get("user") and request.method in {"POST", "PATCH", "PUT", "DELETE"} and (
            request.path == "/api/providers" or request.path.startswith("/api/providers/")
        ):
            response.headers["Cache-Control"] = "no-store"

        return response

    @app.before_request
    def enforce_https():
        # Skip in dev/debug and for the health check probe.
        if app.config.get("DEBUG") or request.path == "/health":
            return None
        if request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https":
            return None

        trusted_hosts = {"localhost", "127.0.0.1"}
        render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
        if render_hostname:
            trusted_hosts.add(render_hostname.lower())
        configured_hosts = app.config.get("TRUSTED_HOSTS") or ()
        trusted_hosts.update(str(host).lower() for host in configured_hosts)

        request_host = request.host.lower().split(":", 1)[0]
        if request_host not in trusted_hosts:
            return jsonify({"error": "Untrusted host"}), 400

        location = f"https://{request.host}{request.full_path}"
        return redirect(location, code=301)

    @app.route("/health")
    def health_check():
        try:
            db.session.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "app": "Tedile",
            }, 200

        except Exception:
            app.logger.exception("Database health check failed")
            db.session.rollback()

            return {
                "status": "degraded",
                "app": "Tedile",
                "error": "Database unavailable",
            }, 503

    return app
