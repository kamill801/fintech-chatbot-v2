from __future__ import annotations

import unittest

from ledger.application.service import ServiceError
from ledger.domain.events import (
    EVENT_JUDGMENT_COMPLETED,
    EVENT_JUDGMENT_CORRECTED,
    EVENT_JUDGMENT_REASON_REQUESTED,
    EVENT_TRANSACTION_RECORDED,
    EVENT_TRANSACTION_REFLECTED,
)
from ledger.quota import QuotaExceededError, QuotaUnavailableError
from tests.helpers import correlation_id, now_iso, profile_payload, service_with_memory


class FakeQuota:
    def __init__(self, failures: list[Exception] | None = None) -> None:
        self.failures = failures or []
        self.calls: list[str] = []

    def check_and_increment(self, user_ref: str) -> None:
        self.calls.append(user_ref)
        if self.failures:
            raise self.failures.pop(0)


class InMemoryLedgerFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.repository, _privacy, self.judge = service_with_memory()
        self.user_ref = "usr_test"

    def upsert_profile(self) -> None:
        self.service.upsert_profile(
            self.user_ref,
            profile_payload(),
            idempotency_key="profile-1",
            correlation_id=correlation_id(),
        )

    def enable_roast(self, key: str = "settings-roast") -> None:
        self.service.update_settings(
            self.user_ref,
            {"roast_enabled": True},
            idempotency_key=key,
            correlation_id=correlation_id(),
        )

    def test_rejects_transaction_when_profile_is_missing(self) -> None:
        with self.assertRaises(ServiceError) as caught:
            self.service.create_transaction(
                self.user_ref,
                {"amount_krw": 50000, "category": "shopping"},
                idempotency_key="tx-1",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.code, "profile_required")

    def test_normal_mode_judges_sparse_transaction_without_reason_question(self) -> None:
        self.upsert_profile()
        result = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-normal",
            correlation_id=correlation_id(),
        )
        self.assertEqual(result.status, 201)
        self.assertIn("judgment", result.data)
        self.assertNotIn("pending_question", result.data)
        self.assertEqual(result.data["transaction"]["status"], "judged")

    def test_roast_mode_records_pending_question_for_every_transaction(self) -> None:
        self.upsert_profile()
        self.enable_roast()
        result = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(result.status, 202)
        self.assertIn("pending_question", result.data)

    def test_repeated_transaction_idempotency_returns_same_pending_question(self) -> None:
        self.upsert_profile()
        self.enable_roast()
        first = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        second = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(
            first.data["pending_question"]["question_id"],
            second.data["pending_question"]["question_id"],
        )

    def test_creates_exactly_one_reason_question_event_per_transaction(self) -> None:
        self.upsert_profile()
        self.enable_roast()
        self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        reason_events = [
            event
            for event in self.repository.list_events(self.user_ref)
            if event.event_type == EVENT_JUDGMENT_REASON_REQUESTED
        ]
        self.assertEqual(len(reason_events), 1)

    def test_reason_submission_completes_judgment(self) -> None:
        self.upsert_profile()
        self.enable_roast()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        transaction_id = pending.data["transaction"]["transaction_id"]
        judged = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(judged.status, 201)

    def test_quota_covers_direct_transaction_judgment_path(self) -> None:
        quota = FakeQuota()
        self.service, self.repository, _privacy, self.judge = service_with_memory(
            judgment_quota=quota
        )
        self.upsert_profile()
        result = self.service.create_transaction(
            self.user_ref,
            {
                "amount_krw": 1000,
                "category": "transport",
                "reason": "출근",
            },
            idempotency_key="tx-direct",
            correlation_id=correlation_id(),
        )
        self.assertEqual(result.status, 201)
        self.assertEqual(quota.calls, [self.user_ref])

    def test_quota_covers_reason_answer_judgment_path(self) -> None:
        quota = FakeQuota()
        self.service, self.repository, _privacy, self.judge = service_with_memory(
            judgment_quota=quota
        )
        self.upsert_profile()
        self.enable_roast()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(quota.calls, [])
        judged = self.service.add_reason(
            self.user_ref,
            pending.data["transaction"]["transaction_id"],
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(judged.status, 201)
        self.assertEqual(quota.calls, [self.user_ref])

    def test_quota_errors_are_safe_429_service_errors(self) -> None:
        quota = FakeQuota([QuotaExceededError("raw quota key")])
        self.service, self.repository, _privacy, self.judge = service_with_memory(
            judgment_quota=quota
        )
        self.upsert_profile()
        with self.assertRaises(ServiceError) as caught:
            self.service.create_transaction(
                self.user_ref,
                {"amount_krw": 1000, "category": "transport", "reason": "출근"},
                idempotency_key="tx-limited",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(caught.exception.code, "ai_judgment_quota_exceeded")
        self.assertIn("오늘 사용할 수 있는", str(caught.exception))
        self.assertNotIn(self.user_ref, str(caught.exception))
        self.assertEqual(list(self.repository.list_transactions(self.user_ref)), [])

    def test_quota_unavailable_fails_closed_when_limiter_is_configured(self) -> None:
        quota = FakeQuota([QuotaUnavailableError("redis down")])
        self.service, self.repository, _privacy, self.judge = service_with_memory(
            judgment_quota=quota
        )
        self.upsert_profile()
        with self.assertRaises(ServiceError) as caught:
            self.service.create_transaction(
                self.user_ref,
                {"amount_krw": 1000, "category": "transport", "reason": "출근"},
                idempotency_key="tx-quota-down",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(caught.exception.code, "ai_judgment_quota_unavailable")
        self.assertIn("한도를 확인하지 못했어요", str(caught.exception))
        self.assertEqual(list(self.repository.list_transactions(self.user_ref)), [])

    def test_reason_is_not_saved_when_judgment_quota_is_rejected(self) -> None:
        quota = FakeQuota([QuotaExceededError("raw quota key")])
        self.service, self.repository, _privacy, self.judge = service_with_memory(
            judgment_quota=quota
        )
        self.upsert_profile()
        self.enable_roast()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-reason-limited",
            correlation_id=correlation_id(),
        )
        transaction_id = pending.data["transaction"]["transaction_id"]

        with self.assertRaises(ServiceError) as caught:
            self.service.add_reason(
                self.user_ref,
                transaction_id,
                {"reason": "업무상 필요해서 샀다"},
                idempotency_key="reason-limited",
                correlation_id=correlation_id(),
            )

        self.assertEqual(caught.exception.code, "ai_judgment_quota_exceeded")
        transaction = self.repository.get_transaction(self.user_ref, transaction_id)
        self.assertIsNotNone(transaction)
        self.assertIsNone(transaction.reason)
        self.assertIsNone(
            self.repository.get_judgment_for_transaction(self.user_ref, transaction_id)
        )
        saved_pending = self.repository.get_pending_question(self.user_ref)
        self.assertIsNotNone(saved_pending)
        self.assertIsNone(saved_pending.answered_at)

    def test_repeated_reason_submission_is_idempotent_after_judgment(self) -> None:
        self.upsert_profile()
        self.enable_roast()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        transaction_id = pending.data["transaction"]["transaction_id"]
        first = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        second = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(
            first.data["judgment"]["judgment_id"],
            second.data["judgment"]["judgment_id"],
        )

    def test_correction_appends_event_without_removing_original_judgment(self) -> None:
        self.upsert_profile()
        self.enable_roast()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        judged = self.service.add_reason(
            self.user_ref,
            pending.data["transaction"]["transaction_id"],
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        self.service.correct_judgment(
            self.user_ref,
            judged.data["judgment"]["judgment_id"],
            {"corrected_label": "justified", "correction_reason": "환급 예정"},
            idempotency_key="correction-1",
            correlation_id=correlation_id(),
        )
        event_types = [event.event_type for event in self.repository.list_events(self.user_ref)]
        self.assertIn(EVENT_JUDGMENT_COMPLETED, event_types)
        self.assertIn(EVENT_JUDGMENT_CORRECTED, event_types)
        current = self.service.get_transaction(
            self.user_ref, pending.data["transaction"]["transaction_id"]
        ).data["judgment"]
        self.assertNotEqual(current["original_label"], "")
        self.assertEqual(current["effective_label"], "justified")
        self.assertEqual(current["correction"]["correction_reason"], "환급 예정")

    def test_spending_rules_are_sanitized_persisted_and_sent_to_judge(self) -> None:
        self.upsert_profile()
        updated = self.service.update_settings(
            self.user_ref,
            {
                "spending_rules": [
                    "  배달은 주 2회까지  ",
                    "",
                    "친구와의 만남은 우선순위가 높음",
                ]
            },
            idempotency_key="settings-rules",
            correlation_id=correlation_id(),
        )
        self.assertEqual(
            updated.data["settings"]["spending_rules"],
            ["배달은 주 2회까지", "친구와의 만남은 우선순위가 높음"],
        )

        self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 18000, "category": "food_delivery"},
            idempotency_key="tx-with-rules",
            correlation_id=correlation_id(),
        )
        self.assertEqual(
            self.judge.requests[-1].spending_rules,
            ["배달은 주 2회까지", "친구와의 만남은 우선순위가 높음"],
        )

    def test_reflection_replaces_projection_and_appends_audit_events(self) -> None:
        self.upsert_profile()
        created = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 18000, "category": "food_delivery"},
            idempotency_key="tx-reflection",
            correlation_id=correlation_id(),
        )
        transaction_id = created.data["transaction"]["transaction_id"]

        self.service.reflect_transaction(
            self.user_ref,
            transaction_id,
            {"reflection": "unsure", "reflection_note": "편하긴 했어요"},
            idempotency_key="reflection-1",
            correlation_id=correlation_id(),
        )
        replaced = self.service.reflect_transaction(
            self.user_ref,
            transaction_id,
            {"reflection": "regretted", "reflection_note": "집에 먹을 게 있었어요"},
            idempotency_key="reflection-2",
            correlation_id=correlation_id(),
        )

        self.assertEqual(replaced.data["transaction"]["reflection"], "regretted")
        self.assertEqual(
            replaced.data["transaction"]["reflection_note"],
            "집에 먹을 게 있었어요",
        )
        self.assertIn("judgment", self.service.get_transaction(self.user_ref, transaction_id).data)
        reflection_events = [
            event
            for event in self.repository.list_events(self.user_ref)
            if event.event_type == EVENT_TRANSACTION_REFLECTED
        ]
        self.assertEqual(len(reflection_events), 2)

    def test_next_judgment_receives_category_regret_history(self) -> None:
        self.upsert_profile()
        created = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 18000, "category": "food_delivery"},
            idempotency_key="tx-regret-history",
            correlation_id=correlation_id(),
        )
        self.service.reflect_transaction(
            self.user_ref,
            created.data["transaction"]["transaction_id"],
            {"reflection": "regretted", "reflection_note": "습관적으로 주문"},
            idempotency_key="reflection-history",
            correlation_id=correlation_id(),
        )

        self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 21000, "category": "food_delivery"},
            idempotency_key="tx-after-regret",
            correlation_id=correlation_id(),
        )

        self.assertEqual(
            self.judge.requests[-1].reflection_context,
            {
                "category_reflected_count": 1,
                "category_regretted_count": 1,
                "category_regret_rate": 1.0,
            },
        )

    def test_weekly_briefing_prioritizes_real_regret_pattern_and_goal_impact(self) -> None:
        self.upsert_profile()
        for index, amount in enumerate((18000, 22000), start=1):
            created = self.service.create_transaction(
                self.user_ref,
                {
                    "amount_krw": amount,
                    "category": "food_delivery",
                    "occurred_at": now_iso(),
                },
                idempotency_key=f"tx-regret-{index}",
                correlation_id=correlation_id(),
            )
            self.service.reflect_transaction(
                self.user_ref,
                created.data["transaction"]["transaction_id"],
                {"reflection": "regretted", "reflection_note": "습관적으로 주문"},
                idempotency_key=f"reflection-regret-{index}",
                correlation_id=correlation_id(),
            )

        summary = self.service.get_summary(self.user_ref).data["summary"]
        reflections = summary["reflection_summary"]
        briefing = summary["weekly_briefing"]
        self.assertEqual(reflections["regretted_count"], 2)
        self.assertEqual(reflections["regretted_spent_krw"], 40000)
        self.assertEqual(reflections["regret_rate"], 1.0)
        self.assertGreaterEqual(reflections["goal_delay_days"], 1)
        self.assertEqual(briefing["regret_pattern"]["category"], "food_delivery")
        self.assertEqual(briefing["evidence_state"], "learned")
        self.assertIn("배달", briefing["improvement"])

    def test_share_payload_uses_corrected_effective_label(self) -> None:
        telemetry_events = []
        self.service.telemetry_sink = telemetry_events.append
        self.upsert_profile()
        self.enable_roast()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-share-correction",
            correlation_id=correlation_id(),
        )
        judged = self.service.add_reason(
            self.user_ref,
            pending.data["transaction"]["transaction_id"],
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-share-correction",
            correlation_id=correlation_id(),
        )
        self.service.correct_judgment(
            self.user_ref,
            judged.data["judgment"]["judgment_id"],
            {"corrected_label": "justified", "correction_reason": "회사 환급"},
            idempotency_key="correction-share",
            correlation_id=correlation_id(),
        )
        shared = self.service.share_judgment(
            self.user_ref,
            judged.data["judgment"]["judgment_id"],
            idempotency_key="share-corrected",
            correlation_id=correlation_id(),
        )
        self.assertEqual(shared.data["share"]["label"], "justified")
        self.assertIn("납득할 만한 지출", shared.data["share"]["roast_message"])
        self.assertNotIn("장부 바닥", shared.data["share"]["roast_message"])
        current = self.service.get_transaction(
            self.user_ref, pending.data["transaction"]["transaction_id"]
        ).data["judgment"]
        self.assertNotEqual(current["original_label"], "")
        self.assertEqual(current["effective_label"], "justified")
        self.service.record_share_success(
            self.user_ref,
            judged.data["judgment"]["judgment_id"],
            idempotency_key="share-success-corrected",
            correlation_id=correlation_id(),
        )
        share_success = next(
            event for event in telemetry_events if event["event_type"] == "share.succeeded"
        )
        self.assertEqual(share_success["label"], "justified")

    def test_list_transactions_returns_newest_first(self) -> None:
        self.upsert_profile()
        self.service.create_transaction(
            self.user_ref,
            {
                "amount_krw": 1000,
                "category": "transport",
                "reason": "출근",
                "occurred_at": "2026-08-01T00:00:00+00:00",
            },
            idempotency_key="tx-old",
            correlation_id=correlation_id(),
        )
        self.service.create_transaction(
            self.user_ref,
            {
                "amount_krw": 2000,
                "category": "transport",
                "reason": "퇴근",
                "occurred_at": "2026-08-03T00:00:00+00:00",
            },
            idempotency_key="tx-new",
            correlation_id=correlation_id(),
        )
        transactions = self.service.list_transactions(self.user_ref).data["transactions"]
        self.assertEqual([item["amount_krw"] for item in transactions[:2]], [2000, 1000])

    def test_share_requires_roast_enabled(self) -> None:
        self.upsert_profile()
        judged = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        with self.assertRaises(ServiceError) as caught:
            self.service.share_judgment(
                self.user_ref,
                judged.data["judgment"]["judgment_id"],
                idempotency_key="share-1",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.code, "roast_required")

    def test_roast_mode_does_not_overwrite_an_unanswered_question(self) -> None:
        self.upsert_profile()
        self.enable_roast()
        first = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 12000, "category": "cafe"},
            idempotency_key="tx-first-pending",
            correlation_id=correlation_id(),
        )
        with self.assertRaises(ServiceError) as caught:
            self.service.create_transaction(
                self.user_ref,
                {"amount_krw": 9000, "category": "food"},
                idempotency_key="tx-second-pending",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.code, "pending_reason_required")
        self.assertEqual(
            self.repository.get_pending_question(self.user_ref).question_id,
            first.data["pending_question"]["question_id"],
        )

    def test_deletion_purges_profile_projection(self) -> None:
        self.upsert_profile()
        self.service.delete_user_data(
            self.user_ref,
            idempotency_key="delete-1",
            correlation_id=correlation_id(),
        )
        self.assertIsNone(self.repository.get_profile(self.user_ref))

    def test_fallback_telemetry_failure_logs_only_redacted_operator_warning(self) -> None:
        self.upsert_profile()

        def broken_sink(_payload):
            raise RuntimeError("sheet down")

        self.service.telemetry_sink = broken_sink
        with self.assertLogs("ledger.application.service", level="WARNING") as logs:
            self.service.create_transaction(
                self.user_ref,
                {"amount_krw": 1000, "category": "transport", "reason": "출근"},
                idempotency_key="tx-fallback-warning",
                correlation_id=correlation_id(),
            )
        output = "\n".join(logs.output)
        self.assertIn("OpenAI fallback used and telemetry sink failed", output)
        self.assertNotIn(self.user_ref, output)
        self.assertNotIn("1000", output)
        self.assertNotIn("출근", output)


if __name__ == "__main__":
    unittest.main()
