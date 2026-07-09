"""member bank accounts

Revision ID: 20260709_0010
Revises: 20260709_0009
Create Date: 2026-07-09 00:10:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "20260709_0010"
down_revision: str | None = "20260709_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "member_bank_accounts",
        sa.Column("member_id", GUID(), nullable=False),
        sa.Column("bank_name", sa.String(length=200), nullable=False),
        sa.Column("account_number_encrypted", sa.Text(), nullable=False),
        sa.Column("account_number_masked", sa.String(length=64), nullable=False),
        sa.Column("account_number_search_hash", sa.String(length=64), nullable=False),
        sa.Column("ifsc_code", sa.String(length=32), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("payeezz_mandate_status", sa.String(length=32), nullable=False),
        sa.Column("payeezz_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("payeezz_start_date", sa.Date(), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "payeezz_mandate_status in ('Not Started', 'Pending Approval', 'Approved')",
            name=op.f("ck_member_bank_accounts_member_bank_accounts_payeezz_mandate_status_valid"),
        ),
        sa.CheckConstraint(
            "payeezz_amount is null or payeezz_amount >= 0",
            name=op.f("ck_member_bank_accounts_member_bank_accounts_payeezz_amount_non_negative"),
        ),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], name=op.f("fk_member_bank_accounts_member_id_members")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_member_bank_accounts")),
    )
    op.create_index("ix_member_bank_accounts_member_id", "member_bank_accounts", ["member_id"], unique=False)
    op.create_index(
        "ix_member_bank_accounts_payeezz_mandate_status",
        "member_bank_accounts",
        ["payeezz_mandate_status"],
        unique=False,
    )
    op.create_index(
        "ix_member_bank_accounts_account_number_search_hash",
        "member_bank_accounts",
        ["account_number_search_hash"],
        unique=False,
    )
    op.create_index(
        "uq_member_bank_accounts_active_primary",
        "member_bank_accounts",
        ["member_id"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL AND is_primary = 1"),
        postgresql_where=sa.text("deleted_at IS NULL AND is_primary = true"),
    )
    op.create_index(
        "uq_member_bank_accounts_active_bank",
        "member_bank_accounts",
        ["member_id", "bank_name", "account_number_search_hash"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    bind = op.get_bind()
    members = sa.table(
        "members",
        sa.column("id"),
        sa.column("bank_name"),
        sa.column("bank_account_number_encrypted"),
        sa.column("bank_account_number_masked"),
        sa.column("bank_account_number_search_hash"),
        sa.column("ifsc_code"),
        sa.column("payeezz_mandate_status"),
        sa.column("payeezz_amount"),
        sa.column("payeezz_start_date"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    member_bank_accounts = sa.table(
        "member_bank_accounts",
        sa.column("id"),
        sa.column("member_id"),
        sa.column("bank_name"),
        sa.column("account_number_encrypted"),
        sa.column("account_number_masked"),
        sa.column("account_number_search_hash"),
        sa.column("ifsc_code"),
        sa.column("is_primary"),
        sa.column("payeezz_mandate_status"),
        sa.column("payeezz_amount"),
        sa.column("payeezz_start_date"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    rows = bind.execute(
        sa.select(
            members.c.id,
            members.c.bank_name,
            members.c.bank_account_number_encrypted,
            members.c.bank_account_number_masked,
            members.c.bank_account_number_search_hash,
            members.c.ifsc_code,
            members.c.payeezz_mandate_status,
            members.c.payeezz_amount,
            members.c.payeezz_start_date,
            members.c.created_at,
            members.c.updated_at,
        ).where(
            members.c.bank_name.is_not(None)
            | members.c.bank_account_number_encrypted.is_not(None)
            | members.c.ifsc_code.is_not(None)
            | (members.c.payeezz_mandate_status != "Not Started")
            | members.c.payeezz_amount.is_not(None)
            | members.c.payeezz_start_date.is_not(None)
        )
    ).mappings()
    for row in rows:
        if not row["bank_account_number_encrypted"] or not row["bank_account_number_search_hash"]:
            continue
        bind.execute(
            member_bank_accounts.insert().values(
                id=str(uuid4()),
                member_id=row["id"],
                bank_name=row["bank_name"] or "Unknown Bank",
                account_number_encrypted=row["bank_account_number_encrypted"],
                account_number_masked=row["bank_account_number_masked"] or "bank account ending ****",
                account_number_search_hash=row["bank_account_number_search_hash"],
                ifsc_code=row["ifsc_code"],
                is_primary=True,
                payeezz_mandate_status=row["payeezz_mandate_status"] or "Not Started",
                payeezz_amount=row["payeezz_amount"],
                payeezz_start_date=row["payeezz_start_date"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    op.drop_index("ix_members_payeezz_mandate_status", table_name="members")
    with op.batch_alter_table("members") as batch_op:
        batch_op.drop_constraint(op.f("ck_members_members_payeezz_mandate_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_payeezz_amount_non_negative"), type_="check")
        batch_op.drop_column("bank_name")
        batch_op.drop_column("bank_account_number_encrypted")
        batch_op.drop_column("bank_account_number_masked")
        batch_op.drop_column("bank_account_number_search_hash")
        batch_op.drop_column("ifsc_code")
        batch_op.drop_column("payeezz_mandate_status")
        batch_op.drop_column("payeezz_amount")
        batch_op.drop_column("payeezz_start_date")


def downgrade() -> None:
    with op.batch_alter_table("members") as batch_op:
        batch_op.add_column(sa.Column("bank_name", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("bank_account_number_encrypted", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("bank_account_number_masked", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("bank_account_number_search_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("ifsc_code", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("payeezz_mandate_status", sa.String(length=32), nullable=False, server_default="Not Started"))
        batch_op.add_column(sa.Column("payeezz_amount", sa.Numeric(14, 2), nullable=True))
        batch_op.add_column(sa.Column("payeezz_start_date", sa.Date(), nullable=True))
        batch_op.create_check_constraint(
            op.f("ck_members_members_payeezz_mandate_status_valid"),
            "payeezz_mandate_status in ('Not Started', 'Pending Approval', 'Approved')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_payeezz_amount_non_negative"),
            "payeezz_amount is null or payeezz_amount >= 0",
        )

    bind = op.get_bind()
    members = sa.table(
        "members",
        sa.column("id"),
        sa.column("bank_name"),
        sa.column("bank_account_number_encrypted"),
        sa.column("bank_account_number_masked"),
        sa.column("bank_account_number_search_hash"),
        sa.column("ifsc_code"),
        sa.column("payeezz_mandate_status"),
        sa.column("payeezz_amount"),
        sa.column("payeezz_start_date"),
    )
    member_bank_accounts = sa.table(
        "member_bank_accounts",
        sa.column("member_id"),
        sa.column("bank_name"),
        sa.column("account_number_encrypted"),
        sa.column("account_number_masked"),
        sa.column("account_number_search_hash"),
        sa.column("ifsc_code"),
        sa.column("is_primary"),
        sa.column("payeezz_mandate_status"),
        sa.column("payeezz_amount"),
        sa.column("payeezz_start_date"),
        sa.column("deleted_at"),
    )
    primary_rows = bind.execute(
        sa.select(
            member_bank_accounts.c.member_id,
            member_bank_accounts.c.bank_name,
            member_bank_accounts.c.account_number_encrypted,
            member_bank_accounts.c.account_number_masked,
            member_bank_accounts.c.account_number_search_hash,
            member_bank_accounts.c.ifsc_code,
            member_bank_accounts.c.payeezz_mandate_status,
            member_bank_accounts.c.payeezz_amount,
            member_bank_accounts.c.payeezz_start_date,
        ).where(
            member_bank_accounts.c.deleted_at.is_(None),
            member_bank_accounts.c.is_primary.is_(True),
        )
    ).mappings()
    for row in primary_rows:
        bind.execute(
            members.update()
            .where(members.c.id == row["member_id"])
            .values(
                bank_name=row["bank_name"],
                bank_account_number_encrypted=row["account_number_encrypted"],
                bank_account_number_masked=row["account_number_masked"],
                bank_account_number_search_hash=row["account_number_search_hash"],
                ifsc_code=row["ifsc_code"],
                payeezz_mandate_status=row["payeezz_mandate_status"],
                payeezz_amount=row["payeezz_amount"],
                payeezz_start_date=row["payeezz_start_date"],
            )
        )

    op.create_index("ix_members_payeezz_mandate_status", "members", ["payeezz_mandate_status"], unique=False)
    op.drop_index("uq_member_bank_accounts_active_bank", table_name="member_bank_accounts")
    op.drop_index("uq_member_bank_accounts_active_primary", table_name="member_bank_accounts")
    op.drop_index("ix_member_bank_accounts_account_number_search_hash", table_name="member_bank_accounts")
    op.drop_index("ix_member_bank_accounts_payeezz_mandate_status", table_name="member_bank_accounts")
    op.drop_index("ix_member_bank_accounts_member_id", table_name="member_bank_accounts")
    op.drop_table("member_bank_accounts")
