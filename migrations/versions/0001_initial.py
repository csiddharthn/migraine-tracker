"""Initial transactional schema.

Revision ID: 0001_initial
Revises: None
"""
from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = postgresql.JSONB(astext_type=sa.Text())

    op.create_table(
        "trigger_definitions",
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("code", name="pk_trigger_definitions"),
    )
    op.bulk_insert(
        sa.table(
            "trigger_definitions",
            sa.column("code", sa.String),
            sa.column("label", sa.String),
            sa.column("description", sa.Text),
            sa.column("sort_order", sa.Integer),
            sa.column("active", sa.Boolean),
        ),
        [
            {"code": "1", "label": "Aufregung / Stress", "description": "DMKG-Auslöser", "sort_order": 1, "active": True},
            {"code": "2", "label": "Erholungsphase", "description": "DMKG-Auslöser", "sort_order": 2, "active": True},
            {"code": "3", "label": "Änderung im Schlaf-Wach-Rhythmus", "description": "DMKG-Auslöser", "sort_order": 3, "active": True},
            {"code": "4", "label": "Menstruation", "description": "DMKG-Auslöser", "sort_order": 4, "active": True},
            {"code": "5", "label": "Kalte Schlafumgebung / Fenster offen", "description": "Persönlich: ca. 17–18 °C", "sort_order": 5, "active": True},
            {"code": "6", "label": "Hitze / hohe Außentemperatur", "description": "Persönlich: >38 °C tagsüber", "sort_order": 6, "active": True},
            {"code": "7", "label": "Spät und zu wenig Schlaf", "description": "Persönlicher Auslöser", "sort_order": 7, "active": True},
            {"code": "8", "label": "Unsicher", "description": "Auslöser nicht sicher zuordenbar", "sort_order": 8, "active": True},
            {"code": "ND", "label": "Nicht dokumentiert (Altbestand)", "description": "Nur für migrierte Excel-Einträge ohne ausgefüllten Auslöser.", "sort_order": 99, "active": False},
        ],
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("name_key", sa.String(length=180), nullable=False),
        sa.Column("tracking_start_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_profiles"),
        sa.UniqueConstraint("name_key", name="uq_user_profiles_name_key"),
    )
    op.create_index("ix_user_profiles_active_display_name", "user_profiles", ["active", "display_name"])

    op.create_table(
        "migraine_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("strength", sa.SmallInteger(), nullable=False),
        sa.Column("duration_hours", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("pain_type", sa.String(length=80), nullable=True),
        sa.Column("entered_laterality", sa.String(length=40), nullable=True),
        sa.Column("aura_codes", json_type, nullable=False),
        sa.Column("vomiting", sa.Boolean(), nullable=False),
        sa.Column("nausea", sa.Boolean(), nullable=False),
        sa.Column("phonophobia", sa.Boolean(), nullable=False),
        sa.Column("photophobia", sa.Boolean(), nullable=False),
        sa.Column("osmophobia", sa.Boolean(), nullable=False),
        sa.Column("other_symptom_codes", json_type, nullable=False),
        sa.Column("medication_name", sa.String(length=200), nullable=True),
        sa.Column("medication_dose", sa.String(length=120), nullable=True),
        sa.Column("medication_effectiveness", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_system", sa.String(length=30), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("duration_hours >= 0", name="ck_migraine_entries_duration_nonnegative"),
        sa.CheckConstraint("strength >= 0 AND strength <= 10", name="ck_migraine_entries_strength_0_10"),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], name="fk_migraine_entries_user_id_user_profiles", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_migraine_entries"),
        sa.UniqueConstraint("user_id", "entry_date", name="uq_migraine_entries_user_entry_date"),
        sa.UniqueConstraint("source_fingerprint", name="uq_migraine_entries_source_fingerprint"),
    )
    op.create_index("ix_migraine_entries_user_date", "migraine_entries", ["user_id", "entry_date"])
    op.create_index("ix_migraine_entries_medication_name", "migraine_entries", ["medication_name"])
    op.create_index("ix_migraine_entries_strength", "migraine_entries", ["strength"])

    op.create_table(
        "entry_triggers",
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("trigger_code", sa.String(length=10), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["migraine_entries.id"], name="fk_entry_triggers_entry_id_migraine_entries", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trigger_code"], ["trigger_definitions.code"], name="fk_entry_triggers_trigger_code_trigger_definitions"),
        sa.PrimaryKeyConstraint("entry_id", "trigger_code", name="pk_entry_triggers"),
    )
    op.create_index("ix_entry_triggers_trigger_code", "entry_triggers", ["trigger_code"])

    op.create_table(
        "daily_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("aimovig_injection", sa.Boolean(), nullable=False),
        sa.Column("momeallerg_nasal_spray", sa.Boolean(), nullable=False),
        sa.Column("amitriptyline_neuraxpharm", sa.Boolean(), nullable=False),
        sa.Column("source_system", sa.String(length=30), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], name="fk_daily_records_user_id_user_profiles", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_daily_records"),
        sa.UniqueConstraint("user_id", "record_date", name="uq_daily_records_user_record_date"),
        sa.UniqueConstraint("source_fingerprint", name="uq_daily_records_source_fingerprint"),
    )
    op.create_index("ix_daily_records_user_date", "daily_records", ["user_id", "record_date"])

    op.create_table(
        "note_interpretations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("onset_minute", sa.Integer(), nullable=True),
        sa.Column("peak_start_minute", sa.Integer(), nullable=True),
        sa.Column("peak_end_minute", sa.Integer(), nullable=True),
        sa.Column("end_minute", sa.Integer(), nullable=True),
        sa.Column("end_status", sa.String(length=40), nullable=True),
        sa.Column("laterality", sa.String(length=40), nullable=True),
        sa.Column("side_detail", sa.String(length=200), nullable=True),
        sa.Column("contexts", json_type, nullable=False),
        sa.Column("symptoms", json_type, nullable=False),
        sa.Column("interventions", json_type, nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("extraction_method", sa.String(length=40), nullable=False),
        sa.Column("automatic_snapshot", json_type, nullable=False),
        sa.Column("is_reviewed", sa.Boolean(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_minute IS NULL OR end_minute BETWEEN 0 AND 4320", name="ck_note_interpretations_end_minute_range"),
        sa.CheckConstraint("onset_minute IS NULL OR onset_minute BETWEEN 0 AND 4320", name="ck_note_interpretations_onset_minute_range"),
        sa.CheckConstraint("peak_end_minute IS NULL OR peak_end_minute BETWEEN 0 AND 4320", name="ck_note_interpretations_peak_end_minute_range"),
        sa.CheckConstraint("peak_start_minute IS NULL OR peak_start_minute BETWEEN 0 AND 4320", name="ck_note_interpretations_peak_start_minute_range"),
        sa.ForeignKeyConstraint(["entry_id"], ["migraine_entries.id"], name="fk_note_interpretations_entry_id_migraine_entries", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_note_interpretations"),
        sa.UniqueConstraint("entry_id", name="uq_note_interpretations_entry_id"),
    )

    op.create_table(
        "entry_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.String(length=30), nullable=False),
        sa.Column("before_payload", json_type, nullable=True),
        sa.Column("after_payload", json_type, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_entry_audit_log"),
    )
    op.create_index("ix_entry_audit_log_entry_id_changed_at", "entry_audit_log", ["entry_id", "changed_at"])

    op.create_table(
        "migration_source_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_file", sa.String(length=500), nullable=False),
        sa.Column("source_sheet", sa.String(length=100), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("raw_payload", json_type, nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("issues", json_type, nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=True),
        sa.Column("daily_record_id", sa.Uuid(), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], name="fk_migration_source_rows_user_id_user_profiles", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_migration_source_rows"),
        sa.UniqueConstraint("user_id", "source_file", "source_sheet", "source_row", name="uq_migration_source_rows_user_source_location"),
    )
    op.create_index("ix_migration_source_rows_user_date", "migration_source_rows", ["user_id", "record_date"])
    op.create_index("ix_migration_source_rows_status", "migration_source_rows", ["status"])


def downgrade() -> None:
    op.drop_table("migration_source_rows")
    op.drop_table("entry_audit_log")
    op.drop_table("note_interpretations")
    op.drop_table("daily_records")
    op.drop_table("entry_triggers")
    op.drop_table("migraine_entries")
    op.drop_table("user_profiles")
    op.drop_table("trigger_definitions")
