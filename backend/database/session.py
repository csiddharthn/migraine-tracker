from __future__ import annotations

"""Purpose: Database session management and engine creation.

Usage: Provides create_engine_from_url, create_session_factory,
and session_scope context manager.

Functions available:
- create_engine_from_url
- create_session_factory
- session_scope

Classes available:
- None

Call hierarchy:
- session.py -> sqlalchemy
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine_from_url(database_url: str, *, echo: bool = False) -> Engine:
    return create_engine(database_url, echo=echo, pool_pre_ping=True)


def create_session_factory(database_url: str, *, echo: bool = False) -> sessionmaker[Session]:
    engine = create_engine_from_url(database_url, echo=echo)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

