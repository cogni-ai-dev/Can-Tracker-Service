import unittest

from app.domain.enums import (
    ChangeSource,
    KycStatus,
    PayeezzStatus,
    ReportType,
    TaskPriority,
    TaskType,
    UserRole,
    VerificationStatus,
)


class EnumLabelTests(unittest.TestCase):
    def test_kyc_status_labels_are_canonical(self) -> None:
        self.assertEqual(KycStatus.values(), ("Validated", "Registered", "No KYC"))

    def test_verification_status_labels_are_canonical(self) -> None:
        self.assertEqual(VerificationStatus.values(), ("Verified", "Not Verified"))

    def test_payeezz_status_labels_are_canonical(self) -> None:
        self.assertEqual(
            PayeezzStatus.values(),
            ("Not Available", "Sent for Approval", "Aggregator Accepted"),
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

    def test_task_priority_values_are_api_ready(self) -> None:
        self.assertEqual(TaskPriority.values(), ("high", "medium", "low"))


if __name__ == "__main__":
    unittest.main()
