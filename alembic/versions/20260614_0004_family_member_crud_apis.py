"""family member crud apis

Revision ID: 20260614_0004
Revises: 20260614_0003
Create Date: 2026-06-14 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "20260614_0004"
down_revision: str | None = "20260614_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "families",
        sa.Column("family_code", sa.String(length=64), nullable=False),
        sa.Column("family_head_name", sa.String(length=200), nullable=False),
        sa.Column("primary_rm_id", GUID(), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["primary_rm_id"],
            ["users.id"],
            name=op.f("fk_families_primary_rm_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_families")),
    )
    op.create_index("ix_families_family_code", "families", ["family_code"], unique=False)
    op.create_index("ix_families_family_head_name", "families", ["family_head_name"], unique=False)
    op.create_index("ix_families_primary_rm_id", "families", ["primary_rm_id"], unique=False)
    op.create_index(
        "uq_families_active_family_code",
        "families",
        ["family_code"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "members",
        sa.Column("family_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("can_number", sa.String(length=64), nullable=False),
        sa.Column("pan_encrypted", sa.Text(), nullable=True),
        sa.Column("pan_masked", sa.String(length=64), nullable=True),
        sa.Column("pan_search_hash", sa.String(length=64), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("kyc_status", sa.String(length=32), nullable=False),
        sa.Column("mobile_encrypted", sa.Text(), nullable=True),
        sa.Column("mobile_masked", sa.String(length=64), nullable=True),
        sa.Column("mobile_search_hash", sa.String(length=64), nullable=True),
        sa.Column("mobile_status", sa.String(length=32), nullable=False),
        sa.Column("email_encrypted", sa.Text(), nullable=True),
        sa.Column("email_masked", sa.String(length=320), nullable=True),
        sa.Column("email_search_hash", sa.String(length=64), nullable=True),
        sa.Column("email_status", sa.String(length=32), nullable=False),
        sa.Column("nominee_status", sa.String(length=32), nullable=False),
        sa.Column("bank_name", sa.String(length=200), nullable=True),
        sa.Column("bank_account_number_encrypted", sa.Text(), nullable=True),
        sa.Column("bank_account_number_masked", sa.String(length=64), nullable=True),
        sa.Column("bank_account_number_search_hash", sa.String(length=64), nullable=True),
        sa.Column("ifsc_code", sa.String(length=32), nullable=True),
        sa.Column("payeezz_status", sa.String(length=32), nullable=False),
        sa.Column("payeezz_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("payeezz_start_date", sa.Date(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "email_status in ('Verified', 'Not Verified')",
            name=op.f("ck_members_members_email_status_valid"),
        ),
        sa.CheckConstraint(
            "kyc_status in ('Validated', 'Registered', 'No KYC')",
            name=op.f("ck_members_members_kyc_status_valid"),
        ),
        sa.CheckConstraint(
            "mobile_status in ('Verified', 'Not Verified')",
            name=op.f("ck_members_members_mobile_status_valid"),
        ),
        sa.CheckConstraint(
            "nominee_status in ('Verified', 'Not Verified')",
            name=op.f("ck_members_members_nominee_status_valid"),
        ),
        sa.CheckConstraint(
            "payeezz_amount is null or payeezz_amount >= 0",
            name=op.f("ck_members_members_payeezz_amount_non_negative"),
        ),
        sa.CheckConstraint(
            "payeezz_status in ('Not Available', 'Sent for Approval', 'Aggregator Accepted')",
            name=op.f("ck_members_members_payeezz_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["family_id"],
            ["families.id"],
            name=op.f("fk_members_family_id_families"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_members")),
    )
    op.create_index("ix_members_can_number", "members", ["can_number"], unique=False)
    op.create_index("ix_members_email_search_hash", "members", ["email_search_hash"], unique=False)
    op.create_index("ix_members_email_status", "members", ["email_status"], unique=False)
    op.create_index("ix_members_family_id", "members", ["family_id"], unique=False)
    op.create_index("ix_members_kyc_status", "members", ["kyc_status"], unique=False)
    op.create_index("ix_members_mobile_search_hash", "members", ["mobile_search_hash"], unique=False)
    op.create_index("ix_members_mobile_status", "members", ["mobile_status"], unique=False)
    op.create_index("ix_members_name", "members", ["name"], unique=False)
    op.create_index("ix_members_nominee_status", "members", ["nominee_status"], unique=False)
    op.create_index("ix_members_pan_search_hash", "members", ["pan_search_hash"], unique=False)
    op.create_index("ix_members_payeezz_status", "members", ["payeezz_status"], unique=False)
    op.create_index(
        "uq_members_active_can_number",
        "members",
        ["can_number"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_members_active_can_number", table_name="members")
    op.drop_index("ix_members_payeezz_status", table_name="members")
    op.drop_index("ix_members_pan_search_hash", table_name="members")
    op.drop_index("ix_members_nominee_status", table_name="members")
    op.drop_index("ix_members_name", table_name="members")
    op.drop_index("ix_members_mobile_status", table_name="members")
    op.drop_index("ix_members_mobile_search_hash", table_name="members")
    op.drop_index("ix_members_kyc_status", table_name="members")
    op.drop_index("ix_members_family_id", table_name="members")
    op.drop_index("ix_members_email_status", table_name="members")
    op.drop_index("ix_members_email_search_hash", table_name="members")
    op.drop_index("ix_members_can_number", table_name="members")
    op.drop_table("members")

    op.drop_index("uq_families_active_family_code", table_name="families")
    op.drop_index("ix_families_primary_rm_id", table_name="families")
    op.drop_index("ix_families_family_head_name", table_name="families")
    op.drop_index("ix_families_family_code", table_name="families")
    op.drop_table("families")
