import os
import secrets

# Generated once per process if SECRET_KEY is not set via environment.
# Never hardcode a real secret key in source control.
_FALLBACK_SECRET_KEY = secrets.token_hex(32)


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

    SQLALCHEMY_DATABASE_URI = DATABASE_URL or "sqlite:///bengal_learning_center.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "bengal-learning-center")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")


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
