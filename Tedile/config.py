import os
import secrets

from cryptography.fernet import Fernet

# Generated once per process if SECRET_KEY is not set via environment.
# Never hardcode a real secret key in source control.
_FALLBACK_SECRET_KEY = secrets.token_hex(32)

# Generated once per process if ENCRYPTION_KEY is not set via environment.
# Dev-only: data encrypted with an ephemeral key becomes unreadable after restart.
_FALLBACK_ENCRYPTION_KEY = Fernet.generate_key().decode()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", _FALLBACK_SECRET_KEY)
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    TESTING = False
    JSON_SORT_KEYS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    SECURE_PROXY_SSL_HEADER = ("X-Forwarded-Proto", "https")

    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///tedile.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "tedile-app")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

    # Fernet key used to encrypt PII columns (phone/whatsapp) at rest.
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", _FALLBACK_ENCRYPTION_KEY)

    # Default search radius (km) used when a client omits it.
    DEFAULT_SEARCH_RADIUS_KM = int(os.getenv("DEFAULT_SEARCH_RADIUS_KM", "50"))


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"

    def __init__(self):
        if os.getenv("SECRET_KEY") is None:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production."
            )
        if os.getenv("ENCRYPTION_KEY") is None:
            raise RuntimeError(
                "ENCRYPTION_KEY environment variable must be set in production "
                "(a rotating/ephemeral key would make encrypted PII unreadable)."
            )
        if os.getenv("DATABASE_URL") is None:
            raise RuntimeError(
                "DATABASE_URL environment variable must be set in production."
            )
        if self.SQLALCHEMY_DATABASE_URI.startswith("sqlite:///"):
            raise RuntimeError(
                "SQLite is not allowed for UAT or production; use PostgreSQL."
            )


class UATConfig(ProductionConfig):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
