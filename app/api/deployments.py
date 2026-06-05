"""Deployment routes: list with filters, and fetch by id."""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app import models, schemas, services
from app.core.errors import ErrorResponse, NotFoundError
from app.data.session import get_db

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.get(
    "",
    response_model=list[schemas.DeploymentOut],
    summary="List deployments (filter by service and/or status)",
)
def list_deployments(
    response: Response,
    db: Session = Depends(get_db),
    service: str | None = Query(default=None, max_length=100, description="Exact service name"),
    status: models.DeploymentStatus | None = Query(
        default=None, description="Filter by deployment status"
    ),
) -> list[models.Deployment]:
    items = services.list_deployments(
        db,
        service=service,
        status=status,
    )
    # Match count travels in a header so the body stays a clean list.
    response.headers["X-Total-Count"] = str(len(items))
    return items


@router.get(
    "/{deployment_id}",
    response_model=schemas.DeploymentOut,
    responses={404: {"model": ErrorResponse, "description": "Deployment not found"}},
    summary="Get a single deployment by id",
)
def get_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
) -> models.Deployment:
    deployment = services.get(db, deployment_id)
    if deployment is None:
        raise NotFoundError("Deployment not found")
    return deployment
