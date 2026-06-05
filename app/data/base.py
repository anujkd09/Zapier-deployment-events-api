"""Declarative base for all ORM models.

Kept separate from ``session`` so models can import ``Base`` without pulling in the
engine, and so tooling (e.g. Alembic autogenerate) has a single import target.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""
