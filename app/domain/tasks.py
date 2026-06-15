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


@dataclass(frozen=True)
class TaskRule:
    status_field: str
    frontend_field: str
    status_value: str
    type: TaskType
    priority: TaskPriority
    description: str
    label: str
    order: int


TASK_RULES: tuple[TaskRule, ...] = (
    TaskRule(
        status_field="kyc_status",
        frontend_field="kyc",
        status_value=KycStatus.NO_KYC.value,
        type=TaskType.KYC,
        priority=TaskPriority.HIGH,
        description="KYC not done",
        label="No KYC",
        order=10,
    ),
    TaskRule(
        status_field="kyc_status",
        frontend_field="kyc",
        status_value=KycStatus.REGISTERED.value,
        type=TaskType.KYC,
        priority=TaskPriority.MEDIUM,
        description="Re-KYC pending",
        label="Re-KYC",
        order=10,
    ),
    TaskRule(
        status_field="payeezz_status",
        frontend_field="payeezz",
        status_value=PayeezzStatus.NOT_AVAILABLE.value,
        type=TaskType.PAYEEZZ,
        priority=TaskPriority.HIGH,
        description="PayEezz mandate not initiated",
        label="Not Setup",
        order=20,
    ),
    TaskRule(
        status_field="payeezz_status",
        frontend_field="payeezz",
        status_value=PayeezzStatus.SENT_FOR_APPROVAL.value,
        type=TaskType.PAYEEZZ,
        priority=TaskPriority.MEDIUM,
        description="PayEezz sent, awaiting acceptance",
        label="Pending",
        order=20,
    ),
    TaskRule(
        status_field="mobile_status",
        frontend_field="mobile",
        status_value=VerificationStatus.NOT_VERIFIED.value,
        type=TaskType.MOBILE,
        priority=TaskPriority.MEDIUM,
        description="Mobile number not verified in MFU",
        label="Unverified",
        order=30,
    ),
    TaskRule(
        status_field="email_status",
        frontend_field="email",
        status_value=VerificationStatus.NOT_VERIFIED.value,
        type=TaskType.EMAIL,
        priority=TaskPriority.LOW,
        description="Email address not verified in MFU",
        label="Unverified",
        order=40,
    ),
    TaskRule(
        status_field="nominee_status",
        frontend_field="nominee",
        status_value=VerificationStatus.NOT_VERIFIED.value,
        type=TaskType.NOMINEE,
        priority=TaskPriority.MEDIUM,
        description="Nominee details not verified",
        label="Not Verified",
        order=50,
    ),
)


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
    for rule in TASK_RULES:
        if value(member, rule.status_field, rule.frontend_field, default=None) == rule.status_value:
            tasks.append(
                _make_task(
                    rule.type,
                    rule.priority,
                    member,
                    family,
                    rule.description,
                    rule.label,
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
