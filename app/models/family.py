from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import KycStatus, PayeezzStatus, VerificationStatus
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
    primary_rm_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text(), nullable=True)

    primary_rm: Mapped[User] = relationship("User")
    members: Mapped[list[Member]] = relationship(
        back_populates="family",
        cascade="all, delete-orphan",
        order_by="Member.name",
    )


class Member(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint(
            "kyc_status in ('Validated', 'Registered', 'No KYC')",
            name="members_kyc_status_valid",
        ),
        CheckConstraint(
            "mobile_status in ('Verified', 'Not Verified')",
            name="members_mobile_status_valid",
        ),
        CheckConstraint(
            "email_status in ('Verified', 'Not Verified')",
            name="members_email_status_valid",
        ),
        CheckConstraint(
            "nominee_status in ('Verified', 'Not Verified')",
            name="members_nominee_status_valid",
        ),
        CheckConstraint(
            "payeezz_status in ('Not Available', 'Sent for Approval', 'Aggregator Accepted')",
            name="members_payeezz_status_valid",
        ),
        CheckConstraint("payeezz_amount is null or payeezz_amount >= 0", name="members_payeezz_amount_non_negative"),
        Index(
            "uq_members_active_can_number",
            "can_number",
            unique=True,
            sqlite_where=text("deleted_at IS NULL"),
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_members_family_id", "family_id"),
        Index("ix_members_name", "name"),
        Index("ix_members_can_number", "can_number"),
        Index("ix_members_kyc_status", "kyc_status"),
        Index("ix_members_payeezz_status", "payeezz_status"),
        Index("ix_members_mobile_status", "mobile_status"),
        Index("ix_members_email_status", "email_status"),
        Index("ix_members_nominee_status", "nominee_status"),
        Index("ix_members_pan_search_hash", "pan_search_hash"),
        Index("ix_members_mobile_search_hash", "mobile_search_hash"),
        Index("ix_members_email_search_hash", "email_search_hash"),
    )

    family_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("families.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    can_number: Mapped[str] = mapped_column(String(64), nullable=False)

    pan_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    pan_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pan_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date(), nullable=True)
    kyc_status: Mapped[KycStatus] = mapped_column(String(32), nullable=False)

    mobile_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    mobile_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mobile_status: Mapped[VerificationStatus] = mapped_column(String(32), nullable=False)

    email_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    email_masked: Mapped[str | None] = mapped_column(String(320), nullable=True)
    email_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email_status: Mapped[VerificationStatus] = mapped_column(String(32), nullable=False)
    nominee_status: Mapped[VerificationStatus] = mapped_column(String(32), nullable=False)

    bank_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bank_account_number_encrypted: Mapped[str | None] = mapped_column(Text(), nullable=True)
    bank_account_number_masked: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bank_account_number_search_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ifsc_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    payeezz_status: Mapped[PayeezzStatus] = mapped_column(String(32), nullable=False)
    payeezz_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    payeezz_start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text(), nullable=True)

    family: Mapped[Family] = relationship(back_populates="members")
