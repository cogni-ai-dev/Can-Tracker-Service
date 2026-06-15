"""mfu import and sync

Revision ID: 20260614_0005
Revises: 20260614_0004
Create Date: 2026-06-14 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "20260614_0005"
down_revision: str | None = "20260614_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by_user_id", GUID(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("valid_row_count", sa.Integer(), nullable=False),
        sa.Column("error_row_count", sa.Integer(), nullable=False),
        sa.Column("conflict_row_count", sa.Integer(), nullable=False),
        sa.Column("committed_row_count", sa.Integer(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.CheckConstraint(
            "status in ('uploaded', 'validated', 'committed', 'failed')",
            name=op.f("ck_import_batches_import_batches_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_import_batches_uploaded_by_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
    )
    op.create_index("ix_import_batches_created_at", "import_batches", ["created_at"], unique=False)
    op.create_index("ix_import_batches_file_sha256", "import_batches", ["file_sha256"], unique=False)
    op.create_index("ix_import_batches_status", "import_batches", ["status"], unique=False)
    op.create_index(
        "ix_import_batches_uploaded_by_user_id",
        "import_batches",
        ["uploaded_by_user_id"],
        unique=False,
    )

    op.create_table(
        "import_rows",
        sa.Column("import_batch_id", GUID(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data", sa.JSON(), nullable=False),
        sa.Column("normalized_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("family_id", GUID(), nullable=True),
        sa.Column("member_id", GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.CheckConstraint(
            "status in ('valid', 'error', 'conflict', 'committed', 'skipped')",
            name=op.f("ck_import_rows_import_rows_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["families.id"],
            name=op.f("fk_import_rows_family_id_families"),
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            name=op.f("fk_import_rows_import_batch_id_import_batches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["members.id"],
            name=op.f("fk_import_rows_member_id_members"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_rows")),
    )
    op.create_index("ix_import_rows_family_id", "import_rows", ["family_id"], unique=False)
    op.create_index("ix_import_rows_import_batch_id", "import_rows", ["import_batch_id"], unique=False)
    op.create_index("ix_import_rows_member_id", "import_rows", ["member_id"], unique=False)
    op.create_index("ix_import_rows_row_number", "import_rows", ["row_number"], unique=False)
    op.create_index("ix_import_rows_status", "import_rows", ["status"], unique=False)

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_audit_logs_import_batch_id_import_batches"),
            "import_batches",
            ["import_batch_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_constraint(op.f("fk_audit_logs_import_batch_id_import_batches"), type_="foreignkey")

    op.drop_index("ix_import_rows_status", table_name="import_rows")
    op.drop_index("ix_import_rows_row_number", table_name="import_rows")
    op.drop_index("ix_import_rows_member_id", table_name="import_rows")
    op.drop_index("ix_import_rows_import_batch_id", table_name="import_rows")
    op.drop_index("ix_import_rows_family_id", table_name="import_rows")
    op.drop_table("import_rows")

    op.drop_index("ix_import_batches_uploaded_by_user_id", table_name="import_batches")
    op.drop_index("ix_import_batches_status", table_name="import_batches")
    op.drop_index("ix_import_batches_file_sha256", table_name="import_batches")
    op.drop_index("ix_import_batches_created_at", table_name="import_batches")
    op.drop_table("import_batches")
