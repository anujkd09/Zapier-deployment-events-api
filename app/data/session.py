"""Database engine, session factory, and FastAPI session dependency."""

from collections.abc import Generator

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


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee it is closed after the request.

    Used as a FastAPI dependency so each request gets an isolated session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
