import os

from flask import Flask

from app.extensions import db
from config import Config, DevelopmentConfig, ProductionConfig


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    app_env = (os.getenv("APP_ENV") or "development").lower()
    config_obj = ProductionConfig if app_env == "production" else DevelopmentConfig

    app.config.from_object(config_obj)
    app.config.from_prefixed_env()
    app.secret_key = app.config["SECRET_KEY"]

    db.init_app(app)

    try:
        from app.models.document import DocumentUpload  # noqa: F401
    except Exception:
        DocumentUpload = None

    with app.app_context():
        if app.config.get("DATABASE_URL") and hasattr(db, "create_all"):
            db.create_all()

    from app.routes.auth import auth_bp
    from app.routes.parent import parent_bp
    from app.routes.admin import admin_bp
    from app.routes.teacher import teacher_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)

    @app.route("/health")
    def health_check():
        try:
            db.session.execute("SELECT 1")
            status = "healthy"
            code = 200
        except Exception:
            status = "degraded"
            code = 503

        return {"status": status, "app": "BengalLearningCenter"}, code

    return app
