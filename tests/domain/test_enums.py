import unittest

from app.domain.enums import (
    CanStatus,
    ChangeSource,
    KycStatus,
    ModuleCode,
    ModuleRole,
    PayeezzStatus,
    ReportType,
    TaskPriority,
    TaskType,
    UserRole,
    VerificationStatus,
)


class EnumLabelTests(unittest.TestCase):
    def test_can_status_labels_are_canonical(self) -> None:
        self.assertEqual(CanStatus.values(), ("Pending", "Available"))

    def test_kyc_status_labels_are_canonical(self) -> None:
        self.assertEqual(KycStatus.values(), ("Not Started", "Pending Re-KYC", "Verified"))

    def test_verification_status_labels_are_canonical(self) -> None:
        self.assertEqual(VerificationStatus.values(), ("Pending Verification", "Verified"))

    def test_payeezz_mandate_status_labels_are_canonical(self) -> None:
        self.assertEqual(
            PayeezzStatus.values(),
            ("Not Started", "Pending Approval", "Approved"),
        )

    def test_task_type_labels_are_canonical(self) -> None:
        self.assertEqual(TaskType.values(), ("kyc", "payeezz", "mobile", "email", "nominee"))

    def test_report_type_labels_are_canonical(self) -> None:
        self.assertEqual(
            ReportType.values(),
            (
                "kyc_pending",
                "payeezz_pending",
                "contact_pending",
                "family_compliance",
                "rm_tasks",
                "full",
            ),
        )

    def test_change_source_labels_are_canonical(self) -> None:
        self.assertEqual(ChangeSource.values(), ("manual", "import", "mfu_api"))

    def test_user_role_values_are_api_ready(self) -> None:
        self.assertEqual(UserRole.values(), ("admin", "ops", "rm", "management"))

    def test_module_code_values_are_api_ready(self) -> None:
        self.assertEqual(ModuleCode.values(), ("can_compliance", "client_crm"))

    def test_module_role_values_are_api_ready(self) -> None:
        self.assertEqual(
            ModuleRole.values(),
            (
                "can_admin",
                "can_ops",
                "can_rm",
                "can_management",
                "crm_admin",
                "crm_ops",
                "crm_relationship_manager",
                "crm_viewer",
            ),
        )

    def test_task_priority_values_are_api_ready(self) -> None:
        self.assertEqual(TaskPriority.values(), ("high", "medium", "low"))


if __name__ == "__main__":
    unittest.main()
