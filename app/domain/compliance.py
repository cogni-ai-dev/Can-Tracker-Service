"""Pure compliance calculations for member and family status records."""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.domain.enums import KycStatus, PayeezzStatus, VerificationStatus
from app.domain.records import active, value


@dataclass(frozen=True)
class CountPercentage:
    count: int
    percentage: int


@dataclass(frozen=True)
class KycMetrics:
    total_members: int
    validated: CountPercentage
    registered: CountPercentage
    no_kyc: CountPercentage
    pending: CountPercentage
    completion: CountPercentage


@dataclass(frozen=True)
class PayeezzMetrics:
    total_members: int
    aggregator_accepted: CountPercentage
    sent_for_approval: CountPercentage
    not_available: CountPercentage
    pending: CountPercentage
    completion: CountPercentage


@dataclass(frozen=True)
class VerificationMetrics:
    total_members: int
    verified: CountPercentage
    not_verified: CountPercentage
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
    validated = _count_status(records, "kyc_status", "kyc", KycStatus.VALIDATED.value)
    registered = _count_status(records, "kyc_status", "kyc", KycStatus.REGISTERED.value)
    no_kyc = _count_status(records, "kyc_status", "kyc", KycStatus.NO_KYC.value)
    pending = registered + no_kyc
    return KycMetrics(
        total_members=total,
        validated=count_percentage(validated, total),
        registered=count_percentage(registered, total),
        no_kyc=count_percentage(no_kyc, total),
        pending=count_percentage(pending, total),
        completion=count_percentage(validated, total),
    )


def payeezz_counts(members: Iterable[Any]) -> PayeezzMetrics:
    records = _members_tuple(members)
    total = len(records)
    accepted = _count_status(
        records,
        "payeezz_status",
        "payeezz",
        PayeezzStatus.AGGREGATOR_ACCEPTED.value,
    )
    sent = _count_status(
        records,
        "payeezz_status",
        "payeezz",
        PayeezzStatus.SENT_FOR_APPROVAL.value,
    )
    not_available = _count_status(
        records,
        "payeezz_status",
        "payeezz",
        PayeezzStatus.NOT_AVAILABLE.value,
    )
    pending = sent + not_available
    return PayeezzMetrics(
        total_members=total,
        aggregator_accepted=count_percentage(accepted, total),
        sent_for_approval=count_percentage(sent, total),
        not_available=count_percentage(not_available, total),
        pending=count_percentage(pending, total),
        completion=count_percentage(accepted, total),
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
    not_verified = _count_status(
        records,
        canonical_name,
        frontend_name,
        VerificationStatus.NOT_VERIFIED.value,
    )
    return VerificationMetrics(
        total_members=total,
        verified=count_percentage(verified, total),
        not_verified=count_percentage(not_verified, total),
        completion=count_percentage(verified, total),
        pending=count_percentage(not_verified, total),
    )


def mobile_verification_counts(members: Iterable[Any]) -> VerificationMetrics:
    return verification_counts(members, "mobile_status", "mobile")


def email_verification_counts(members: Iterable[Any]) -> VerificationMetrics:
    return verification_counts(members, "email_status", "email")


def nominee_verification_counts(members: Iterable[Any]) -> VerificationMetrics:
    return verification_counts(members, "nominee_status", "nominee")


def family_completion(members: Iterable[Any]) -> FamilyCompletion:
    records = _members_tuple(members)
    kyc = kyc_counts(records)
    payeezz = payeezz_counts(records)
    mobile = mobile_verification_counts(records)
    email = email_verification_counts(records)
    nominee = nominee_verification_counts(records)
    return FamilyCompletion(
        total_members=len(records),
        total_cans=len(records),
        kyc_completion=kyc.completion,
        payeezz_completion=payeezz.completion,
        mobile_verification=mobile.completion,
        email_verification=email.completion,
        nominee_verification=nominee.completion,
    )
