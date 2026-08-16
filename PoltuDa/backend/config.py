"""
Flask Configuration
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

INSTANCE_DIR = os.path.join(os.path.dirname(__file__), 'instance')
os.makedirs(INSTANCE_DIR, exist_ok=True)


def _default_secret(name, fallback):
    value = os.getenv(name)
    if value:
        return value
    if os.getenv('FLASK_ENV') == 'production':
        raise RuntimeError(f"Missing required environment variable: {name}")
    return fallback


class Config:
    """Base configuration"""

    # Flask
    SECRET_KEY = _default_secret('SECRET_KEY', 'dev-secret-key-change-in-production-please-use-32bytes')
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    PREFERRED_URL_SCHEME = 'https' if os.getenv('FLASK_ENV') == 'production' else 'http'

    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(INSTANCE_DIR, 'poltuda.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # JWT
    JWT_SECRET_KEY = _default_secret('JWT_SECRET_KEY', 'jwt-secret-key-dev-please-use-32bytes-for-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
    JWT_TOKEN_LOCATION = ['headers']

    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')

    # File Upload
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100

    # Location
    DEFAULT_SEARCH_RADIUS = 10
    MAX_SEARCH_RADIUS = 50


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    JWT_COOKIE_SECURE = True


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig
    if env == 'testing':
        return TestingConfig
    return DevelopmentConfig
