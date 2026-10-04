"""Configuration objects for MyDoc.

All configuration is driven by environment variables so the same code base can
run in development, testing and production without modification.
"""

import os
from datetime import timedelta

from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Paths / helpers
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))   # .../app
ROOT_DIR = os.path.dirname(BASE_DIR)                    # project root


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Base configuration
# ---------------------------------------------------------------------------
class Config:
    """Common configuration shared by every environment."""

    # --- Core ---------------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-insecure-secret-key"
    TESTING = False
    DEBUG = False

    # --- Database -----------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or "sqlite:///mydoc.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # --- Sessions & cookies -------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = _env_bool("REMEMBER_COOKIE_SECURE", False)
    REMEMBER_COOKIE_DURATION = timedelta(days=30)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # --- Security headers ---------------------------------------------------
    CONTENT_SECURITY_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'"
    )
    REFERRER_POLICY = "strict-origin-when-cross-origin"

    # --- Uploads ------------------------------------------------------------
    MAX_CONTENT_LENGTH = _env_int("MAX_UPLOAD_MB", 4) * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(ROOT_DIR, "app", "static", "uploads")
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/gif", "image/webp"}

    # --- CSRF / rate limiting ----------------------------------------------
    WTF_CSRF_TIME_LIMIT = 3600
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URL", "memory://")
    RATELIMIT_ENABLED = _env_bool("RATELIMIT_ENABLED", True)
    RATELIMIT_DEFAULT = "200 per hour"

    # --- Mailer -------------------------------------------------------------
    MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "console")
    MAIL_SUPPRESS_SEND = _env_bool("MAIL_SUPPRESS_SEND", True)
    MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@mydoc.local")
    SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
    SMTP_PORT = _env_int("SMTP_PORT", 587)
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", True)
    SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:5000")

    # --- Application --------------------------------------------------------
    SITE_NAME = "MyDoc"
    DOCS_PER_PAGE = 10
    TOKEN_MAX_AGE_SECONDS = 3600  # e-mail verification / password reset tokens
    ACCOUNT_DELETION_CONFIRM = True


class DevelopmentConfig(Config):
    """Local development."""

    DEBUG = True


class TestingConfig(Config):
    """Used by pytest — fast in-memory database, CSRF/limits disabled."""

    TESTING = True
    DEBUG = True
    SECRET_KEY = "testing-secret-key"
    # StaticPool => one shared connection, so every context/session sees the
    # same in-memory database (prevents cross-connection invisibility).
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": StaticPool,
    }
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SERVER_NAME = "localhost"
    MAIL_SUPPRESS_SEND = True
    UPLOAD_FOLDER = os.path.join(ROOT_DIR, "instance", "test_uploads")



class ProductionConfig(Config):
    """Hardened production configuration."""

    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    def __init__(self):  # pragma: no cover - guarded at boot in real deployments
        if not os.environ.get("SECRET_KEY") or self.SECRET_KEY == Config.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY must be set in the environment for production."
            )


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> type[Config]:
    """Resolve a configuration class from the ``FLASK_ENV`` variable."""
    name = (name or os.environ.get("FLASK_ENV", "development")).lower()
    return CONFIG_MAP.get(name, DevelopmentConfig)
