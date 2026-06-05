"""Pydantic response schemas for deployments.

Schemas are the API's trust boundary and define the exact response shape, so the
serialized output is stable and documented in OpenAPI.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_serializer

from app.models.deployment_model import DeploymentStatus


class DeploymentOut(BaseModel):
    """A single deployment as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    service: str
    status: DeploymentStatus
    duration: int  # seconds
    timestamp: datetime
    commit_sha: str | None = None

    @field_serializer("timestamp", when_used="json")
    def _serialize_timestamp(self, value: datetime) -> str:
        """Emit ISO-8601 UTC with a trailing ``Z`` in JSON responses.

        SQLite does not persist timezone info, so values read back are naive even
        though we store UTC. Treat naive as UTC and normalize so the response is
        consistent regardless of backend.

        Scoped to ``when_used="json"`` so Python-mode dumps (``model_dump()``)
        keep the native ``datetime`` declared by the field, while JSON output —
        which the ``date-time`` schema describes — is the normalized string.
        """
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
