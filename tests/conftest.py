from __future__ import annotations

"""Purpose: Shared test fixtures.

Usage: Provides session and user fixtures for tests.

Functions available:
- session (fixture), user (fixture)

Classes available:
- None

Call hierarchy:
- conftest.py -> backend.database.base, backend.services.user_service
"""

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.database.base import Base
from backend.database.seed import seed_reference_data
from backend.services.user_service import UserService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        seed_reference_data(database_session)
        database_session.commit()
        yield database_session
        database_session.rollback()


@pytest.fixture
def user(session: Session):
    profile = UserService(session).create("Testperson", date(2026, 6, 1))
    session.commit()
    return profile
