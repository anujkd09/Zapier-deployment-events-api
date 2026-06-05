"""Deployment repository: pure data access.

This layer knows *how to talk to the database* and nothing else. All queries go
through SQLAlchemy's expression API, which binds parameters and prevents SQL
injection. It returns ORM rows and leaves interpretation to the service layer.
Swapping storage (e.g. Postgres, a cache) means rewriting only this file.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


def get(db: Session, deployment_id: str) -> models.Deployment | None:
    """Fetch a single deployment by id, or None if it doesn't exist."""
    return db.get(models.Deployment, deployment_id)


def list_deployments(
    db: Session,
    *,
    service: str | None = None,
    status: models.DeploymentStatus | None = None,
) -> list[models.Deployment]:
    """Return a filtered list of deployments.

    Filters are optional and combine with AND. Results are ordered newest-first,
    with ``id`` as a stable tie-breaker for deterministic ordering.
    """
    filters = []
    if service is not None:
        filters.append(models.Deployment.service == service)
    if status is not None:
        filters.append(models.Deployment.status == status)

    stmt = (
        select(models.Deployment)
        .where(*filters)
        .order_by(models.Deployment.timestamp.desc(), models.Deployment.id)
    )
    return list(db.scalars(stmt).all())
