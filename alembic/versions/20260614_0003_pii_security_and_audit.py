"""pii security and audit

Revision ID: 20260614_0003
Revises: 20260614_0002
Create Date: 2026-06-14 20:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "20260614_0003"
down_revision: str | None = "20260614_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", GUID(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("actor_user_id", GUID(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("import_batch_id", GUID(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "action in ('create', 'update', 'delete', 'restore', 'sensitive_read', 'import_commit')",
            name=op.f("ck_audit_logs_audit_logs_action_valid"),
        ),
        sa.CheckConstraint(
            "entity_type in ('family', 'member', 'user', 'import_batch')",
            name=op.f("ck_audit_logs_audit_logs_entity_type_valid"),
        ),
        sa.CheckConstraint(
            "source in ('manual', 'import', 'mfu_api')",
            name=op.f("ck_audit_logs_audit_logs_source_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_actor_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_audit_logs_import_batch_id", "audit_logs", ["import_batch_id"], unique=False)
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], unique=False)
    op.create_index("ix_audit_logs_source", "audit_logs", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_logs_source", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_import_batch_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
