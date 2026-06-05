"""Service layer. Re-exported so callers can use ``services.<fn>`` directly."""

from app.services.deployment_service import get, list_deployments

__all__ = ["get", "list_deployments"]
