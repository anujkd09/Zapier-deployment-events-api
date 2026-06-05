"""FastAPI application entrypoint for the Deployment Events API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__, models  # noqa: F401  (import models so tables register)
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.data.base import Base
from app.data.session import engine
from app.api.router import api_router

# Structured JSON logs from the very start.
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup so the service is runnable out of the box.

    Done here (not at import time) so importing the app has no database side
    effects — important for tests, which swap in their own engine. A production
    service would manage schema changes with a migration tool (e.g. Alembic).
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Deployment Events API",
    version=__version__,
    description=(
        "Backend service for ingesting and serving deployment event history."
    ),
    lifespan=lifespan,
)

# Cross-cutting concerns.
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

app.include_router(api_router)


@app.get("/health", tags=["meta"], summary="Liveness check")
def health() -> dict[str, str]:
    """Liveness probe for load balancers / orchestrators."""
    return {"status": "ok", "version": __version__}
