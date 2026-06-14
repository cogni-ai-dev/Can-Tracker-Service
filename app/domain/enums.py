"""Canonical enum labels shared by schemas, imports, reports, and UI adapters."""

from enum import Enum


class CanonicalStrEnum(str, Enum):
    """String enum whose value is the external domain label."""

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(item.value for item in cls)

    def __str__(self) -> str:
        return self.value


class KycStatus(CanonicalStrEnum):
    VALIDATED = "Validated"
    REGISTERED = "Registered"
    NO_KYC = "No KYC"


class VerificationStatus(CanonicalStrEnum):
    VERIFIED = "Verified"
    NOT_VERIFIED = "Not Verified"


class PayeezzStatus(CanonicalStrEnum):
    NOT_AVAILABLE = "Not Available"
    SENT_FOR_APPROVAL = "Sent for Approval"
    AGGREGATOR_ACCEPTED = "Aggregator Accepted"


class TaskType(CanonicalStrEnum):
    KYC = "kyc"
    PAYEEZZ = "payeezz"
    MOBILE = "mobile"
    EMAIL = "email"
    NOMINEE = "nominee"


class TaskPriority(CanonicalStrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReportType(CanonicalStrEnum):
    KYC_PENDING = "kyc_pending"
    PAYEEZZ_PENDING = "payeezz_pending"
    CONTACT_PENDING = "contact_pending"
    FAMILY_COMPLIANCE = "family_compliance"
    RM_TASKS = "rm_tasks"
    FULL = "full"


class ChangeSource(CanonicalStrEnum):
    MANUAL = "manual"
    IMPORT = "import"
    MFU_API = "mfu_api"
