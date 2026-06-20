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


class ReportExportFormat(CanonicalStrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ChangeSource(CanonicalStrEnum):
    MANUAL = "manual"
    IMPORT = "import"
    MFU_API = "mfu_api"


class ImportBatchStatus(CanonicalStrEnum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    COMMITTED = "committed"
    FAILED = "failed"


class ImportRowStatus(CanonicalStrEnum):
    VALID = "valid"
    ERROR = "error"
    CONFLICT = "conflict"
    COMMITTED = "committed"
    SKIPPED = "skipped"


class AuditEntityType(CanonicalStrEnum):
    FAMILY = "family"
    MEMBER = "member"
    USER = "user"
    IMPORT_BATCH = "import_batch"


class AuditAction(CanonicalStrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    SENSITIVE_READ = "sensitive_read"
    IMPORT_COMMIT = "import_commit"


class UserRole(CanonicalStrEnum):
    ADMIN = "admin"
    OPS = "ops"
    RM = "rm"
    MANAGEMENT = "management"


class ModuleCode(CanonicalStrEnum):
    CAN_COMPLIANCE = "can_compliance"
    CLIENT_CRM = "client_crm"


class ModuleRole(CanonicalStrEnum):
    CAN_ADMIN = "can_admin"
    CAN_OPS = "can_ops"
    CAN_RM = "can_rm"
    CAN_MANAGEMENT = "can_management"
    CRM_ADMIN = "crm_admin"
    CRM_OPS = "crm_ops"
    CRM_RELATIONSHIP_MANAGER = "crm_relationship_manager"
    CRM_VIEWER = "crm_viewer"
