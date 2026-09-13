from __future__ import annotations

import unittest

from ledger.adapters.openai_planner import PlanNarrative
from ledger.application.service import ServiceError
from ledger.domain.models import DomainValidationError
from ledger.domain.events import (
    EVENT_PLAN_ACTIVATED,
    EVENT_PLAN_CHECKED_IN,
    EVENT_PLANNED_EXPENSE_MATCHED,
    EVENT_PLAN_REVISED,
)
from ledger.domain.plans import SpendingPlan
from tests.helpers import correlation_id, profile_payload, service_with_memory


class CountingPlanAdvisor:
    def __init__(self) -> None:
        self.calls = 0

    def advise(self, request) -> PlanNarrative:
        self.calls += 1
        return PlanNarrative(
            headline="확정한 계획을 차분하게 이어가요.",
            explanation="예약과 실제 지출을 나눠 다음 행동을 정했어요.",
            segment_focuses=[
                {
                    "allocation_id": item["allocation_id"],
                    "focus": "예약한 지출을 먼저 확인하세요.",
                }
                for item in request.allocations
            ],
            next_action="다음 지출 전에 현재 구간을 확인하세요.",
            assumptions=["입력한 장부가 최신 상태라고 가정했어요."],
            confidence="medium",
            fallback_used=False,
        )


def plan_payload(*, budget: int = 300_000) -> dict:
    return {
        "period_start": "2026-09-01",
        "period_end": "2026-09-30",
        "confirmed_budget_krw": budget,
        "priorities": ["친구와의 약속", "건강"],
        "planned_expenses": [
            {
                "planned_expense_id": "planned-class",
                "name": "운동 수업",
                "amount_krw": 100_000,
                "due_date": "2026-09-20",
                "category": "health",
            }
        ],
    }


class SpendingPlanFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.repository, _privacy, self.judge = service_with_memory()
        self.user_ref = "usr_plan"
        self.service.upsert_profile(
            self.user_ref,
            profile_payload(),
            idempotency_key="profile",
            correlation_id=correlation_id(),
        )

    def create_expense(
        self,
        key: str,
        amount: int,
        occurred_at: str,
        *,
        excluded: bool = False,
    ) -> dict:
        return self.service.create_transaction(
            self.user_ref,
            {
                "amount_krw": amount,
                "category": "health",
                "occurred_at": occurred_at,
                "exclude_from_budget": excluded,
            },
            idempotency_key=key,
            correlation_id=correlation_id(),
        ).data["transaction"]

    def activate(self, *, budget: int = 300_000):
        return self.service.activate_spending_plan(
            self.user_ref,
            {**plan_payload(budget=budget), "confirmed": True},
            idempotency_key=f"activate-{budget}",
            correlation_id=correlation_id(),
        )

    def test_preview_does_not_persist_and_activation_is_encrypted_round_trip(self) -> None:
        preview = self.service.preview_spending_plan(self.user_ref, plan_payload())
        self.assertTrue(preview.data["preview"])
        self.assertIsNone(self.repository.get_spending_plan(self.user_ref))

        activated = self.activate()
        self.assertEqual(activated.status, 201)
        self.assertEqual(activated.data["plan"]["status"], "active")
        self.assertEqual(
            sum(item["amount_krw"] for item in activated.data["plan"]["allocations"]),
            300_000,
        )
        stored = self.repository._users[self.user_ref].spending_plan
        self.assertIsInstance(stored, str)
        self.assertNotIn("운동 수업", stored)
        self.assertIsInstance(self.repository.get_spending_plan(self.user_ref), SpendingPlan)

    def test_confirmed_narrative_is_encrypted_and_get_does_not_call_ai_again(self) -> None:
        advisor = CountingPlanAdvisor()
        service, repository, _privacy, _judge = service_with_memory(
            plan_advisor=advisor
        )
        user_ref = "usr_stable_plan_narrative"
        service.upsert_profile(
            user_ref,
            profile_payload(),
            idempotency_key="profile",
            correlation_id=correlation_id(),
        )

        activated = service.activate_spending_plan(
            user_ref,
            {**plan_payload(), "confirmed": True},
            idempotency_key="activate",
            correlation_id=correlation_id(),
        )
        self.assertEqual(advisor.calls, 1)
        self.assertEqual(
            activated.data["narrative"]["headline"],
            "확정한 계획을 차분하게 이어가요.",
        )
        service.get_spending_plan(user_ref)
        service.get_spending_plan(user_ref)
        self.assertEqual(advisor.calls, 1)
        self.assertNotIn(
            "확정한 계획",
            repository._users[user_ref].spending_plan,
        )

    def test_progress_excludes_flagged_expenses_and_exposes_negative_shortfall(self) -> None:
        self.activate(budget=100_000)
        self.create_expense("included", 50_000, "2026-09-10T12:00:00Z")
        self.create_expense("excluded", 80_000, "2026-09-11T12:00:00Z", excluded=True)

        progress = self.service.get_spending_plan(self.user_ref).data["progress"]
        self.assertEqual(progress["actual_spent_krw"], 50_000)
        self.assertEqual(progress["reserved_remaining_krw"], 100_000)
        self.assertEqual(progress["total_remaining_krw"], 50_000)
        self.assertEqual(progress["flexible_remaining_krw"], -50_000)
        self.assertEqual(progress["shortfall_krw"], 50_000)

    def test_revision_preview_apply_check_in_and_match_preserve_history(self) -> None:
        current = self.activate().data["plan"]
        transaction = self.create_expense("actual", 70_000, "2026-09-20T03:00:00Z")
        revision_payload = {
            **plan_payload(budget=350_000),
            "base_version": current["version"],
            "reason": "추석 모임 반영",
        }
        preview = self.service.preview_spending_plan_revision(
            self.user_ref, revision_payload
        )
        self.assertEqual(preview.data["revision_preview"]["budget_change_krw"], 50_000)
        self.assertEqual(self.repository.get_spending_plan(self.user_ref).version, 1)

        applied = self.service.apply_spending_plan_revision(
            self.user_ref,
            {**revision_payload, "apply": True},
            idempotency_key="revision",
            correlation_id=correlation_id(),
        )
        self.assertEqual(applied.data["plan"]["version"], 2)
        self.assertEqual(len(applied.data["plan"]["revisions"]), 1)
        self.assertEqual(applied.data["original_plan"]["confirmed_budget_krw"], 300_000)

        checked = self.service.check_in_spending_plan(
            self.user_ref,
            {"decision": "maintain", "note": "이번 주는 유지"},
            idempotency_key="check-in",
            correlation_id=correlation_id(),
        )
        self.assertEqual(checked.data["next_step"], "continue")
        self.assertEqual(len(checked.data["plan"]["check_ins"]), 1)

        before_match = checked.data["progress"]
        matched = self.service.match_planned_expense(
            self.user_ref,
            "planned-class",
            {"transaction_id": transaction["transaction_id"]},
            idempotency_key="match",
            correlation_id=correlation_id(),
        )
        self.assertEqual(matched.data["progress"]["actual_spent_krw"], 70_000)
        self.assertEqual(matched.data["progress"]["reserved_remaining_krw"], 0)
        self.assertEqual(
            matched.data["progress"]["flexible_remaining_krw"],
            before_match["flexible_remaining_krw"] + 100_000,
        )
        events = [event.event_type for event in self.repository.list_events(self.user_ref)]
        self.assertIn(EVENT_PLAN_ACTIVATED, events)
        self.assertIn(EVENT_PLAN_REVISED, events)
        self.assertIn(EVENT_PLAN_CHECKED_IN, events)
        self.assertIn(EVENT_PLANNED_EXPENSE_MATCHED, events)

    def test_transaction_response_includes_plan_impact(self) -> None:
        self.activate()
        result = self.service.create_transaction(
            self.user_ref,
            {
                "amount_krw": 20_000,
                "category": "cafe",
                "occurred_at": "2026-09-12T03:00:00Z",
            },
            idempotency_key="impact",
            correlation_id=correlation_id(),
        )
        self.assertEqual(result.data["plan_impact"]["total_remaining_krw"], 280_000)
        self.assertEqual(result.data["plan_impact"]["flexible_remaining_krw"], 180_000)

    def test_signal_month_uses_user_timezone_and_excludes_budget_flags(self) -> None:
        self.create_expense("local-september", 80_000, "2026-08-31T15:30:00Z")
        self.create_expense(
            "excluded-large", 700_000, "2026-09-02T03:00:00Z", excluded=True
        )
        result = self.service.create_transaction(
            self.user_ref,
            {
                "amount_krw": 20_000,
                "category": "health",
                "occurred_at": "2026-09-05T03:00:00Z",
            },
            idempotency_key="timezone-current",
            correlation_id=correlation_id(),
        )
        self.assertEqual(result.data["signals"]["budget_usage_after"], 0.125)

    def test_plan_period_edges_use_the_configured_local_timezone(self) -> None:
        self.activate()
        self.create_expense("first-edge", 10_000, "2026-08-31T15:00:00Z")
        self.create_expense("last-edge", 20_000, "2026-09-30T14:59:59Z")
        self.create_expense("outside-edge", 40_000, "2026-09-30T15:00:00Z")

        progress = self.service.get_spending_plan(self.user_ref).data["progress"]

        self.assertEqual(progress["actual_spent_krw"], 30_000)

    def test_custom_allocations_must_cover_the_complete_period(self) -> None:
        payload = {
            **plan_payload(),
            "allocations": [
                {
                    "allocation_id": "gap",
                    "label": "빠진 첫날",
                    "start_date": "2026-09-02",
                    "end_date": "2026-09-30",
                    "amount_krw": 300_000,
                }
            ],
        }

        with self.assertRaises(DomainValidationError):
            self.service.preview_spending_plan(self.user_ref, payload)

    def test_matching_rejects_another_users_transaction(self) -> None:
        self.activate()
        other_user = "usr_other"
        self.service.upsert_profile(
            other_user,
            profile_payload(),
            idempotency_key="other-profile",
            correlation_id=correlation_id(),
        )
        other_transaction = self.service.create_transaction(
            other_user,
            {
                "amount_krw": 70_000,
                "category": "health",
                "occurred_at": "2026-09-20T03:00:00Z",
            },
            idempotency_key="other-transaction",
            correlation_id=correlation_id(),
        ).data["transaction"]

        with self.assertRaises(ServiceError) as raised:
            self.service.match_planned_expense(
                self.user_ref,
                "planned-class",
                {"transaction_id": other_transaction["transaction_id"]},
                idempotency_key="foreign-match",
                correlation_id=correlation_id(),
            )
        self.assertEqual(raised.exception.code, "transaction_not_found")

    def test_deletion_purges_plan_projection_and_events(self) -> None:
        self.activate()
        self.service.delete_user_data(
            self.user_ref,
            idempotency_key="delete",
            correlation_id=correlation_id(),
        )
        self.assertIsNone(self.repository.get_spending_plan(self.user_ref))
        self.assertEqual(list(self.repository.list_events(self.user_ref)), [])

    def test_deletion_does_not_treat_a_plan_only_account_as_empty(self) -> None:
        plan_only_user = "usr_plan_only"
        self.service.activate_spending_plan(
            plan_only_user,
            {**plan_payload(), "confirmed": True},
            idempotency_key="activate-plan-only",
            correlation_id=correlation_id(),
        )

        self.service.delete_user_data(
            plan_only_user,
            idempotency_key="delete-plan-only",
            correlation_id=correlation_id(),
        )

        self.assertIsNone(self.repository.get_spending_plan(plan_only_user))
        self.assertEqual(list(self.repository.list_events(plan_only_user)), [])


if __name__ == "__main__":
    unittest.main()
