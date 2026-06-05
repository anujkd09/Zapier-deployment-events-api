"""Shared pytest fixtures.

Each test gets an isolated, in-memory SQLite database via a dependency override,
so tests never touch the real ``deployments.db`` file and never bleed state into
each other.
"""

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.data.base import Base
from app.data.session import get_db
from app.main import app
from app.models.deployment_model import Deployment


@pytest.fixture()
def session_factory() -> Generator[sessionmaker, None, None]:
    """Create an isolated in-memory DB and wire it into the app via get_db."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture()
def client(session_factory: sessionmaker) -> Generator[TestClient, None, None]:
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
