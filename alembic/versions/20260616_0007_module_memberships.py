"""module memberships

Revision ID: 20260616_0007
Revises: 20260614_0006
Create Date: 2026-06-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "20260616_0007"
down_revision: str | None = "20260614_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "modules",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "code in ('can_compliance', 'client_crm')",
            name=op.f("ck_modules_modules_code_valid"),
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_modules")),
    )
    op.create_table(
        "user_module_memberships",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("module_code", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "module_code in ('can_compliance', 'client_crm')",
            name=op.f("ck_user_module_memberships_user_module_memberships_module_code_valid"),
        ),
        sa.CheckConstraint(
            (
                "role in ('can_admin', 'can_ops', 'can_rm', 'can_management', "
                "'crm_admin', 'crm_ops', 'crm_relationship_manager', 'crm_viewer')"
            ),
            name=op.f("ck_user_module_memberships_user_module_memberships_role_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["module_code"],
            ["modules.code"],
            name=op.f("fk_user_module_memberships_module_code_modules"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_module_memberships_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_module_memberships")),
        sa.UniqueConstraint("user_id", "module_code", name="uq_user_module_memberships_user_module"),
    )
    op.create_index(
        "ix_user_module_memberships_is_active",
        "user_module_memberships",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "ix_user_module_memberships_module_code",
        "user_module_memberships",
        ["module_code"],
        unique=False,
    )
    op.create_index("ix_user_module_memberships_role", "user_module_memberships", ["role"], unique=False)
    op.create_index("ix_user_module_memberships_user_id", "user_module_memberships", ["user_id"], unique=False)

    op.bulk_insert(
        sa.table(
            "modules",
            sa.column("code", sa.String),
            sa.column("name", sa.String),
            sa.column("is_active", sa.Boolean),
        ),
        [
            {"code": "can_compliance", "name": "CAN Compliance", "is_active": True},
            {"code": "client_crm", "name": "Client CRM", "is_active": True},
        ],
    )

    op.execute(
        """
        insert into user_module_memberships (
            id, user_id, module_code, role, is_active, created_at, updated_at, deleted_at
        )
        select
            users.id,
            users.id,
            'can_compliance',
            case users.role
                when 'admin' then 'can_admin'
                when 'ops' then 'can_ops'
                when 'rm' then 'can_rm'
                when 'management' then 'can_management'
            end,
            users.is_active,
            current_timestamp,
            current_timestamp,
            users.deleted_at
        from users
        where users.role in ('admin', 'ops', 'rm', 'management')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_user_module_memberships_user_id", table_name="user_module_memberships")
    op.drop_index("ix_user_module_memberships_role", table_name="user_module_memberships")
    op.drop_index("ix_user_module_memberships_module_code", table_name="user_module_memberships")
    op.drop_index("ix_user_module_memberships_is_active", table_name="user_module_memberships")
    op.drop_table("user_module_memberships")
    op.drop_table("modules")
