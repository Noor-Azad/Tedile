import os

from flask import Flask, redirect, request
from sqlalchemy import text

from app.extensions import db, migrate
from app.security import get_csrf_token
from config import Config, DevelopmentConfig, ProductionConfig


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app_env = (os.getenv("APP_ENV") or "development").lower()
    config_obj = ProductionConfig() if app_env == "production" else DevelopmentConfig()

    app.config.from_object(config_obj)
    app.config.from_prefixed_env()
    app.secret_key = app.config["SECRET_KEY"]
    app.context_processor(lambda: {"csrf_token": get_csrf_token})

    db.init_app(app)
    migrate.init_app(app, db)

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

    @app.before_request
    def enforce_https():
        # Skip in dev/debug and for the health check probe.
        if app.config.get("DEBUG") or request.path == "/health":
            return None
        if request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https":
            return None
        return redirect(request.url.replace("http://", "https://", 1), code=301)

    @app.route("/health")
    def health_check():
        try:
            db.session.execute(text("SELECT 1"))
            return {
                "status": "healthy",
                "app": "Tedile",
            }, 200

        except Exception as e:
            app.logger.exception("Database health check failed")
            db.session.rollback()

            return {
                "status": "degraded",
                "app": "Tedile",
                "error": str(e),
            }, 503

    return app
