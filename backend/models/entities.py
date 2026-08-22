from __future__ import annotations

"""Purpose: SQLAlchemy entity models for migraine tracking.

Usage: Defines UserProfile, MigraineEntry, MedicationIntake, TriggerDefinition,
EntryTrigger, DailyRecord, NoteInterpretation, EntryAuditLog, MigrationSourceRow.

Functions available:
- None

Classes available:
- UserProfile, MigraineEntry, MedicationIntake, TriggerDefinition,
  EntryTrigger, DailyRecord, NoteInterpretation, EntryAuditLog, MigrationSourceRow

Call hierarchy:
- entities.py -> backend.database.base
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base, TimestampMixin


JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class UserProfile(TimestampMixin, Base):
    """Purpose: User profile entity.

    Methodology: Stores user identity, tracking start, and active status.

    Arguments: None (entity definition)

    Returns: None
    """
    __tablename__ = "user_profiles"
    __table_args__ = (Index("ix_user_profiles_active_display_name", "active", "display_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    name_key: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    tracking_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MigraineEntry(TimestampMixin, Base):
    __tablename__ = "migraine_entries"
    __table_args__ = (
        CheckConstraint("strength >= 0 AND strength <= 10", name="strength_0_10"),
        CheckConstraint("duration_hours >= 0", name="duration_nonnegative"),
        UniqueConstraint("user_id", "entry_date", name="uq_migraine_entries_user_entry_date"),
        Index("ix_migraine_entries_user_date", "user_id", "entry_date"),
        Index("ix_migraine_entries_strength", "strength"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    strength: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_hours: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    pain_type: Mapped[str | None] = mapped_column(String(80))
    entered_laterality: Mapped[str | None] = mapped_column(String(40))
    aura_codes: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    vomiting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nausea: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    phonophobia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    photophobia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    osmophobia: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    other_symptom_codes: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_system: Mapped[str] = mapped_column(String(30), default="streamlit", nullable=False)
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True)
    source_narrative: Mapped[str | None] = mapped_column(Text)
    ai_provider: Mapped[str | None] = mapped_column(String(40))
    ai_model: Mapped[str | None] = mapped_column(String(100))
    ai_prompt_version: Mapped[str | None] = mapped_column(String(40))
    ai_extraction: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    ai_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserProfile] = relationship(lazy="joined")

    triggers: Mapped[list[EntryTrigger]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    interpretation: Mapped[NoteInterpretation | None] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    medications: Mapped[list[MedicationIntake]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="MedicationIntake.sequence",
        lazy="selectin",
    )


class MedicationIntake(TimestampMixin, Base):
    __tablename__ = "medication_intakes"
    __table_args__ = (
        UniqueConstraint("entry_id", "sequence", name="uq_medication_intakes_entry_sequence"),
        Index("ix_medication_intakes_entry_id", "entry_id"),
        Index("ix_medication_intakes_name", "name"),
        Index("ix_medication_intakes_taken_at", "taken_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("migraine_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    taken_at: Mapped[time | None] = mapped_column(Time)
    dose: Mapped[str | None] = mapped_column(String(120))
    effectiveness: Mapped[str | None] = mapped_column(String(20))

    entry: Mapped[MigraineEntry] = relationship(back_populates="medications")


class TriggerDefinition(Base):
    __tablename__ = "trigger_definitions"

    code: Mapped[str] = mapped_column(String(10), primary_key=True)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EntryTrigger(Base):
    __tablename__ = "entry_triggers"
    __table_args__ = (Index("ix_entry_triggers_trigger_code", "trigger_code"),)

    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("migraine_entries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    trigger_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("trigger_definitions.code"),
        primary_key=True,
    )

    entry: Mapped[MigraineEntry] = relationship(back_populates="triggers")
    definition: Mapped[TriggerDefinition] = relationship(lazy="joined")


class DailyRecord(TimestampMixin, Base):
    __tablename__ = "daily_records"
    __table_args__ = (
        UniqueConstraint("user_id", "record_date", name="uq_daily_records_user_record_date"),
        Index("ix_daily_records_user_date", "user_id", "record_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    aimovig_injection: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    momeallerg_nasal_spray: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    amitriptyline_neuraxpharm: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_system: Mapped[str] = mapped_column(String(30), default="streamlit", nullable=False)
    source_row: Mapped[int | None] = mapped_column(Integer)
    source_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True)


class NoteInterpretation(TimestampMixin, Base):
    __tablename__ = "note_interpretations"
    __table_args__ = (
        CheckConstraint("onset_minute IS NULL OR onset_minute BETWEEN 0 AND 4320", name="onset_minute_range"),
        CheckConstraint("peak_start_minute IS NULL OR peak_start_minute BETWEEN 0 AND 4320", name="peak_start_minute_range"),
        CheckConstraint("peak_end_minute IS NULL OR peak_end_minute BETWEEN 0 AND 4320", name="peak_end_minute_range"),
        CheckConstraint("end_minute IS NULL OR end_minute BETWEEN 0 AND 4320", name="end_minute_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("migraine_entries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    onset_minute: Mapped[int | None] = mapped_column(Integer)
    peak_start_minute: Mapped[int | None] = mapped_column(Integer)
    peak_end_minute: Mapped[int | None] = mapped_column(Integer)
    end_minute: Mapped[int | None] = mapped_column(Integer)
    end_status: Mapped[str | None] = mapped_column(String(40))
    laterality: Mapped[str | None] = mapped_column(String(40))
    side_detail: Mapped[str | None] = mapped_column(String(200))
    contexts: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    interventions: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="niedrig", nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(40), default="regelbasiert", nullable=False)
    automatic_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, default=dict, nullable=False)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    entry: Mapped[MigraineEntry] = relationship(back_populates="interpretation")


class EntryAuditLog(Base):
    __tablename__ = "entry_audit_log"
    __table_args__ = (Index("ix_entry_audit_log_entry_id_changed_at", "entry_id", "changed_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origin: Mapped[str] = mapped_column(String(30), nullable=False)
    before_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)
    after_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_DOCUMENT)


class MigrationSourceRow(Base):
    __tablename__ = "migration_source_rows"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_file",
            "source_sheet",
            "source_row",
            name="uq_migration_source_rows_user_source_location",
        ),
        Index("ix_migration_source_rows_user_date", "user_id", "record_date"),
        Index("ix_migration_source_rows_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(100), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    record_date: Mapped[date | None] = mapped_column(Date)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    issues: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, default=list, nullable=False)
    entry_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    daily_record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
