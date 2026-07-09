import unittest

from app.domain.reports import REPORT_DEFINITIONS, build_report_rows, filter_report_records, get_report_definition


def active_member(member_id: str, **overrides: str) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "id": member_id,
        "name": member_id,
        "family_code": "FAM-001",
        "kyc_status": "Verified",
        "payeezz_mandate_status": "Approved",
        "mobile_verification_status": "Verified",
        "email_verification_status": "Verified",
        "nominee_verification_status": "Verified",
        "deleted_at": None,
    }
    base.update(overrides)
    return base


class ReportDefinitionTests(unittest.TestCase):
    def test_all_report_types_have_metadata(self) -> None:
        self.assertEqual(
            tuple(REPORT_DEFINITIONS),
            (
                "kyc_pending",
                "payeezz_pending",
                "contact_pending",
                "family_compliance",
                "rm_tasks",
                "full",
            ),
        )

    def test_kyc_pending_columns_match_plan(self) -> None:
        self.assertEqual(
            [column.key for column in get_report_definition("kyc_pending").columns],
            [
                "name",
                "can_number",
                "can_status",
                "pan_masked",
                "kyc_status",
                "family_head_name",
                "family_code",
                "rm_name",
                "last_updated_at",
            ],
        )

    def test_payeezz_pending_columns_match_plan(self) -> None:
        self.assertEqual(
            [column.key for column in get_report_definition("payeezz_pending").columns],
            [
                "name",
                "can_number",
                "can_status",
                "payeezz_mandate_status",
                "bank_name",
                "bank_account_number_masked",
                "family_head_name",
                "family_code",
                "rm_name",
            ],
        )

    def test_contact_pending_columns_match_plan(self) -> None:
        self.assertEqual(
            [column.key for column in get_report_definition("contact_pending").columns],
            [
                "name",
                "can_number",
                "can_status",
                "mobile_verification_status",
                "email_verification_status",
                "nominee_verification_status",
                "family_head_name",
                "family_code",
                "rm_name",
            ],
        )

    def test_family_compliance_columns_match_plan(self) -> None:
        self.assertEqual(
            [column.key for column in get_report_definition("family_compliance").columns],
            [
                "family_head_name",
                "family_code",
                "rm_name",
                "members",
                "kyc_percentage",
                "payeezz_percentage",
                "mobile_percentage",
                "email_percentage",
                "nominee_percentage",
            ],
        )

    def test_rm_tasks_columns_match_plan(self) -> None:
        self.assertEqual(
            [column.key for column in get_report_definition("rm_tasks").columns],
            [
                "rm_name",
                "kyc_count",
                "payeezz_count",
                "mobile_count",
                "email_count",
                "nominee_count",
                "total",
            ],
        )

    def test_full_columns_match_plan(self) -> None:
        self.assertEqual(
            [column.key for column in get_report_definition("full").columns],
            [
                "name",
                "can_number",
                "can_status",
                "pan_masked",
                "date_of_birth",
                "kyc_status",
                "mobile_verification_status",
                "email_verification_status",
                "nominee_verification_status",
                "payeezz_mandate_status",
                "bank_name",
                "ifsc_code",
                "family_head_name",
                "family_code",
                "rm_name",
                "last_updated_at",
            ],
        )


class ReportFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.members = [
            active_member("valid"),
            active_member("registered", kyc_status="Pending Re-KYC"),
            active_member("no-kyc", kyc_status="Not Started"),
            active_member("sent", payeezz_mandate_status="Pending Approval"),
            active_member("not-available", payeezz_mandate_status="Not Started"),
            active_member("mobile", mobile_verification_status="Pending Verification"),
            active_member("email", email_verification_status="Pending Verification"),
            active_member("nominee", nominee_verification_status="Pending Verification"),
            active_member(
                "deleted",
                kyc_status="Not Started",
                payeezz_mandate_status="Not Started",
                mobile_verification_status="Pending Verification",
                deleted_at="2026-01-01T00:00:00Z",
            ),
        ]

    def test_kyc_pending_filter_includes_registered_and_no_kyc_only(self) -> None:
        rows = filter_report_records("kyc_pending", self.members)

        self.assertEqual([row["id"] for row in rows], ["registered", "no-kyc"])

    def test_payeezz_pending_filter_includes_not_accepted_only(self) -> None:
        rows = filter_report_records("payeezz_pending", self.members)

        self.assertEqual([row["id"] for row in rows], ["sent", "not-available"])

    def test_contact_pending_filter_includes_mobile_email_or_nominee_pending(self) -> None:
        rows = filter_report_records("contact_pending", self.members)

        self.assertEqual([row["id"] for row in rows], ["mobile", "email", "nominee"])

    def test_family_compliance_filter_includes_active_families(self) -> None:
        families = [
            {"id": "F001", "family_code": "FAM-001", "deleted_at": None},
            {"id": "F002", "family_code": "FAM-002", "deleted_at": "2026-01-01T00:00:00Z"},
        ]

        rows = filter_report_records("family_compliance", families)

        self.assertEqual([row["id"] for row in rows], ["F001"])

    def test_rm_tasks_filter_includes_known_task_types(self) -> None:
        tasks = [
            {"type": "kyc", "rm_name": "Priya Sharma"},
            {"type": "payeezz", "rm_name": "Priya Sharma"},
            {"type": "mobile", "rm_name": "Rohit Mehra"},
            {"type": "email", "rm_name": "Rohit Mehra"},
            {"type": "nominee", "rm_name": "Rohit Mehra"},
            {"type": "unknown", "rm_name": "Unknown"},
        ]

        rows = filter_report_records("rm_tasks", tasks)

        self.assertEqual([row["type"] for row in rows], ["kyc", "payeezz", "mobile", "email", "nominee"])

    def test_rm_tasks_rows_are_grouped_by_rm_with_type_counts(self) -> None:
        tasks = [
            {"type": "kyc", "rm_name": "Priya Sharma"},
            {"type": "payeezz", "rm_name": "Priya Sharma"},
            {"type": "email", "rm_name": "Priya Sharma"},
            {"type": "payeezz", "rm_name": "Rohit Mehra"},
            {"type": "mobile", "rm_name": "Rohit Mehra"},
            {"type": "nominee", "rm_name": "Rohit Mehra"},
            {"type": "unknown", "rm_name": "Rohit Mehra"},
        ]

        rows = build_report_rows("rm_tasks", tasks)

        self.assertEqual(
            rows,
            (
                {
                    "rm_name": "Priya Sharma",
                    "kyc_count": 1,
                    "payeezz_count": 1,
                    "mobile_count": 0,
                    "email_count": 1,
                    "nominee_count": 0,
                    "total": 3,
                },
                {
                    "rm_name": "Rohit Mehra",
                    "kyc_count": 0,
                    "payeezz_count": 1,
                    "mobile_count": 1,
                    "email_count": 0,
                    "nominee_count": 1,
                    "total": 3,
                },
            ),
        )

    def test_full_filter_includes_all_active_members(self) -> None:
        rows = filter_report_records("full", self.members)

        self.assertEqual([row["id"] for row in rows], [member["id"] for member in self.members[:-1]])


if __name__ == "__main__":
    unittest.main()
