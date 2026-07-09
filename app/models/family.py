from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import CanStatus, KycStatus, PayeezzStatus, VerificationStatus
from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Family(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "families"
    __table_args__ = (
        Index(
            "uq_families_active_family_code",
            "family_code",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_families_primary_rm_id", "primary_rm_id"),
        Index("ix_families_family_code", "family_code"),
        Index("ix_families_family_head_name", "family_head_name"),
    )

    family_code: Mapped[str] = mapped_column(String(64), nullable=False)
    family_head_name: Mapped[str] = mapped_column(String(200), nullable=False)
    primary_rm_id: Mapped[UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text(), nullable=True)

    primary_rm: Mapped[User | None] = relationship("User")
    members: Mapped[list[Member]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan",
        order_by="Member.name",
    )


class Member(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint(
            "kyc_status in ('Verified', 'Pending Re-KYC', 'Not Started')",
            name="members_kyc_status_valid",
        ),
        CheckConstraint(
            "can_status in ('Pending', 'Available')",
            name="members_can_status_valid",
        ),
        CheckConstraint(
            "((can_number is null and can_status = 'Pending') or "
            "(can_number is not null and can_status = 'Available'))",
            name="members_can_number_status_consistent",
        ),
        CheckConstraint(
            "mobile_verification_status in ('Verified', 'Pending Verification')",
            name="members_mobile_verification_status_valid",
        ),
        CheckConstraint(
            "email_verification_status in ('Verified', 'Pending Verification')",
            name="members_email_verification_status_valid",
        ),
        CheckConstraint(
            "nominee_verification_status in ('Verified', 'Pending Verification')",
            name="members_nominee_verification_status_valid",
        ),
        Index(
            "uq_members_active_can_number",
            "can_number",
            unique=True,
            sqlite_where=text("deleted_at IS NULL AND can_number IS NOT NULL"),
            postgresql_where=text("deleted_at IS NULL AND can_number IS NOT NULL"),
        ),
        Index("ix_members_family_id", "family_id"),
        Index("ix_members_name", "name"),
        Index("ix_members_can_number", "can_number"),
        Index("ix_members_can_status", "can_status"),
        Index("ix_members_kyc_status", "kyc_status"),
        Index("ix_members_mobile_verification_status", "mobile_verification_status"),
        Index("ix_members_email_verification_status", "email_verification_status"),
        Index("ix_members_nominee_verification_status", "nominee_verification_status"),
        Index("ix_members_nominee_name", "nominee_name"),
        Index("ix_members_pan_search_hash", "pan_search_hash"),
        Index("ix_members_mobile_search_hash", "mobile_search_hash"),
        Index("ix_members_email_search_hash", "email_search_hash"),
    )

    family_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    can_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    can_status: Mapped[CanStatus] = mapped_column(String(32), nullable=False)

    pan_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    pan_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pan_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date(), nullable=True)
    kyc_status: Mapped[KycStatus] = mapped_column(String(32), nullable=False)

    mobile_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    mobile_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile_verification_status: Mapped[VerificationStatus] = mapped_column(String(32), nullable=False)

    email_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    email_masked: Mapped[str | None] = mapped_column(String(320), nullable=True)
    email_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_verification_status: Mapped[VerificationStatus] = mapped_column(String(32), nullable=False)
    nominee_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nominee_verification_status: Mapped[VerificationStatus] = mapped_column(String(32), nullable=False)

    remarks: Mapped[str | None] = mapped_column(Text(), nullable=True)

    family: Mapped[Family] = relationship(back_populates="members")
    bank_accounts: Mapped[list[MemberBankAccount]] = relationship(
        back_populates="member",
        cascade="all, delete-orphan",
        order_by="(MemberBankAccount.is_primary.desc(), MemberBankAccount.bank_name, MemberBankAccount.id)",
    )


class MemberBankAccount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "member_bank_accounts"
    __table_args__ = (
        CheckConstraint(
            "payeezz_mandate_status in ('Not Started', 'Pending Approval', 'Approved')",
            name="member_bank_accounts_payeezz_mandate_status_valid",
        ),
        CheckConstraint("payeezz_amount is null or payeezz_amount >= 0", name="member_bank_accounts_payeezz_amount_non_negative"),
        Index(
            "uq_member_bank_accounts_active_primary",
            "member_id",
            unique=True,
            sqlite_where=text("deleted_at IS NULL AND is_primary = 1"),
            postgresql_where=text("deleted_at IS NULL AND is_primary = true"),
        ),
        Index(
            "uq_member_bank_accounts_active_bank",
            "member_id",
            "bank_name",
            "account_number_search_hash",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_member_bank_accounts_member_id", "member_id"),
        Index("ix_member_bank_accounts_payeezz_mandate_status", "payeezz_mandate_status"),
        Index("ix_member_bank_accounts_account_number_search_hash", "account_number_search_hash"),
    )

    member_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("members.id"), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number_encrypted: Mapped[str] = mapped_column(Text(), nullable=False)
    account_number_masked: Mapped[str] = mapped_column(String(64), nullable=False)
    account_number_search_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ifsc_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    payeezz_mandate_status: Mapped[PayeezzStatus] = mapped_column(String(32), nullable=False)
    payeezz_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    payeezz_start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)

    member: Mapped[Member] = relationship(back_populates="bank_accounts")
