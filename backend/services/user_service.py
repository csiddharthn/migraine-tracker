from __future__ import annotations

"""Purpose: User service for user profile management.

Usage: Creates and validates user profiles.

Functions available:
- UserService.create, normalize_name

Classes available:
- UserService, DuplicateUserError

Call hierarchy:
- user_service.py -> backend.repositories.users
"""

import re
import unicodedata
from datetime import date

from sqlalchemy.orm import Session

from backend.models import UserProfile
from backend.repositories import UserRepository


class DuplicateUserError(ValueError):
    pass


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = UserRepository(session)

    def create(self, display_name: str, tracking_start_date: date | None = None) -> UserProfile:
        cleaned = " ".join(display_name.split())
        if len(cleaned) < 2:
            raise ValueError("Bitte geben Sie einen Namen mit mindestens zwei Zeichen ein.")
        if len(cleaned) > 160:
            raise ValueError("Der Name darf höchstens 160 Zeichen lang sein.")
        name_key = normalize_name(cleaned)
        if self.repository.get_by_name_key(name_key) is not None:
            raise DuplicateUserError("Eine Person mit diesem Namen ist bereits vorhanden.")
        profile = UserProfile(
            display_name=cleaned,
            name_key=name_key,
            tracking_start_date=tracking_start_date or date.today(),
            active=True,
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def get_or_create(self, display_name: str, tracking_start_date: date | None = None) -> UserProfile:
        cleaned = " ".join(display_name.split())
        existing = self.repository.get_by_name_key(normalize_name(cleaned))
        if existing is not None:
            if tracking_start_date is not None and tracking_start_date < existing.tracking_start_date:
                existing.tracking_start_date = tracking_start_date
            return existing
        return self.create(cleaned, tracking_start_date)


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
