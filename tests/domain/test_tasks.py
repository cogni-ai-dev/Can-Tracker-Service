import unittest
from types import SimpleNamespace

from app.domain.tasks import generate_member_tasks, generate_tasks, mask_can_number

BASE_MEMBER = {
    "id": "member-1",
    "family_id": "family-1",
    "name": "Ravi Agarwal",
    "can_number": "1100000000000003",
    "kyc_status": "Validated",
    "mobile_status": "Verified",
    "email_status": "Verified",
    "nominee_status": "Verified",
    "payeezz_status": "Aggregator Accepted",
}

BASE_FAMILY = {
    "id": "family-1",
    "family_head_name": "Ramesh Kumar Agarwal",
    "family_code": "FAM-001",
    "primary_rm_id": "rm-1",
    "rm_name": "Priya Sharma",
}


class TaskGenerationTests(unittest.TestCase):
    def test_mask_can_number_uses_only_last_six_characters(self) -> None:
        self.assertEqual(mask_can_number("1100000000000003"), "000003")
        self.assertEqual(mask_can_number("123"), "123")

    def test_no_task_for_fully_compliant_member(self) -> None:
        self.assertEqual(generate_member_tasks(BASE_MEMBER, BASE_FAMILY), ())

    def test_no_task_for_deleted_member(self) -> None:
        deleted_member = {
            **BASE_MEMBER,
            "kyc_status": "No KYC",
            "payeezz_status": "Not Available",
            "deleted_at": "2026-01-01T00:00:00Z",
        }

        self.assertEqual(generate_member_tasks(deleted_member, BASE_FAMILY), ())

    def test_no_kyc_generates_high_priority_kyc_task(self) -> None:
        task = generate_member_tasks({**BASE_MEMBER, "kyc_status": "No KYC"}, BASE_FAMILY)[0]

        self.assertEqual(task.type, "kyc")
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.description, "KYC not done")
        self.assertEqual(task.label, "No KYC")
        self.assertEqual(task.member_id, "member-1")
        self.assertEqual(task.member_name, "Ravi Agarwal")
        self.assertEqual(task.family_id, "family-1")
        self.assertEqual(task.family_head_name, "Ramesh Kumar Agarwal")
        self.assertEqual(task.family_code, "FAM-001")
        self.assertEqual(task.rm_id, "rm-1")
        self.assertEqual(task.rm_name, "Priya Sharma")
        self.assertEqual(task.can_number_masked, "000003")

    def test_registered_generates_medium_priority_re_kyc_task(self) -> None:
        task = generate_member_tasks({**BASE_MEMBER, "kyc_status": "Registered"}, BASE_FAMILY)[0]

        self.assertEqual(task.type, "kyc")
        self.assertEqual(task.priority, "medium")
        self.assertEqual(task.description, "Re-KYC pending")
        self.assertEqual(task.label, "Re-KYC")

    def test_payeezz_not_available_generates_high_priority_task(self) -> None:
        task = generate_member_tasks({**BASE_MEMBER, "payeezz_status": "Not Available"}, BASE_FAMILY)[0]

        self.assertEqual(task.type, "payeezz")
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.description, "PayEezz mandate not initiated")
        self.assertEqual(task.label, "Not Setup")

    def test_payeezz_sent_generates_medium_priority_task(self) -> None:
        task = generate_member_tasks({**BASE_MEMBER, "payeezz_status": "Sent for Approval"}, BASE_FAMILY)[0]

        self.assertEqual(task.type, "payeezz")
        self.assertEqual(task.priority, "medium")
        self.assertEqual(task.description, "PayEezz sent, awaiting acceptance")
        self.assertEqual(task.label, "Pending")

    def test_verification_tasks_are_generated_with_expected_priorities(self) -> None:
        tasks = generate_member_tasks(
            {
                **BASE_MEMBER,
                "mobile_status": "Not Verified",
                "email_status": "Not Verified",
                "nominee_status": "Not Verified",
            },
            BASE_FAMILY,
        )

        self.assertEqual([task.type for task in tasks], ["mobile", "email", "nominee"])
        self.assertEqual([task.priority for task in tasks], ["medium", "low", "medium"])
        self.assertEqual([task.label for task in tasks], ["Unverified", "Unverified", "Not Verified"])
        self.assertEqual(
            [task.description for task in tasks],
            [
                "Mobile number not verified in MFU",
                "Email address not verified in MFU",
                "Nominee details not verified",
            ],
        )

    def test_generate_tasks_uses_family_mapping_and_frontend_field_aliases(self) -> None:
        member = {
            "id": "M0003",
            "fid": "F001",
            "name": "Ravi Agarwal",
            "can": "1100000000000003",
            "kyc": "Registered",
            "mobile": "Verified",
            "email": "Verified",
            "nominee": "Verified",
            "payeezz": "Aggregator Accepted",
        }
        family = {"id": "F001", "head": "Ramesh Kumar Agarwal", "code": "FAM-001", "rm": "Priya Sharma"}

        task = generate_tasks([member], [family])[0]

        self.assertEqual(task.member_id, "M0003")
        self.assertEqual(task.family_id, "F001")
        self.assertEqual(task.family_head_name, "Ramesh Kumar Agarwal")
        self.assertEqual(task.family_code, "FAM-001")
        self.assertEqual(task.rm_name, "Priya Sharma")

    def test_member_like_objects_are_supported(self) -> None:
        member = SimpleNamespace(**{**BASE_MEMBER, "kyc_status": "No KYC"})
        family = SimpleNamespace(**BASE_FAMILY)

        task = generate_member_tasks(member, family)[0]

        self.assertEqual(task.type, "kyc")
        self.assertEqual(task.family_code, "FAM-001")


if __name__ == "__main__":
    unittest.main()
