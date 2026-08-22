from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest

from backend.analytics.calculations import medication_summary
from backend.services.entry_service import DuplicateEntryError, EntryService
from backend.services.schemas import EntryInput, EntryPatch, MedicationInput
from backend.models import DailyRecord


def payload() -> EntryInput:
    return EntryInput(
        entry_date=date(2026, 8, 10),
        trigger_codes=["8"],
        strength=5,
        duration_hours=Decimal("7.0"),
        pain_type="Dumpf / drückend",
        entered_laterality="Rechts",
        medications=[MedicationInput(name="Eletriptan", taken_at=time(15, 30))],
        notes="Ca. 15:00 Uhr: Beginn der Kopfschmerzen ausschließlich auf der rechten Kopfseite.",
        momeallerg_nasal_spray=True,
    )


def test_create_and_duplicate_prevention(session, user) -> None:
    service = EntryService(session, user.id)
    entry = service.create(payload())
    session.commit()

    assert entry.entry_date == date(2026, 8, 10)
    assert [trigger.trigger_code for trigger in entry.triggers] == ["8"]
    assert entry.interpretation is not None
    assert entry.interpretation.laterality == "rechts"
    assert entry.interpretation.onset_minute == 15 * 60
    assert entry.medications[0].taken_at == time(15, 30)
    assert service.repository.list_medication_names() == ["Eletriptan"]
    assert service.repository.get_daily_record(entry.entry_date).momeallerg_nasal_spray is True

    with pytest.raises(DuplicateEntryError):
        service.create(payload())


def test_legacy_inactive_trigger_can_be_preserved_but_not_added(session, user) -> None:
    service = EntryService(session, user.id)

    with pytest.raises(ValueError):
        service._validate_triggers(["ND"])

    service._validate_triggers(["ND"], allowed_inactive_codes={"ND"})


def test_create_ai_assisted_entry_preserves_provenance(session, user) -> None:
    service = EntryService(session, user.id)
    ai_payload = payload().model_copy(
        update={
            "source_narrative": "Freie ursprüngliche Beschreibung.",
            "ai_provider": "groq",
            "ai_model": "test-model",
            "ai_prompt_version": "test-v1",
            "ai_extraction": {"strength": 7},
        }
    )

    entry = service.create(ai_payload, origin="ai_assisted")

    assert entry.source_system == "ai_assisted"
    assert entry.source_narrative == "Freie ursprüngliche Beschreibung."
    assert entry.ai_model == "test-model"
    assert entry.ai_extraction == {"strength": 7}
    assert entry.ai_reviewed_at is not None


def test_partial_update_preserves_unmentioned_fields(session, user) -> None:
    service = EntryService(session, user.id)
    entry = service.create(payload())
    session.commit()

    updated = service.update(
        entry.id,
        EntryPatch(
            strength=6,
            medications=[
                MedicationInput(name="Eletriptan", taken_at=time(16, 45)),
                MedicationInput(name="Amitriptylin neuraxpharm", taken_at=time(22, 0), dose="10 mg"),
            ],
        ),
    )
    session.commit()

    assert updated.strength == 6
    assert updated.duration_hours == Decimal("7.00")
    assert updated.notes == payload().notes
    assert updated.entry_date == payload().entry_date
    assert [(item.name, item.taken_at) for item in updated.medications] == [
        ("Eletriptan", time(16, 45)),
        ("Amitriptylin neuraxpharm", time(22, 0)),
    ]
    assert service.repository.list_medication_names() == ["Amitriptylin neuraxpharm", "Eletriptan"]
    summaries = {item["label"]: item for item in medication_summary([updated])}
    assert summaries["Eletriptan"]["days"] == 1
    assert summaries["Amitriptylin neuraxpharm (10 mg)"]["days"] == 1


def test_partial_manual_peak_keeps_other_automatic_note_values(session, user) -> None:
    service = EntryService(session, user.id)
    structured_payload = payload().model_copy(
        update={
            "notes": (
                "Zeitlicher Ablauf:\n\n"
                "15:00 Uhr: Beginn der Kopfschmerzen.\n"
                "Höhepunkt: 17:00–20:00 Uhr (Dauer: 180 Minuten).\n"
                "22:00 Uhr: Kopfschmerzen vollständig verschwunden.\n\n"
                "Mögliche Einflussfaktoren: Zu wenig Schlaf.\n\n"
                "Beschwerden und Maßnahmen: Ausschließlich auf der rechten Kopfseite."
            ),
            "note_annotation": {
                "peakStartMinute": 17 * 60 + 15,
                "peakEndMinute": 19 * 60 + 45,
                "confidence": "hoch",
            },
        }
    )

    entry = service.create(structured_payload)
    session.commit()

    assert entry.interpretation.onset_minute == 15 * 60
    assert entry.interpretation.peak_start_minute == 17 * 60 + 15
    assert entry.interpretation.peak_end_minute == 19 * 60 + 45
    assert entry.interpretation.end_minute == 22 * 60
    assert entry.interpretation.laterality == "rechts"
    assert "Später Schlaf / Schlafmangel" in entry.interpretation.contexts
    assert entry.interpretation.is_reviewed is True
    assert entry.interpretation.automatic_snapshot["peak_start_minute"] == 17 * 60


def test_date_correction_moves_streamlit_daily_record(session, user) -> None:
    service = EntryService(session, user.id)
    entry = service.create(payload())
    session.commit()

    updated = service.update(entry.id, EntryPatch(entry_date=date(2026, 8, 11)))
    session.commit()

    records = session.query(DailyRecord).order_by(DailyRecord.record_date).all()
    assert updated.entry_date == date(2026, 8, 11)
    assert [record.record_date for record in records] == [date(2026, 8, 11)]
    assert records[0].momeallerg_nasal_spray is True
