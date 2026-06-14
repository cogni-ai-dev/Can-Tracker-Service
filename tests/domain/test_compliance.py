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
    kyc: str = "Validated",
    payeezz: str = "Aggregator Accepted",
    mobile: str = "Verified",
    email: str = "Verified",
    nominee: str = "Verified",
) -> dict[str, str]:
    return {
        "kyc_status": kyc,
        "payeezz_status": payeezz,
        "mobile_status": mobile,
        "email_status": email,
        "nominee_status": nominee,
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
                member(kyc="Validated"),
                member(kyc="Validated"),
                member(kyc="Registered"),
                member(kyc="No KYC"),
            ]
        )

        self.assertEqual(metrics.total_members, 4)
        self.assertEqual(metrics.validated.count, 2)
        self.assertEqual(metrics.validated.percentage, 50)
        self.assertEqual(metrics.registered.count, 1)
        self.assertEqual(metrics.no_kyc.count, 1)
        self.assertEqual(metrics.pending.count, 2)
        self.assertEqual(metrics.pending.percentage, 50)
        self.assertEqual(metrics.completion.count, 2)
        self.assertEqual(metrics.completion.percentage, 50)

    def test_deleted_members_are_excluded_from_metrics(self) -> None:
        deleted_pending = {**member(kyc="No KYC"), "deleted_at": "2026-01-01T00:00:00Z"}

        metrics = kyc_counts([member(kyc="Validated"), deleted_pending])

        self.assertEqual(metrics.total_members, 1)
        self.assertEqual(metrics.validated.count, 1)
        self.assertEqual(metrics.pending.count, 0)

    def test_payeezz_counts_pending_and_completion(self) -> None:
        metrics = payeezz_counts(
            [
                member(payeezz="Aggregator Accepted"),
                member(payeezz="Sent for Approval"),
                member(payeezz="Not Available"),
                member(payeezz="Not Available"),
            ]
        )

        self.assertEqual(metrics.total_members, 4)
        self.assertEqual(metrics.aggregator_accepted.count, 1)
        self.assertEqual(metrics.aggregator_accepted.percentage, 25)
        self.assertEqual(metrics.sent_for_approval.count, 1)
        self.assertEqual(metrics.not_available.count, 2)
        self.assertEqual(metrics.pending.count, 3)
        self.assertEqual(metrics.pending.percentage, 75)
        self.assertEqual(metrics.completion.count, 1)

    def test_mobile_verification_counts(self) -> None:
        metrics = mobile_verification_counts(
            [member(mobile="Verified"), member(mobile="Not Verified"), member(mobile="Not Verified")]
        )

        self.assertEqual(metrics.verified.count, 1)
        self.assertEqual(metrics.verified.percentage, 33)
        self.assertEqual(metrics.not_verified.count, 2)
        self.assertEqual(metrics.pending.percentage, 67)

    def test_email_verification_counts(self) -> None:
        metrics = email_verification_counts(
            [member(email="Verified"), member(email="Verified"), member(email="Not Verified")]
        )

        self.assertEqual(metrics.verified.count, 2)
        self.assertEqual(metrics.completion.percentage, 67)
        self.assertEqual(metrics.not_verified.count, 1)

    def test_nominee_verification_counts(self) -> None:
        metrics = nominee_verification_counts(
            [
                member(nominee="Verified"),
                member(nominee="Not Verified"),
                member(nominee="Not Verified"),
                member(nominee="Not Verified"),
            ]
        )

        self.assertEqual(metrics.verified.count, 1)
        self.assertEqual(metrics.completion.percentage, 25)
        self.assertEqual(metrics.pending.count, 3)

    def test_family_completion_percentages(self) -> None:
        completion = family_completion(
            [
                member(),
                member(email="Not Verified", nominee="Not Verified", payeezz="Sent for Approval"),
                member(
                    kyc="No KYC",
                    mobile="Not Verified",
                    email="Not Verified",
                    nominee="Not Verified",
                    payeezz="Not Available",
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


if __name__ == "__main__":
    unittest.main()
