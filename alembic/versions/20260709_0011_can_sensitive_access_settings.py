"""can sensitive access settings

Revision ID: 20260709_0011
Revises: 20260709_0010
Create Date: 2026-07-09 00:11:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "20260709_0011"
down_revision: str | None = "20260709_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FIELDS = ("pan", "mobile", "email", "bank_account_number")


def upgrade() -> None:
    op.create_table(
        "can_sensitive_access_settings",
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("field_name", sa.String(length=64), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role in ('can_ops', 'can_rm')", name=op.f("ck_can_sensitive_access_settings_role_valid")),
        sa.CheckConstraint(
            "field_name in ('pan', 'mobile', 'email', 'bank_account_number')",
            name=op.f("ck_can_sensitive_access_settings_field_name_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_can_sensitive_access_settings")),
        sa.UniqueConstraint("role", "field_name", name=op.f("uq_can_sensitive_access_settings_role_field")),
    )
    op.create_index("ix_can_sensitive_access_settings_role", "can_sensitive_access_settings", ["role"], unique=False)

    settings = sa.table(
        "can_sensitive_access_settings",
        sa.column("id"),
        sa.column("role"),
        sa.column("field_name"),
        sa.column("is_enabled"),
    )
    rows = [
        {
            "id": str(uuid4()),
            "role": role,
            "field_name": field_name,
            "is_enabled": role == "can_ops",
        }
        for role in ("can_ops", "can_rm")
        for field_name in FIELDS
    ]
    op.bulk_insert(settings, rows)


def downgrade() -> None:
    op.drop_index("ix_can_sensitive_access_settings_role", table_name="can_sensitive_access_settings")
    op.drop_table("can_sensitive_access_settings")
