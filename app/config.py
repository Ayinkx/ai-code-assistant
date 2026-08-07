"""Application configuration.

Configuration is loaded from environment variables so the same codebase can
run locally, in CI, and in production without modification. Sensitive values
such as the database password and secret key must never be committed to the
repository; supply them through environment variables or a local ``.env``
file (see ``.env.example``).
"""

import os
from pathlib import Path
from typing import ClassVar

from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from a .env file if one exists. This is a
# convenience for local development only; production deployments should
# provide variables via the container/platform environment.
load_dotenv(BASE_DIR / ".env")


def _db_uri() -> str:
    """Return the SQLAlchemy database URI for the current environment.

    Defaults to a local SQLite file so the application is runnable with zero
    configuration for development, while still being PostgreSQL-first in
    production (see ``docker-compose.yml``).

    For file-backed SQLite databases the parent directory is created
    automatically (SQLAlchemy does not create parent folders itself).
    """
    uri = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'app.db'}",
    )
    if uri.startswith("sqlite:///") and "sqlite:///:memory:" not in uri:
        db_file = Path(uri.replace("sqlite:///", "", 1))
        db_file.parent.mkdir(parents=True, exist_ok=True)
    return uri


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = _db_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session lifetime in seconds (12 hours).
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME", 60 * 60 * 12))

    # App branding / feature toggles.
    APP_NAME = os.getenv("APP_NAME", "AI Code Assistant")
    SESSION_COOKIE_SECURE = False

    # Maximum size of an uploaded file in bytes (configured for future phases).
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))


class DevelopmentConfig(Config):
    """Local development configuration."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(Config):
    """Configuration used by the automated test suite.

    Uses an in-memory SQLite database and disables CSRF so that test clients
    do not need to fetch and submit a token for every request.
    """

    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    # Keep a single in-memory SQLite connection alive across the test run.
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict] = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }


class ProductionConfig(Config):
    """Production configuration.

    Requires explicit configuration of the secret key and database URL. Fails
    fast on startup if required settings are missing rather than silently
    running with insecure defaults.
    """

    DEBUG = False

    def __init__(self) -> None:
        if not os.getenv("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY must be set in the production environment.")
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL must be set in the production environment.")
        if not os.getenv("DATABASE_URL", "").startswith("postgresql"):
            raise RuntimeError(
                "Production must use PostgreSQL (DATABASE_URL starting with " "postgresql://)."
            )

    # Secure session cookie over HTTPS.
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


# Registry used by the application factory via ``create_app(config_name)``.
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
