"""Computed pending task generation from current member status fields."""

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any

from app.domain.enums import KycStatus, PayeezzStatus, TaskPriority, TaskType, VerificationStatus
from app.domain.records import active, family_lookup, value


@dataclass(frozen=True)
class ComputedTask:
    type: str
    priority: str
    member_id: Any
    member_name: str
    family_id: Any
    family_head_name: str
    family_code: str
    rm_id: Any
    rm_name: str
    can_number_masked: str
    description: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def mask_can_number(can_number: Any) -> str:
    value_text = "" if can_number is None else str(can_number)
    return value_text[-6:]


def _task_context(member: Any, family: Any | None) -> dict[str, Any]:
    family_id = value(member, "family_id", "fid", default=None)
    if family_id is None and family is not None:
        family_id = value(family, "id", "family_id", default=None)
    return {
        "member_id": value(member, "member_id", "id", default=None),
        "member_name": value(member, "member_name", "name", default=""),
        "family_id": family_id,
        "family_head_name": value(
            member,
            "family_head_name",
            "family_head",
            "fam",
            default=value(family, "family_head_name", "head", default="") if family is not None else "",
        ),
        "family_code": value(
            member,
            "family_code",
            default=value(family, "family_code", "code", default="") if family is not None else "",
        ),
        "rm_id": value(
            member,
            "rm_id",
            "primary_rm_id",
            default=value(family, "rm_id", "primary_rm_id", default=None) if family is not None else None,
        ),
        "rm_name": value(
            member,
            "rm_name",
            "primary_rm_name",
            "rm",
            default=value(family, "rm_name", "primary_rm_name", "rm", default="") if family is not None else "",
        ),
        "can_number_masked": mask_can_number(value(member, "can_number", "can", default="")),
    }


def _make_task(
    task_type: TaskType,
    priority: TaskPriority,
    member: Any,
    family: Any | None,
    description: str,
    label: str,
) -> ComputedTask:
    return ComputedTask(
        type=task_type.value,
        priority=priority.value,
        description=description,
        label=label,
        **_task_context(member, family),
    )


def generate_member_tasks(member: Any, family: Any | None = None) -> tuple[ComputedTask, ...]:
    if not active(member):
        return ()

    tasks: list[ComputedTask] = []
    kyc_status = value(member, "kyc_status", "kyc", default=None)
    payeezz_status = value(member, "payeezz_status", "payeezz", default=None)
    mobile_status = value(member, "mobile_status", "mobile", default=None)
    email_status = value(member, "email_status", "email", default=None)
    nominee_status = value(member, "nominee_status", "nominee", default=None)

    if kyc_status == KycStatus.NO_KYC.value:
        tasks.append(
            _make_task(
                TaskType.KYC,
                TaskPriority.HIGH,
                member,
                family,
                "KYC not done",
                "No KYC",
            )
        )
    elif kyc_status == KycStatus.REGISTERED.value:
        tasks.append(
            _make_task(
                TaskType.KYC,
                TaskPriority.MEDIUM,
                member,
                family,
                "Re-KYC pending",
                "Re-KYC",
            )
        )

    if payeezz_status == PayeezzStatus.NOT_AVAILABLE.value:
        tasks.append(
            _make_task(
                TaskType.PAYEEZZ,
                TaskPriority.HIGH,
                member,
                family,
                "PayEezz mandate not initiated",
                "Not Setup",
            )
        )
    elif payeezz_status == PayeezzStatus.SENT_FOR_APPROVAL.value:
        tasks.append(
            _make_task(
                TaskType.PAYEEZZ,
                TaskPriority.MEDIUM,
                member,
                family,
                "PayEezz sent, awaiting acceptance",
                "Pending",
            )
        )

    if mobile_status == VerificationStatus.NOT_VERIFIED.value:
        tasks.append(
            _make_task(
                TaskType.MOBILE,
                TaskPriority.MEDIUM,
                member,
                family,
                "Mobile number not verified in MFU",
                "Unverified",
            )
        )
    if email_status == VerificationStatus.NOT_VERIFIED.value:
        tasks.append(
            _make_task(
                TaskType.EMAIL,
                TaskPriority.LOW,
                member,
                family,
                "Email address not verified in MFU",
                "Unverified",
            )
        )
    if nominee_status == VerificationStatus.NOT_VERIFIED.value:
        tasks.append(
            _make_task(
                TaskType.NOMINEE,
                TaskPriority.MEDIUM,
                member,
                family,
                "Nominee details not verified",
                "Not Verified",
            )
        )

    return tuple(tasks)


def generate_tasks(
    members: Iterable[Any],
    families: Mapping[Any, Any] | Iterable[Any] | None = None,
) -> tuple[ComputedTask, ...]:
    families_by_id = family_lookup(families)
    tasks: list[ComputedTask] = []
    for member in members:
        family_id = value(member, "family_id", "fid", default=None)
        tasks.extend(generate_member_tasks(member, families_by_id.get(family_id)))
    return tuple(tasks)
