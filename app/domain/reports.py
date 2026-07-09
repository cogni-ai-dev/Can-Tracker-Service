"""Report definition metadata and report-scope filters."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Literal

from app.domain.compliance import payeezz_status
from app.domain.enums import KycStatus, PayeezzStatus, ReportType, TaskType, VerificationStatus
from app.domain.records import active, value

ReportScope = Literal["members", "families", "tasks"]


@dataclass(frozen=True)
class ReportColumn:
    key: str
    label: str


@dataclass(frozen=True)
class ReportDefinition:
    report_type: str
    title: str
    description: str
    scope: ReportScope
    filter_name: str
    columns: tuple[ReportColumn, ...]
    sort_by: tuple[str, ...]
    filter_fn: Callable[[Any], bool]


def kyc_pending_filter(member: Any) -> bool:
    return active(member) and value(member, "kyc_status", "kyc") != KycStatus.VERIFIED.value


def payeezz_pending_filter(member: Any) -> bool:
    return active(member) and payeezz_status(member) != PayeezzStatus.APPROVED.value


def contact_pending_filter(member: Any) -> bool:
    if not active(member):
        return False
    return (
        value(member, "mobile_verification_status", "mobile") == VerificationStatus.PENDING_VERIFICATION.value
        or value(member, "email_verification_status", "email") == VerificationStatus.PENDING_VERIFICATION.value
        or value(member, "nominee_verification_status", "nominee") == VerificationStatus.PENDING_VERIFICATION.value
    )


def active_record_filter(record: Any) -> bool:
    return active(record)


def task_record_filter(task: Any) -> bool:
    return value(task, "type") in TaskType.values()


def rm_task_report_rows(tasks: Iterable[Any]) -> tuple[dict[str, Any], ...]:
    grouped: dict[str, dict[str, Any]] = {}
    count_keys = {
        TaskType.KYC.value: "kyc_count",
        TaskType.PAYEEZZ.value: "payeezz_count",
        TaskType.MOBILE.value: "mobile_count",
        TaskType.EMAIL.value: "email_count",
        TaskType.NOMINEE.value: "nominee_count",
    }

    for task in tasks:
        task_type = value(task, "type", default=None)
        if task_type not in count_keys:
            continue
        rm_name = value(task, "rm_name", "rm", default="-") or "-"
        row = grouped.setdefault(
            rm_name,
            {
                "rm_name": rm_name,
                "kyc_count": 0,
                "payeezz_count": 0,
                "mobile_count": 0,
                "email_count": 0,
                "nominee_count": 0,
                "total": 0,
            },
        )
        row[count_keys[task_type]] += 1
        row["total"] += 1

    return tuple(grouped[rm_name] for rm_name in sorted(grouped))


REPORT_DEFINITIONS: dict[str, ReportDefinition] = {
    ReportType.KYC_PENDING.value: ReportDefinition(
        report_type=ReportType.KYC_PENDING.value,
        title="KYC Pending Report",
        description="Active members where KYC is Pending Re-KYC or Not Started.",
        scope="members",
        filter_name="kyc_pending_filter",
        columns=(
            ReportColumn("name", "Name"),
            ReportColumn("can_number", "CAN"),
            ReportColumn("can_status", "CAN status"),
            ReportColumn("pan_masked", "PAN masked"),
            ReportColumn("kyc_status", "KYC status"),
            ReportColumn("family_head_name", "Family head"),
            ReportColumn("family_code", "Family code"),
            ReportColumn("rm_name", "RM"),
            ReportColumn("last_updated_at", "Last updated"),
        ),
        sort_by=("family_code", "name"),
        filter_fn=kyc_pending_filter,
    ),
    ReportType.PAYEEZZ_PENDING.value: ReportDefinition(
        report_type=ReportType.PAYEEZZ_PENDING.value,
        title="PayEezz Pending Report",
        description="Active members without an approved PayEezz mandate.",
        scope="members",
        filter_name="payeezz_pending_filter",
        columns=(
            ReportColumn("name", "Name"),
            ReportColumn("can_number", "CAN"),
            ReportColumn("can_status", "CAN status"),
            ReportColumn("payeezz_mandate_status", "PayEezz status"),
            ReportColumn("bank_name", "Bank name"),
            ReportColumn("bank_account_number_masked", "Account masked"),
            ReportColumn("family_head_name", "Family head"),
            ReportColumn("family_code", "Family code"),
            ReportColumn("rm_name", "RM"),
        ),
        sort_by=("family_code", "name"),
        filter_fn=payeezz_pending_filter,
    ),
    ReportType.CONTACT_PENDING.value: ReportDefinition(
        report_type=ReportType.CONTACT_PENDING.value,
        title="Contact Verification Report",
        description="Active members with unverified mobile, email, or nominee status.",
        scope="members",
        filter_name="contact_pending_filter",
        columns=(
            ReportColumn("name", "Name"),
            ReportColumn("can_number", "CAN"),
            ReportColumn("can_status", "CAN status"),
            ReportColumn("mobile_verification_status", "Mobile status"),
            ReportColumn("email_verification_status", "Email status"),
            ReportColumn("nominee_verification_status", "Nominee status"),
            ReportColumn("family_head_name", "Family head"),
            ReportColumn("family_code", "Family code"),
            ReportColumn("rm_name", "RM"),
        ),
        sort_by=("family_code", "name"),
        filter_fn=contact_pending_filter,
    ),
    ReportType.FAMILY_COMPLIANCE.value: ReportDefinition(
        report_type=ReportType.FAMILY_COMPLIANCE.value,
        title="Family-wise Compliance Report",
        description="Compliance percentages for each active family.",
        scope="families",
        filter_name="active_family_filter",
        columns=(
            ReportColumn("family_head_name", "Family head"),
            ReportColumn("family_code", "Family code"),
            ReportColumn("rm_name", "RM"),
            ReportColumn("members", "Members"),
            ReportColumn("kyc_percentage", "KYC percentage"),
            ReportColumn("payeezz_percentage", "PayEezz percentage"),
            ReportColumn("mobile_percentage", "Mobile percentage"),
            ReportColumn("email_percentage", "Email percentage"),
            ReportColumn("nominee_percentage", "Nominee percentage"),
        ),
        sort_by=("family_code",),
        filter_fn=active_record_filter,
    ),
    ReportType.RM_TASKS.value: ReportDefinition(
        report_type=ReportType.RM_TASKS.value,
        title="RM-wise Pending Tasks",
        description="Computed pending tasks grouped by relationship manager.",
        scope="tasks",
        filter_name="task_record_filter",
        columns=(
            ReportColumn("rm_name", "RM"),
            ReportColumn("kyc_count", "KYC count"),
            ReportColumn("payeezz_count", "PayEezz count"),
            ReportColumn("mobile_count", "Mobile count"),
            ReportColumn("email_count", "Email count"),
            ReportColumn("nominee_count", "Nominee count"),
            ReportColumn("total", "Total"),
        ),
        sort_by=("rm_name",),
        filter_fn=task_record_filter,
    ),
    ReportType.FULL.value: ReportDefinition(
        report_type=ReportType.FULL.value,
        title="Full CAN Database",
        description="All active member records and compliance statuses.",
        scope="members",
        filter_name="active_member_filter",
        columns=(
            ReportColumn("name", "Name"),
            ReportColumn("can_number", "CAN"),
            ReportColumn("can_status", "CAN status"),
            ReportColumn("pan_masked", "PAN masked"),
            ReportColumn("date_of_birth", "DOB"),
            ReportColumn("kyc_status", "KYC"),
            ReportColumn("mobile_verification_status", "Mobile status"),
            ReportColumn("email_verification_status", "Email status"),
            ReportColumn("nominee_verification_status", "Nominee status"),
            ReportColumn("payeezz_mandate_status", "PayEezz"),
            ReportColumn("bank_name", "Bank name"),
            ReportColumn("ifsc_code", "IFSC"),
            ReportColumn("family_head_name", "Family head"),
            ReportColumn("family_code", "Family code"),
            ReportColumn("rm_name", "RM"),
            ReportColumn("last_updated_at", "Last updated"),
        ),
        sort_by=("family_code", "name"),
        filter_fn=active_record_filter,
    ),
}


def get_report_definition(report_type: str | ReportType) -> ReportDefinition:
    key = report_type.value if isinstance(report_type, ReportType) else report_type
    return REPORT_DEFINITIONS[key]


def filter_report_records(report_type: str | ReportType, records: Iterable[Any]) -> tuple[Any, ...]:
    definition = get_report_definition(report_type)
    return tuple(record for record in records if definition.filter_fn(record))


def build_report_rows(report_type: str | ReportType, records: Iterable[Any]) -> tuple[Any, ...]:
    key = report_type.value if isinstance(report_type, ReportType) else report_type
    if key == ReportType.RM_TASKS.value:
        return rm_task_report_rows(records)
    return filter_report_records(key, records)
