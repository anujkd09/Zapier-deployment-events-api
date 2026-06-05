"""FastAPI application entrypoint for the Deployment Events API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app import __version__, models  # noqa: F401  (import models so tables register)
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.data.base import Base
from app.data import session as db_session
from app.api.router import api_router

# Structured JSON logs from the very start.
configure_logging()


def create_app(engine: Engine | None = None) -> FastAPI:
    """Build a FastAPI app bound to ``engine`` (defaults to the configured one).

    The engine and its session factory are stored on ``app.state`` and resolved
    by ``get_db`` per request, so the database is injected per application
    instance. Tests build an app around an in-memory engine and exercise the real
    startup path with no module globals to patch.
    """
    if engine is None:
        engine = db_session.engine
        session_factory = db_session.SessionLocal
    else:
        session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Create tables on startup so the service is runnable out of the box.

        Done here (not at import time) so importing the app has no database side
        effects. A production service would manage schema changes with a
        migration tool (e.g. Alembic).
        """
        Base.metadata.create_all(bind=app.state.engine)
        yield

    app = FastAPI(
        title="Deployment Events API",
        version=__version__,
        description=(
            "Backend service for ingesting and serving deployment event history."
        ),
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = session_factory

    # Cross-cutting concerns.
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["meta"], summary="Liveness check")
    def health() -> dict[str, str]:
        """Liveness probe for load balancers / orchestrators."""
        return {"status": "ok", "version": __version__}

    return app


# Default application instance used by uvicorn / ASGI servers.
app = create_app()
