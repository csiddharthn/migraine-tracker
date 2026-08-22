from __future__ import annotations

"""Purpose: User repository for user profile management.

Usage: Retrieves and lists UserProfile records.

Functions available:
- UserRepository.get, get_by_name_key, list_users

Classes available:
- UserRepository

Call hierarchy:
- users.py -> backend.models.UserProfile
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import UserProfile


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: uuid.UUID) -> UserProfile | None:
        return self.session.get(UserProfile, user_id)

    def get_by_name_key(self, name_key: str) -> UserProfile | None:
        return self.session.scalar(select(UserProfile).where(UserProfile.name_key == name_key))

    def list_users(self, *, active_only: bool = True) -> list[UserProfile]:
        statement = select(UserProfile)
        if active_only:
            statement = statement.where(UserProfile.active.is_(True))
        return list(self.session.scalars(statement.order_by(UserProfile.display_name)))
