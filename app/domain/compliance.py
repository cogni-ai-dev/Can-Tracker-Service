"""Pure compliance calculations for member and family status records."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.domain.enums import CanStatus, KycStatus, PayeezzStatus, VerificationStatus
from app.domain.records import active, value


@dataclass(frozen=True)
class CountPercentage:
    count: int
    percentage: int


@dataclass(frozen=True)
class KycMetrics:
    total_members: int
    verified: CountPercentage
    pending_rekyc: CountPercentage
    not_started: CountPercentage
    pending: CountPercentage
    completion: CountPercentage


@dataclass(frozen=True)
class PayeezzMetrics:
    total_members: int
    approved: CountPercentage
    pending_approval: CountPercentage
    not_started: CountPercentage
    pending: CountPercentage
    completion: CountPercentage


@dataclass(frozen=True)
class VerificationMetrics:
    total_members: int
    verified: CountPercentage
    pending_verification: CountPercentage
    completion: CountPercentage
    pending: CountPercentage


@dataclass(frozen=True)
class FamilyCompletion:
    total_members: int
    total_cans: int
    kyc_completion: CountPercentage
    payeezz_completion: CountPercentage
    mobile_verification: CountPercentage
    email_verification: CountPercentage
    nominee_verification: CountPercentage

    @property
    def kyc_completion_pct(self) -> int:
        return self.kyc_completion.percentage

    @property
    def payeezz_completion_pct(self) -> int:
        return self.payeezz_completion.percentage

    @property
    def mobile_verification_pct(self) -> int:
        return self.mobile_verification.percentage

    @property
    def email_verification_pct(self) -> int:
        return self.email_verification.percentage

    @property
    def nominee_verification_pct(self) -> int:
        return self.nominee_verification.percentage


def percentage(count: int, denominator: int) -> int:
    """Return rounded whole-number percentage, with zero for empty denominators."""

    if denominator <= 0:
        return 0
    ratio = (Decimal(count) / Decimal(denominator)) * Decimal(100)
    return int(ratio.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def count_percentage(count: int, total: int) -> CountPercentage:
    return CountPercentage(count=count, percentage=percentage(count, total))


def _members_tuple(members: Iterable[Any]) -> tuple[Any, ...]:
    return tuple(member for member in members if active(member))


def _status(record: Any, canonical_name: str, frontend_name: str) -> Any:
    return value(record, canonical_name, frontend_name, default=None)


def _count_status(members: tuple[Any, ...], canonical_name: str, frontend_name: str, status: str) -> int:
    return sum(1 for member in members if _status(member, canonical_name, frontend_name) == status)


def kyc_counts(members: Iterable[Any]) -> KycMetrics:
    records = _members_tuple(members)
    total = len(records)
    verified = _count_status(records, "kyc_status", "kyc", KycStatus.VERIFIED.value)
    pending_rekyc = _count_status(records, "kyc_status", "kyc", KycStatus.PENDING_REKYC.value)
    not_started = _count_status(records, "kyc_status", "kyc", KycStatus.NOT_STARTED.value)
    pending = pending_rekyc + not_started
    return KycMetrics(
        total_members=total,
        verified=count_percentage(verified, total),
        pending_rekyc=count_percentage(pending_rekyc, total),
        not_started=count_percentage(not_started, total),
        pending=count_percentage(pending, total),
        completion=count_percentage(verified, total),
    )


def payeezz_counts(members: Iterable[Any]) -> PayeezzMetrics:
    records = _members_tuple(members)
    total = len(records)
    approved = _count_status(
        records,
        "payeezz_mandate_status",
        "payeezz",
        PayeezzStatus.APPROVED.value,
    )
    pending_approval = _count_status(
        records,
        "payeezz_mandate_status",
        "payeezz",
        PayeezzStatus.PENDING_APPROVAL.value,
    )
    not_started = _count_status(
        records,
        "payeezz_mandate_status",
        "payeezz",
        PayeezzStatus.NOT_STARTED.value,
    )
    pending = pending_approval + not_started
    return PayeezzMetrics(
        total_members=total,
        approved=count_percentage(approved, total),
        pending_approval=count_percentage(pending_approval, total),
        not_started=count_percentage(not_started, total),
        pending=count_percentage(pending, total),
        completion=count_percentage(approved, total),
    )


def verification_counts(
    members: Iterable[Any],
    canonical_name: str,
    frontend_name: str,
) -> VerificationMetrics:
    records = _members_tuple(members)
    total = len(records)
    verified = _count_status(
        records,
        canonical_name,
        frontend_name,
        VerificationStatus.VERIFIED.value,
    )
    pending_verification = _count_status(
        records,
        canonical_name,
        frontend_name,
        VerificationStatus.PENDING_VERIFICATION.value,
    )
    return VerificationMetrics(
        total_members=total,
        verified=count_percentage(verified, total),
        pending_verification=count_percentage(pending_verification, total),
        completion=count_percentage(verified, total),
        pending=count_percentage(pending_verification, total),
    )


def mobile_verification_counts(members: Iterable[Any]) -> VerificationMetrics:
    return verification_counts(members, "mobile_verification_status", "mobile")


def email_verification_counts(members: Iterable[Any]) -> VerificationMetrics:
    return verification_counts(members, "email_verification_status", "email")


def nominee_verification_counts(members: Iterable[Any]) -> VerificationMetrics:
    return verification_counts(members, "nominee_verification_status", "nominee")


def family_completion(members: Iterable[Any]) -> FamilyCompletion:
    records = _members_tuple(members)
    kyc = kyc_counts(records)
    payeezz = payeezz_counts(records)
    mobile = mobile_verification_counts(records)
    email = email_verification_counts(records)
    nominee = nominee_verification_counts(records)
    return FamilyCompletion(
        total_members=len(records),
        total_cans=sum(
            1
            for member in records
            if value(member, "can_status", default=None) == CanStatus.AVAILABLE.value
            and value(member, "can_number", default=None)
        ),
        kyc_completion=kyc.completion,
        payeezz_completion=payeezz.completion,
        mobile_verification=mobile.completion,
        email_verification=email.completion,
        nominee_verification=nominee.completion,
    )
