import unittest

from app.domain.compliance import (
    email_verification_counts,
    family_completion,
    kyc_counts,
    mobile_verification_counts,
    nominee_verification_counts,
    payeezz_counts,
    percentage,
)


def member(
    kyc: str = "Verified",
    payeezz: str = "Approved",
    mobile: str = "Verified",
    email: str = "Verified",
    nominee: str = "Verified",
    can_number: str | None = "CAN-001",
    can_status: str = "Available",
) -> dict[str, object]:
    return {
        "can_number": can_number,
        "can_status": can_status,
        "kyc_status": kyc,
        "payeezz_mandate_status": payeezz,
        "mobile_verification_status": mobile,
        "email_verification_status": email,
        "nominee_verification_status": nominee,
    }


class PercentageTests(unittest.TestCase):
    def test_zero_denominator_returns_zero(self) -> None:
        self.assertEqual(percentage(0, 0), 0)
        self.assertEqual(percentage(10, 0), 0)

    def test_rounds_to_nearest_whole_number(self) -> None:
        self.assertEqual(percentage(1, 3), 33)
        self.assertEqual(percentage(2, 3), 67)
        self.assertEqual(percentage(1, 200), 1)

    def test_full_completion_is_one_hundred(self) -> None:
        self.assertEqual(percentage(4, 4), 100)


class ComplianceMetricTests(unittest.TestCase):
    def test_kyc_counts_pending_and_completion(self) -> None:
        metrics = kyc_counts(
            [
                member(kyc="Verified"),
                member(kyc="Verified"),
                member(kyc="Pending Re-KYC"),
                member(kyc="Not Started"),
            ]
        )

        self.assertEqual(metrics.total_members, 4)
        self.assertEqual(metrics.verified.count, 2)
        self.assertEqual(metrics.verified.percentage, 50)
        self.assertEqual(metrics.pending_rekyc.count, 1)
        self.assertEqual(metrics.not_started.count, 1)
        self.assertEqual(metrics.pending.count, 2)
        self.assertEqual(metrics.pending.percentage, 50)
        self.assertEqual(metrics.completion.count, 2)
        self.assertEqual(metrics.completion.percentage, 50)

    def test_deleted_members_are_excluded_from_metrics(self) -> None:
        deleted_pending = {**member(kyc="Not Started"), "deleted_at": "2026-01-01T00:00:00Z"}

        metrics = kyc_counts([member(kyc="Verified"), deleted_pending])

        self.assertEqual(metrics.total_members, 1)
        self.assertEqual(metrics.verified.count, 1)
        self.assertEqual(metrics.pending.count, 0)

    def test_payeezz_counts_pending_and_completion(self) -> None:
        metrics = payeezz_counts(
            [
                member(payeezz="Approved"),
                member(payeezz="Pending Approval"),
                member(payeezz="Not Started"),
                member(payeezz="Not Started"),
            ]
        )

        self.assertEqual(metrics.total_members, 4)
        self.assertEqual(metrics.approved.count, 1)
        self.assertEqual(metrics.approved.percentage, 25)
        self.assertEqual(metrics.pending_approval.count, 1)
        self.assertEqual(metrics.not_started.count, 2)
        self.assertEqual(metrics.pending.count, 3)
        self.assertEqual(metrics.pending.percentage, 75)
        self.assertEqual(metrics.completion.count, 1)

    def test_mobile_verification_counts(self) -> None:
        metrics = mobile_verification_counts(
            [member(mobile="Verified"), member(mobile="Pending Verification"), member(mobile="Pending Verification")]
        )

        self.assertEqual(metrics.verified.count, 1)
        self.assertEqual(metrics.verified.percentage, 33)
        self.assertEqual(metrics.pending_verification.count, 2)
        self.assertEqual(metrics.pending.percentage, 67)

    def test_email_verification_counts(self) -> None:
        metrics = email_verification_counts(
            [member(email="Verified"), member(email="Verified"), member(email="Pending Verification")]
        )

        self.assertEqual(metrics.verified.count, 2)
        self.assertEqual(metrics.completion.percentage, 67)
        self.assertEqual(metrics.pending_verification.count, 1)

    def test_nominee_verification_counts(self) -> None:
        metrics = nominee_verification_counts(
            [
                member(nominee="Verified"),
                member(nominee="Pending Verification"),
                member(nominee="Pending Verification"),
                member(nominee="Pending Verification"),
            ]
        )

        self.assertEqual(metrics.verified.count, 1)
        self.assertEqual(metrics.completion.percentage, 25)
        self.assertEqual(metrics.pending.count, 3)

    def test_family_completion_percentages(self) -> None:
        completion = family_completion(
            [
                member(),
                member(email="Pending Verification", nominee="Pending Verification", payeezz="Pending Approval"),
                member(
                    kyc="Not Started",
                    mobile="Pending Verification",
                    email="Pending Verification",
                    nominee="Pending Verification",
                    payeezz="Not Started",
                ),
            ]
        )

        self.assertEqual(completion.total_members, 3)
        self.assertEqual(completion.total_cans, 3)
        self.assertEqual(completion.kyc_completion.count, 2)
        self.assertEqual(completion.kyc_completion_pct, 67)
        self.assertEqual(completion.payeezz_completion_pct, 33)
        self.assertEqual(completion.mobile_verification_pct, 67)
        self.assertEqual(completion.email_verification_pct, 33)
        self.assertEqual(completion.nominee_verification_pct, 33)

    def test_zero_member_family_completion_returns_zeroes(self) -> None:
        completion = family_completion([])

        self.assertEqual(completion.total_members, 0)
        self.assertEqual(completion.total_cans, 0)
        self.assertEqual(completion.kyc_completion_pct, 0)
        self.assertEqual(completion.payeezz_completion_pct, 0)
        self.assertEqual(completion.mobile_verification_pct, 0)
        self.assertEqual(completion.email_verification_pct, 0)
        self.assertEqual(completion.nominee_verification_pct, 0)

    def test_family_completion_counts_only_available_cans(self) -> None:
        completion = family_completion(
            [
                member(can_number="CAN-1", can_status="Available"),
                member(can_number=None, can_status="Pending"),
                member(can_number="CAN-2", can_status="Available"),
            ]
        )

        self.assertEqual(completion.total_members, 3)
        self.assertEqual(completion.total_cans, 2)


if __name__ == "__main__":
    unittest.main()
