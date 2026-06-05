"""Service layer for deployments: business rules and orchestration.

The service sits between the routes and the repository. Today it mostly
delegates to the repository because there are no business rules yet, but this is
the seam where logic belongs as the API grows (e.g. computing failure rates,
flagging anomalies, enriching results). Keeping it separate means the routes
stay thin and the data access stays swappable.
"""

from sqlalchemy.orm import Session

from app import models, repositories


def get(db: Session, deployment_id: str) -> models.Deployment | None:
    """Return a single deployment by id, or None if it doesn't exist."""
    return repositories.get(db, deployment_id)


def list_deployments(
    db: Session,
    *,
    service: str | None = None,
    status: models.DeploymentStatus | None = None,
) -> list[models.Deployment]:
    """Return a filtered list of deployments."""
    return repositories.list_deployments(
        db,
        service=service,
        status=status,
    )
