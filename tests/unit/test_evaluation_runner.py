from __future__ import annotations

import unittest
from dataclasses import dataclass

from tests.evaluation_runner import evaluate_label_agreement, load_fixture


@dataclass(frozen=True)
class FakeJudgment:
    label: str


class FixtureLabelJudge:
    def __init__(self, labels: dict[str, str]) -> None:
        self.labels = labels
        self.requests = []

    def judge(self, request):
        self.requests.append(request)
        return FakeJudgment(self.labels[request.transaction_id])


class EvaluationRunnerTests(unittest.TestCase):
    def test_computes_label_agreement_from_versioned_fixture_without_live_claim(self) -> None:
        fixture = load_fixture("tests/fixtures/judgment_scenarios_v1.json")
        labels = {
            case["case_id"]: case["expected_label"]
            for case in fixture["cases"]
        }
        judge = FixtureLabelJudge(labels)

        report = evaluate_label_agreement(fixture, judge)

        self.assertEqual(report.fixture_version, 1)
        self.assertEqual(report.policy_version, "overspending-v1")
        self.assertEqual(report.total, 10)
        self.assertEqual(report.matches, 10)
        self.assertEqual(report.agreement, 1.0)
        self.assertFalse(report.live_model_used)
        self.assertEqual(len(judge.requests), 10)

    def test_agreement_drops_for_mismatched_fake_judge(self) -> None:
        fixture = load_fixture("tests/fixtures/judgment_scenarios_v1.json")
        labels = {
            case["case_id"]: case["expected_label"]
            for case in fixture["cases"]
        }
        labels[fixture["cases"][0]["case_id"]] = "overspending"

        report = evaluate_label_agreement(fixture, FixtureLabelJudge(labels))

        self.assertEqual(report.matches, 9)
        self.assertEqual(report.agreement, 0.9)
        self.assertFalse(report.live_model_used)


if __name__ == "__main__":
    unittest.main()
