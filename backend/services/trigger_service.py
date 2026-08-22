from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import TriggerDefinition
from backend.repositories.triggers import TriggerRepository


class DuplicateTriggerError(ValueError):
    pass


class TriggerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = TriggerRepository(session)

    def create(self, label: str, description: str = "") -> TriggerDefinition:
        cleaned_label = " ".join(label.split())
        cleaned_description = " ".join(description.split())
        if len(cleaned_label) < 2:
            raise ValueError("Bitte geben Sie eine Bezeichnung mit mindestens zwei Zeichen ein.")
        if len(cleaned_label) > 160:
            raise ValueError("Die Bezeichnung darf höchstens 160 Zeichen lang sein.")
        if len(cleaned_description) > 2_000:
            raise ValueError("Die Beschreibung darf höchstens 2.000 Zeichen lang sein.")
        if self.repository.get_by_label(cleaned_label) is not None:
            raise DuplicateTriggerError("Ein Auslöser mit dieser Bezeichnung ist bereits vorhanden.")

        trigger = TriggerDefinition(
            code=self.repository.next_numeric_code(),
            label=cleaned_label,
            description=cleaned_description,
            sort_order=self.repository.next_sort_order(),
            active=True,
        )
        self.session.add(trigger)
        self.session.flush()
        return trigger
