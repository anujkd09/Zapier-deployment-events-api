"""Application configuration.

Settings are read from environment variables so the database location and other
deployment-specific values are never hardcoded into source. Sensible defaults are
provided so the app runs out of the box for local development and tests.
"""

import os


class Settings:
    """Runtime settings sourced from environment variables."""

    # SQLAlchemy database URL. Defaults to a local SQLite file in the project root.
    # Override with DATABASE_URL (e.g. a Postgres URL) without touching code.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./deployments.db")


settings = Settings()
