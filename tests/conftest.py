"""Shared pytest fixtures.

Each test gets an isolated, in-memory SQLite database. The app is built around
that engine via ``create_app``, so tests never touch the real ``deployments.db``
file and never bleed state into each other.
"""

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.data.base import Base
from app.main import create_app
from app.models.deployment_model import Deployment


@pytest.fixture()
def engine() -> Generator[Engine, None, None]:
    """An isolated in-memory SQLite engine, shared by the app and seeding."""
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def session_factory(engine: Engine) -> sessionmaker:
    """Session factory bound to the test engine, for seeding from tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def client(engine: Engine) -> Generator[TestClient, None, None]:
    # Build an app bound to the in-memory test engine and use TestClient as a
    # context manager so the real lifespan startup path runs against the test DB
    # (no globals to patch, no stray ``deployments.db`` on disk).
    app = create_app(engine=engine)
    with TestClient(app) as test_client:
        yield test_client


def make_deployment(**overrides) -> Deployment:
    """Build a Deployment with sensible defaults, overridable per field."""
    data = {
        "id": "deploy_001",
        "service": "billing-api",
        "status": "failed",
        "duration": 320,
        "timestamp": datetime(2025, 4, 28, 14, 32, tzinfo=timezone.utc),
        "commit_sha": "abc1234",
    }
    data.update(overrides)
    return Deployment(**data)


def seed(session_factory: sessionmaker, deployments: list[Deployment]) -> None:
    """Insert deployments into the test database."""
    db = session_factory()
    try:
        db.add_all(deployments)
        db.commit()
    finally:
        db.close()
