from __future__ import annotations

"""Purpose: Credential repository for user authentication.

Usage: Manages UserCredential records.

Functions available:
- CredentialRepository.get_by_username, get_by_user_id, create, delete

Classes available:
- CredentialRepository
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import UserCredential


class CredentialRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_username(self, username: str) -> UserCredential | None:
        return self.session.scalar(select(UserCredential).where(UserCredential.username == username))

    def get_by_user_id(self, user_id: uuid.UUID) -> UserCredential | None:
        return self.session.scalar(select(UserCredential).where(UserCredential.user_id == user_id))

    def create(self, user_id: uuid.UUID, username: str, password_hash: str) -> UserCredential:
        cred = UserCredential(user_id=user_id, username=username, password_hash=password_hash)
        self.session.add(cred)
        self.session.flush()
        return cred
