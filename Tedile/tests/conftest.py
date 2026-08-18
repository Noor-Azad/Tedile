from app.extensions import db
from app import create_app
from config import DevelopmentConfig


def create_isolated_test_app():
    DevelopmentConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    app = create_app()
    configure_isolated_sqlite(app)
    return app


def configure_isolated_sqlite(app):
    """Force and verify an in-memory SQLite database before destructive setup."""
    app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        TESTING=True,
    )
    with app.app_context():
        engine_url = db.engine.url
        if engine_url.drivername != "sqlite" or engine_url.database != ":memory:":
            raise RuntimeError(
                "Tests may only create/drop an in-memory SQLite database; refusing "
                f"to touch {engine_url}."
            )
