from __future__ import annotations

import json
import unittest
from dataclasses import dataclass
from unittest.mock import patch

from ledger.adapters.openai_judge import (
    JudgmentRequest,
    OpenAIResponsesJudge,
    deterministic_fallback_judgment,
    parse_judgment_payload,
)
from ledger.adapters.synthetic import (
    DisabledProductionAccountAdapter,
    ProviderUnavailableError,
    SyntheticReadOnlyAccountAdapter,
)
from ledger.application.signals import SignalInputs, compute_signal_set
from ledger.domain.models import JudgmentResult
from ledger.rendering import render_judgment
from validators import validate_judgment_parity


VALID_MODEL_PAYLOAD = {
    "label": "caution",
    "confidence": 0.81,
    "rationale": "목표 달성 속도를 늦출 수 있다.",
    "recommended_action": "이번 주 쇼핑을 한 번 쉰다.",
    "decision_factors": ["budget_usage"],
    "normal_message": "목표 달성 속도를 늦출 수 있다. 이번 주 쇼핑을 한 번 쉰다.",
    "roast_message": "아이고 이 화상아, 장부가 벌써 빽빽하다. 이번 주 쇼핑을 한 번 쉰다.",
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


def request() -> JudgmentRequest:
    signals = compute_signal_set(
        SignalInputs(
            transaction_amount_krw=120000,
            discretionary_budget_krw=800000,
            spent_before_transaction_krw=456000,
            category="shopping",
            goal_pressure=0.55,
            baseline_deviation=1.4,
            recurrence_30d=3,
            has_reason=True,
            history_complete=True,
        )
    )
    return JudgmentRequest(
        transaction_id="tx-1",
        amount_krw=120000,
        category="shopping",
        signals=signals,
        user_reason=None,
    )


class StrictOpenAIJudgeTests(unittest.TestCase):
    def test_parses_strict_schema_payload(self) -> None:
        parsed = parse_judgment_payload(VALID_MODEL_PAYLOAD)
        self.assertEqual(parsed["label"], "caution")

    def test_rejects_schema_payload_with_extra_field(self) -> None:
        with self.assertRaises(ValueError):
            parse_judgment_payload({**VALID_MODEL_PAYLOAD, "merchant": "raw"})

    def test_retries_once_after_invalid_schema_then_returns_model_judgment(self) -> None:
        fake_responses = FakeResponses([{"label": "caution"}, VALID_MODEL_PAYLOAD.copy()])
        judge = OpenAIResponsesJudge(
            model="test-model",
            max_retries=2,
            client_factory=lambda: FakeClient(fake_responses),
        )
        result = judge.judge(request())
        self.assertFalse(result.fallback_used)
        self.assertEqual(len(fake_responses.calls), 2)

    def test_retry_attempts_are_capped_to_avoid_multiplicative_retries(self) -> None:
        fake_responses = FakeResponses(
            [{"label": "caution"}, {"label": "caution"}, VALID_MODEL_PAYLOAD.copy()]
        )
        judge = OpenAIResponsesJudge(
            model="test-model",
            max_retries=9,
            client_factory=lambda: FakeClient(fake_responses),
        )
        result = judge.judge(request())
        self.assertTrue(result.fallback_used)
        self.assertEqual(len(fake_responses.calls), 2)

    def test_falls_back_after_two_model_failures(self) -> None:
        fake_responses = FakeResponses([RuntimeError("boom"), RuntimeError("boom")])
        judge = OpenAIResponsesJudge(
            model="test-model",
            client_factory=lambda: FakeClient(fake_responses),
        )
        result = judge.judge(request())
        self.assertTrue(result.fallback_used)

    def test_sends_store_false_and_strict_json_schema(self) -> None:
        fake_responses = FakeResponses([VALID_MODEL_PAYLOAD.copy()])
        judge = OpenAIResponsesJudge(
            model="test-model",
            client_factory=lambda: FakeClient(fake_responses),
        )
        judge.judge(request())
        call = fake_responses.calls[0]
        self.assertIs(call["store"], False)
        self.assertTrue(call["text"]["format"]["strict"])
        self.assertEqual(call["max_output_tokens"], 700)
        self.assertEqual(call["timeout"], 20.0)

    def test_allows_configured_strict_output_token_cap(self) -> None:
        fake_responses = FakeResponses([VALID_MODEL_PAYLOAD.copy()])
        judge = OpenAIResponsesJudge(
            model="test-model",
            max_output_tokens=321,
            client_factory=lambda: FakeClient(fake_responses),
        )
        judge.judge(request())
        self.assertEqual(fake_responses.calls[0]["max_output_tokens"], 321)

    def test_omits_raw_merchant_from_model_input(self) -> None:
        fake_responses = FakeResponses([VALID_MODEL_PAYLOAD.copy()])
        judge = OpenAIResponsesJudge(
            model="test-model",
            client_factory=lambda: FakeClient(fake_responses),
        )
        judge.judge(request())
        user_content = fake_responses.calls[0]["input"][1]["content"]
        self.assertNotIn("merchant", user_content)

    def test_prompt_defines_korean_grandma_mode_voice_and_safety(self) -> None:
        fake_responses = FakeResponses([VALID_MODEL_PAYLOAD.copy()])
        judge = OpenAIResponsesJudge(
            model="test-model",
            client_factory=lambda: FakeClient(fake_responses),
        )
        judge.judge(request())
        system_content = fake_responses.calls[0]["input"][0]["content"]
        self.assertIn("욕쟁이 할머니 모드", system_content)
        self.assertIn("장부 바닥", system_content)
        self.assertIn("without threats", system_content)

    def test_deterministic_fallback_uses_a_specific_grandma_voice(self) -> None:
        result = deterministic_fallback_judgment(request())
        self.assertTrue(any(marker in result.roast_message for marker in ("장부", "냄비", "지갑")))
        self.assertTrue(any(marker in result.roast_message for marker in ("아이고", "아이구", "쯧", "그래")))
        self.assertIn(result.recommended_action, result.roast_message)


class RenderingTests(unittest.TestCase):
    def judgment(self) -> JudgmentResult:
        return JudgmentResult(
            judgment_id="judgment-1",
            transaction_id="tx-1",
            label="caution",
            confidence=0.81,
            rationale="목표 달성 속도를 늦출 수 있다.",
            recommended_action="이번 주 쇼핑을 한 번 쉰다.",
            decision_factors=["budget_usage"],
            normal_message="목표 달성 속도를 늦출 수 있다. 이번 주 쇼핑을 한 번 쉰다.",
            roast_message="아이고 이 화상아, 장부가 벌써 빽빽하다. 이번 주 쇼핑을 한 번 쉰다.",
            fallback_used=False,
            model="test-model",
            policy_version="overspending-v1",
            created_at="2026-08-01T00:00:00Z",
        )

    def test_normal_and_roast_preserve_semantic_fields(self) -> None:
        normal = render_judgment(self.judgment(), roast_enabled=False).to_dict()
        roast = render_judgment(self.judgment(), roast_enabled=True).to_dict()
        valid, reason = validate_judgment_parity(normal, roast)
        self.assertTrue(valid, reason)

    def test_unsafe_roast_uses_safe_message_without_changing_label(self) -> None:
        judgment = JudgmentResult(
            **{
                **self.judgment().to_dict(),
                "roast_message": "거지처럼 굴지 마라.",
            }
        )
        rendered = render_judgment(judgment, roast_enabled=True)
        self.assertEqual(rendered.label, "caution")
        self.assertNotIn("거지", rendered.message)

    def test_roast_threat_variant_uses_safe_message(self) -> None:
        judgment = JudgmentResult(
            **{
                **self.judgment().to_dict(),
                "roast_message": "쯧, 쓸데없는 소비면 너는 죽는 거야.",
            }
        )
        rendered = render_judgment(judgment, roast_enabled=True)
        self.assertEqual(rendered.label, "caution")
        self.assertNotIn("죽는", rendered.message)

    def test_bland_roast_uses_specific_grandma_fallback(self) -> None:
        judgment = JudgmentResult(
            **{
                **self.judgment().to_dict(),
                "roast_message": "이번 주 쇼핑을 한 번 쉰다.",
            }
        )
        rendered = render_judgment(judgment, roast_enabled=True)
        self.assertIn("냄비", rendered.message)
        self.assertIn("이번 주 쇼핑을 한 번 쉰다.", rendered.message)

    def test_unsafe_normal_uses_safe_message_without_changing_recommendation(self) -> None:
        judgment = JudgmentResult(
            **{
                **self.judgment().to_dict(),
                "normal_message": "빚쟁이처럼 굴지 마라.",
            }
        )
        rendered = render_judgment(judgment, roast_enabled=False)
        self.assertEqual(rendered.recommended_action, "이번 주 쇼핑을 한 번 쉰다.")
        self.assertNotIn("빚쟁이", rendered.message)


class AccountAdapterTests(unittest.TestCase):
    def test_synthetic_adapter_returns_read_only_transactions_for_user(self) -> None:
        adapter = SyntheticReadOnlyAccountAdapter.sample()
        transaction = adapter.fetch_transactions("usr_test", "synthetic-connection")[0]
        self.assertEqual(transaction.source, "synthetic")
        self.assertEqual(transaction.user_ref, "usr_test")

    def test_synthetic_adapter_revokes_connection(self) -> None:
        adapter = SyntheticReadOnlyAccountAdapter.sample()
        adapter.revoke_connection("usr_test", "synthetic-connection")
        self.assertEqual(adapter.list_connections("usr_test")[0].status, "revoked")

    def test_disabled_provider_rejects_reads(self) -> None:
        with self.assertRaises(ProviderUnavailableError):
            DisabledProductionAccountAdapter().list_connections("usr_test")

    def test_read_only_port_exposes_no_money_movement_methods(self) -> None:
        adapter = SyntheticReadOnlyAccountAdapter.sample()
        forbidden = {"transfer", "withdraw", "pay", "create_order", "execute_savings"}
        self.assertTrue(forbidden.isdisjoint(set(dir(adapter))))


class SheetsTelemetryTests(unittest.TestCase):
    def test_sheets_rejects_raw_fields_without_importing_network_clients(self) -> None:
        with patch.dict("sys.modules", {"gspread": None}):
            import sheets_logger

            with self.assertRaises(Exception):
                sheets_logger.save_telemetry_event(
                    {"event_type": "judgment.completed", "merchant": "raw"}
                )


if __name__ == "__main__":
    unittest.main()
