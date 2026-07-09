"""nullable can and status renames

Revision ID: 20260709_0008
Revises: 20260616_0007
Create Date: 2026-07-09 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260709_0008"
down_revision: str | None = "20260616_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("uq_members_active_can_number", table_name="members")
    op.drop_index("ix_members_payeezz_status", table_name="members")
    op.drop_index("ix_members_nominee_status", table_name="members")
    op.drop_index("ix_members_mobile_status", table_name="members")
    op.drop_index("ix_members_email_status", table_name="members")

    with op.batch_alter_table("members") as batch_op:
        batch_op.drop_constraint(op.f("ck_members_members_kyc_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_mobile_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_email_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_nominee_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_payeezz_status_valid"), type_="check")
        batch_op.add_column(sa.Column("can_status", sa.String(length=32), nullable=True))
        batch_op.alter_column("can_number", existing_type=sa.String(length=64), nullable=True)
        batch_op.alter_column("mobile_status", new_column_name="mobile_verification_status")
        batch_op.alter_column("email_status", new_column_name="email_verification_status")
        batch_op.alter_column("nominee_status", new_column_name="nominee_verification_status")
        batch_op.alter_column("payeezz_status", new_column_name="payeezz_mandate_status")

    op.execute("update members set can_status = 'Available' where can_number is not null")
    op.execute("update members set can_status = 'Pending' where can_number is null")
    op.execute(
        """
        update members
        set kyc_status = case kyc_status
            when 'Validated' then 'Verified'
            when 'Registered' then 'Pending Re-KYC'
            when 'No KYC' then 'Not Started'
            else kyc_status
        end
        """
    )
    for column_name in (
        "mobile_verification_status",
        "email_verification_status",
        "nominee_verification_status",
    ):
        op.execute(
            f"""
            update members
            set {column_name} = case {column_name}
                when 'Not Verified' then 'Pending Verification'
                else {column_name}
            end
            """
        )
    op.execute(
        """
        update members
        set payeezz_mandate_status = case payeezz_mandate_status
            when 'Not Available' then 'Not Started'
            when 'Sent for Approval' then 'Pending Approval'
            when 'Aggregator Accepted' then 'Approved'
            else payeezz_mandate_status
        end
        """
    )

    with op.batch_alter_table("members") as batch_op:
        batch_op.alter_column("can_status", existing_type=sa.String(length=32), nullable=False)
        batch_op.create_check_constraint(
            op.f("ck_members_members_can_status_valid"),
            "can_status in ('Pending', 'Available')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_can_number_status_consistent"),
            "((can_number is null and can_status = 'Pending') or "
            "(can_number is not null and can_status = 'Available'))",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_kyc_status_valid"),
            "kyc_status in ('Verified', 'Pending Re-KYC', 'Not Started')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_mobile_verification_status_valid"),
            "mobile_verification_status in ('Verified', 'Pending Verification')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_email_verification_status_valid"),
            "email_verification_status in ('Verified', 'Pending Verification')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_nominee_verification_status_valid"),
            "nominee_verification_status in ('Verified', 'Pending Verification')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_payeezz_mandate_status_valid"),
            "payeezz_mandate_status in ('Not Started', 'Pending Approval', 'Approved')",
        )

    op.create_index("ix_members_can_status", "members", ["can_status"], unique=False)
    op.create_index("ix_members_mobile_verification_status", "members", ["mobile_verification_status"], unique=False)
    op.create_index("ix_members_email_verification_status", "members", ["email_verification_status"], unique=False)
    op.create_index("ix_members_nominee_verification_status", "members", ["nominee_verification_status"], unique=False)
    op.create_index("ix_members_payeezz_mandate_status", "members", ["payeezz_mandate_status"], unique=False)
    op.create_index(
        "uq_members_active_can_number",
        "members",
        ["can_number"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL AND can_number IS NOT NULL"),
        postgresql_where=sa.text("deleted_at IS NULL AND can_number IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_members_active_can_number", table_name="members")
    op.drop_index("ix_members_payeezz_mandate_status", table_name="members")
    op.drop_index("ix_members_nominee_verification_status", table_name="members")
    op.drop_index("ix_members_email_verification_status", table_name="members")
    op.drop_index("ix_members_mobile_verification_status", table_name="members")
    op.drop_index("ix_members_can_status", table_name="members")

    with op.batch_alter_table("members") as batch_op:
        batch_op.drop_constraint(op.f("ck_members_members_can_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_can_number_status_consistent"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_kyc_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_mobile_verification_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_email_verification_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_nominee_verification_status_valid"), type_="check")
        batch_op.drop_constraint(op.f("ck_members_members_payeezz_mandate_status_valid"), type_="check")

    op.execute("update members set can_number = id where can_number is null")
    op.execute(
        """
        update members
        set kyc_status = case kyc_status
            when 'Verified' then 'Validated'
            when 'Pending Re-KYC' then 'Registered'
            when 'Not Started' then 'No KYC'
            else kyc_status
        end
        """
    )
    for column_name in (
        "mobile_verification_status",
        "email_verification_status",
        "nominee_verification_status",
    ):
        op.execute(
            f"""
            update members
            set {column_name} = case {column_name}
                when 'Pending Verification' then 'Not Verified'
                else {column_name}
            end
            """
        )
    op.execute(
        """
        update members
        set payeezz_mandate_status = case payeezz_mandate_status
            when 'Not Started' then 'Not Available'
            when 'Pending Approval' then 'Sent for Approval'
            when 'Approved' then 'Aggregator Accepted'
            else payeezz_mandate_status
        end
        """
    )

    with op.batch_alter_table("members") as batch_op:
        batch_op.alter_column("payeezz_mandate_status", new_column_name="payeezz_status")
        batch_op.alter_column("nominee_verification_status", new_column_name="nominee_status")
        batch_op.alter_column("email_verification_status", new_column_name="email_status")
        batch_op.alter_column("mobile_verification_status", new_column_name="mobile_status")
        batch_op.alter_column("can_number", existing_type=sa.String(length=64), nullable=False)
        batch_op.drop_column("can_status")
        batch_op.create_check_constraint(
            op.f("ck_members_members_kyc_status_valid"),
            "kyc_status in ('Validated', 'Registered', 'No KYC')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_mobile_status_valid"),
            "mobile_status in ('Verified', 'Not Verified')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_email_status_valid"),
            "email_status in ('Verified', 'Not Verified')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_nominee_status_valid"),
            "nominee_status in ('Verified', 'Not Verified')",
        )
        batch_op.create_check_constraint(
            op.f("ck_members_members_payeezz_status_valid"),
            "payeezz_status in ('Not Available', 'Sent for Approval', 'Aggregator Accepted')",
        )

    op.create_index("ix_members_email_status", "members", ["email_status"], unique=False)
    op.create_index("ix_members_mobile_status", "members", ["mobile_status"], unique=False)
    op.create_index("ix_members_nominee_status", "members", ["nominee_status"], unique=False)
    op.create_index("ix_members_payeezz_status", "members", ["payeezz_status"], unique=False)
    op.create_index(
        "uq_members_active_can_number",
        "members",
        ["can_number"],
        unique=True,
        sqlite_where=sa.text("deleted_at IS NULL"),
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
