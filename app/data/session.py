"""Database engine, session factory, and FastAPI session dependency."""

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite needs ``check_same_thread=False`` so a connection can be used across the
# threads that FastAPI/uvicorn may serve requests on. This flag is SQLite-specific,
# so only apply it for SQLite URLs.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(request: Request) -> Generator[Session, None, None]:
    """Yield a database session and guarantee it is closed after the request.

    The session factory is resolved from ``app.state`` (set in ``create_app``)
    rather than the module global, so the engine is injected per application
    instance — tests build an app bound to their own engine with no globals to
    patch. Each request still gets its own isolated session.
    """
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        raise RuntimeError(
            "session_factory is not configured on app.state; "
            "build the app via app.main.create_app()."
        )
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
