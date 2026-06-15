"""reporting and exports

Revision ID: 20260614_0006
Revises: 20260614_0005
Create Date: 2026-06-15 00:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "20260614_0006"
down_revision: str | None = "20260614_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_exports",
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("exported_by_user_id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.CheckConstraint(
            "report_type in ('kyc_pending', 'payeezz_pending', 'contact_pending', "
            "'family_compliance', 'rm_tasks', 'full')",
            name=op.f("ck_report_exports_report_exports_report_type_valid"),
        ),
        sa.CheckConstraint(
            "format in ('csv', 'xlsx', 'pdf')",
            name=op.f("ck_report_exports_report_exports_format_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["exported_by_user_id"],
            ["users.id"],
            name=op.f("fk_report_exports_exported_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_exports")),
    )
    op.create_index("ix_report_exports_created_at", "report_exports", ["created_at"], unique=False)
    op.create_index("ix_report_exports_exported_by_user_id", "report_exports", ["exported_by_user_id"], unique=False)
    op.create_index("ix_report_exports_format", "report_exports", ["format"], unique=False)
    op.create_index("ix_report_exports_report_type", "report_exports", ["report_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_report_exports_report_type", table_name="report_exports")
    op.drop_index("ix_report_exports_format", table_name="report_exports")
    op.drop_index("ix_report_exports_exported_by_user_id", table_name="report_exports")
    op.drop_index("ix_report_exports_created_at", table_name="report_exports")
    op.drop_table("report_exports")
