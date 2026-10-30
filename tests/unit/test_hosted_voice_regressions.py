"""Regressions from hosted R1B/R2A/R2B/R3B, without provider calls."""
from dataclasses import replace
import unittest

from ledger.adapters.openai_judge import (
    EvidenceMismatch, OpenAIResponsesJudge, deterministic_fallback_judgment,
    validate_judgment_evidence,
)
from ledger.rendering import grandma_mode_fallback
from tests.unit.test_openai_rendering_adapters import FakeClient, FakeResponses, VALID_MODEL_PAYLOAD, request
from validators import validate_roast_tone


class HostedVoiceRegressions(unittest.TestCase):
    def test_food_category_history_does_not_prove_delivery_repetition(self):
        req = replace(request(), category="food", user_reason="집에 먹을 것이 있지만 설거지하기 싫어서 배달했어요")
        for field in ("rationale", "normal_message", "roast_message", "recommended_action"):
            for text in ("배달 음식 구매는 최근 한 달 동안 잦은 반복이 있었습니다", "배달 음식을 자주 시키면 부담이 커져요."):
                with self.subTest(field=field, text=text):
                    with self.assertRaises(EvidenceMismatch):
                        validate_judgment_evidence({**VALID_MODEL_PAYLOAD, field: text}, req)

    def test_broad_history_self_report_and_future_delivery_advice_are_distinct(self):
        cases = (
            ("오늘 배달했어요", "식비 분류 전체의 최근 30일 기록에 반복 지출이 있어요."),
            ("배달 음식을 자주 시켜요", "직접 자주 배달한다고 남겼어요."),
            ("배달을 매일 시켜 먹어요", "배달을 자주 시켜 생활비 부담이 커질 수 있어요."),
            ("날마다 배달을 시켜 먹어요", "배달을 자주 시켜 생활비 부담이 커질 수 있어요."),
            ("오늘 배달했어요", "다음 배달 전 집에 있는 음식을 확인해 보세요."),
            ("오늘 배달했어요", "앞으로 배달을 자주 시키지 않도록 먼저 식단을 확인해 보세요."),
        )
        for reason, text in cases:
            with self.subTest(text=text):
                validate_judgment_evidence({**VALID_MODEL_PAYLOAD, "rationale": text}, replace(request(), category="food", user_reason=reason))

    def test_negated_delivery_frequency_is_not_evidence(self):
        req = replace(request(), category="food", user_reason="배달을 자주 시키지는 않아요. 오늘만 시켰어요")
        with self.assertRaises(EvidenceMismatch):
            validate_judgment_evidence({**VALID_MODEL_PAYLOAD, "rationale": "배달을 자주 시킨 기록이 있어요."}, req)

    def test_short_negation_does_not_authorize_positive_frequency_claims(self):
        cases = (
            ("매일 커피를 안 마셔요. 오늘만 샀어요.", "직접 매일 커피를 마신다고 남겼어요."),
            ("배달은 자주 안 시켜요. 오늘만 시켰어요.", "배달을 자주 시킨다고 남겼어요."),
            ("날마다 배달을 안시켜요. 오늘만 시켰어요.", "배달을 자주 시킨다고 남겼어요."),
        )
        for reason, text in cases:
            with self.subTest(reason=reason), self.assertRaises(EvidenceMismatch):
                validate_judgment_evidence({**VALID_MODEL_PAYLOAD, "rationale": text}, replace(request(), user_reason=reason))

    def test_future_advice_cannot_smuggle_in_an_invented_delivery_habit(self):
        req = replace(request(), category="food", user_reason="오늘 설거지가 하기 싫어서 배달했어요")
        with self.assertRaises(EvidenceMismatch):
            validate_judgment_evidence({**VALID_MODEL_PAYLOAD, "recommended_action": "앞으로 배달을 자주 시키는 습관은 줄여 보세요."}, req)

    def test_recorded_purchase_cannot_be_postponed_but_next_purchase_can_be_planned(self):
        for text in ("이번 옷 구매는 다음 달로 미뤄 보세요.", "다음 달 초에 구매해보세요."):
            with self.subTest(text=text), self.assertRaises(EvidenceMismatch):
                validate_judgment_evidence({**VALID_MODEL_PAYLOAD, "recommended_action": text}, request())
        validate_judgment_evidence({**VALID_MODEL_PAYLOAD, "recommended_action": "다음 옷 구매 전 예산을 확인해 보세요."}, request())

    def test_purchase_specific_spoken_voice_does_not_require_a_domestic_object(self):
        self.assertTrue(validate_roast_tone("아이고, 할인표가 네 대신 필요한지 정해 주냐. 다음 구매 전엔 하루만 생각해 보자꾸나.", label="caution")[0])

    def test_formal_roast_is_retried_before_saving_within_existing_two_attempts(self):
        bad = {**VALID_MODEL_PAYLOAD, "roast_message": "그래, 지갑 사용은 적합합니다. 예산을 확인하는 것이 필요합니다."}
        good = {**VALID_MODEL_PAYLOAD, "roast_message": "쯧, 장부부터 보고 이번 주 쇼핑 한 번 쉬어라."}
        responses = FakeResponses([bad, good])
        result = OpenAIResponsesJudge(client_factory=lambda: FakeClient(responses)).judge(request())
        self.assertEqual(len(responses.calls), 2)
        self.assertFalse(result.fallback_used)
        self.assertEqual(result.roast_message, good["roast_message"])

    def test_fallback_keeps_decision_and_action_fields_but_uses_respectful_action(self):
        result = deterministic_fallback_judgment(request())
        self.assertTrue(result.recommended_action.endswith(("보세요.", "해요.")))
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.label, "caution")

    def test_emergency_display_fallback_converts_formal_copy_without_adding_an_action(self):
        text = grandma_mode_fallback(label="justified", rationale="가족의 응급 상황에서 사용한 것은 불가피한 결정이에요. 상황이 중요해 잘 처리된 것입니다.", recommended_action="비상시를 위한 예비자금을 준비해 보세요.")
        self.assertNotIn("것입니다", text)
        self.assertNotIn("결정이에요", text)
        self.assertIn("예비자금을 준비해 보자꾸나", text)
        self.assertTrue(validate_roast_tone(text, label="justified")[0])

    def test_common_formal_rationale_endings_stay_spoken_in_display_fallback(self):
        for rationale in ("필요한 진료비로 확인되며 예산 여유가 있습니다.", "부담이 없습니다.", "평소보다 적었습니다.", "필요한 지출이었습니다.", "계획과 같았습니다."):
            with self.subTest(rationale=rationale):
                text = grandma_mode_fallback(label="justified", rationale=rationale, recommended_action="다음 진료비를 기록해 보세요.")
                self.assertTrue(validate_roast_tone(text, label="justified")[0], text)
