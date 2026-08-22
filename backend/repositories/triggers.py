from __future__ import annotations

"""Purpose: Trigger repository for trigger definition management.

Usage: Lists, retrieves, and creates trigger definitions.

Functions available:
- TriggerRepository.list_all, get_by_label, next_numeric_code, next_sort_order

Classes available:
- TriggerRepository

Call hierarchy:
- triggers.py -> backend.models.TriggerDefinition
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import TriggerDefinition


class TriggerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[TriggerDefinition]:
        return list(self.session.scalars(select(TriggerDefinition).order_by(TriggerDefinition.sort_order, TriggerDefinition.code)))

    def get_by_label(self, label: str) -> TriggerDefinition | None:
        return self.session.scalar(
            select(TriggerDefinition).where(func.lower(TriggerDefinition.label) == label.lower())
        )

    def next_numeric_code(self) -> str:
        codes = self.session.scalars(select(TriggerDefinition.code)).all()
        numeric_codes = [int(code) for code in codes if code.isdigit()]
        return str(max(numeric_codes, default=0) + 1)

    def next_sort_order(self) -> int:
        current = self.session.scalar(
            select(func.max(TriggerDefinition.sort_order)).where(TriggerDefinition.active.is_(True))
        )
        return int(current or 0) + 1
