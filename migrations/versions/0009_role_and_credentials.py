"""Add role to user_profiles and create user_credentials table.

Revision ID: 0009_role_and_credentials
Revises: 0008_split_notes
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009_role_and_credentials"
down_revision = "0008_split_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role column to user_profiles
    op.add_column("user_profiles", sa.Column("role", sa.String(length=20), nullable=False, server_default="user"))
    # Create user_credentials table
    op.create_table(
        "user_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], name="fk_user_credentials_user_id_user_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_user_credentials"),
        sa.UniqueConstraint("username", name="uq_user_credentials_username"),
        sa.UniqueConstraint("user_id", name="uq_user_credentials_user_id"),
    )
    op.create_index("ix_user_credentials_username", "user_credentials", ["username"])


def downgrade() -> None:
    op.drop_index("ix_user_credentials_username", table_name="user_credentials")
    op.drop_table("user_credentials")
    op.drop_column("user_profiles", "role")
