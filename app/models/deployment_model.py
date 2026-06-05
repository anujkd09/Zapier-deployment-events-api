"""SQLAlchemy ORM model for deployments.

The shape mirrors the deployment event contract used by the API:

    {
      "id": "deploy_123",
      "service": "billing-api",
      "status": "failed",
      "duration": 320,          # seconds
      "timestamp": "2025-04-28T14:32:00Z",
      "commit_sha": "abc123"
    }
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.data.base import Base


class DeploymentStatus(str, enum.Enum):
    """Lifecycle outcome of a deployment."""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    ROLLED_BACK = "rolled_back"


def _new_id() -> str:
    """Human-readable, prefixed id (e.g. ``deploy_a1b2c3d4e5f6``)."""
    return f"deploy_{uuid.uuid4().hex[:12]}"


class Deployment(Base):
    """A single deployment of a service, identified by commit."""

    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_id)
    service: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[DeploymentStatus] = mapped_column(
        Enum(DeploymentStatus, native_enum=False, length=20),
        nullable=False,
        index=True,
    )
    # Wall-clock duration of the deployment, in seconds.
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    # When the deployment occurred (timezone-aware UTC).
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Composite index for the common "filter by service (+ status)" access pattern.
    __table_args__ = (Index("ix_service_status", "service", "status"),)
