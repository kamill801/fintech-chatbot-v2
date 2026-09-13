from __future__ import annotations

import json
import unittest
from dataclasses import dataclass

from ledger.adapters.openai_planner import (
    OpenAIResponsesPlanAdvisor,
    PlanAdviceRequest,
)


VALID_NARRATIVE = {
    "headline": "생활비 흐름이 안정적이에요.",
    "explanation": "입력된 지출과 예약을 함께 살폈어요.",
    "segment_focuses": [
        {"allocation_id": "segment-1", "focus": "약속 전에 예약을 확인하세요."}
    ],
    "next_action": "다음 지출 전에 현재 구간을 확인하세요.",
    "assumptions": ["입력된 거래가 최신 상태라고 가정했어요."],
    "confidence": "medium",
}


class FakeResponses:
    def __init__(self, outputs: list[object]) -> None:
        self.outputs = outputs
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return {"output_text": json.dumps(output, ensure_ascii=False)}


@dataclass
class FakeClient:
    responses: FakeResponses


def advice_request() -> PlanAdviceRequest:
    return PlanAdviceRequest(
        period_start="2026-09-01",
        period_end="2026-09-30",
        confirmed_budget_krw=300_000,
        deterministic_progress={
            "actual_spent_krw": 50_000,
            "reserved_remaining_krw": 100_000,
            "total_remaining_krw": 250_000,
            "flexible_remaining_krw": 150_000,
            "shortfall_krw": 0,
            "current_segment_id": "segment-1",
        },
        allocations=[
            {
                "allocation_id": "segment-1",
                "start_date": "2026-09-01",
                "end_date": "2026-09-06",
                "amount_krw": 60_000,
                "actual_spent_krw": 20_000,
                "reserved_remaining_krw": 0,
                "flexible_remaining_krw": 40_000,
            }
        ],
        planned_expenses=[
            {
                "category": "health",
                "amount_krw": 100_000,
                "due_date": "2026-09-20",
                "matched": False,
            }
        ],
        priorities=["건강"],
        spending_rules=["배달은 주말에만"],
        aggregate_patterns={
            "category_spend_krw": {"health": 50_000},
            "reflection_counts": {"well_spent": 1, "unsure": 0, "regretted": 0},
            "judgment_counts": {"justified": 1, "caution": 0},
        },
    )


class OpenAIPlanAdvisorTests(unittest.TestCase):
    def test_sends_only_allowlisted_aggregate_input_with_strict_non_persistent_schema(self) -> None:
        fake_responses = FakeResponses([VALID_NARRATIVE.copy()])
        advisor = OpenAIResponsesPlanAdvisor(
            model="test-model",
            client_factory=lambda: FakeClient(fake_responses),
        )

        result = advisor.advise(advice_request())

        self.assertFalse(result.fallback_used)
        call = fake_responses.calls[0]
        self.assertIs(call["store"], False)
        self.assertTrue(call["text"]["format"]["strict"])
        self.assertEqual(call["max_output_tokens"], 500)
        payload = json.loads(call["input"][1]["content"])
        self.assertEqual(
            set(payload),
            {
                "period_start",
                "period_end",
                "confirmed_budget_krw",
                "deterministic_progress",
                "allocations",
                "planned_expenses",
                "priorities",
                "spending_rules",
                "aggregate_patterns",
            },
        )
        serialized = json.dumps(payload, ensure_ascii=False)
        for forbidden in (
            "merchant",
            "memo",
            "raw reason",
            "reflection_note",
            "account_name",
            "user_ref",
            "transaction_id",
            "raw_transactions",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_rejects_numeric_model_copy_and_uses_honest_fallback(self) -> None:
        invalid = {**VALID_NARRATIVE, "headline": "150000원이 남았어요."}
        fake_responses = FakeResponses([invalid, invalid])
        advisor = OpenAIResponsesPlanAdvisor(
            model="test-model",
            client_factory=lambda: FakeClient(fake_responses),
        )

        result = advisor.advise(advice_request())

        self.assertTrue(result.fallback_used)
        self.assertEqual(len(fake_responses.calls), 2)
        self.assertIn("입력된", result.explanation)

    def test_timeout_falls_back_without_live_call(self) -> None:
        fake_responses = FakeResponses([TimeoutError("timeout"), TimeoutError("timeout")])
        advisor = OpenAIResponsesPlanAdvisor(
            model="test-model",
            client_factory=lambda: FakeClient(fake_responses),
        )

        result = advisor.advise(advice_request())

        self.assertTrue(result.fallback_used)


if __name__ == "__main__":
    unittest.main()
