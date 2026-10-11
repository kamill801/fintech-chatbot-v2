from __future__ import annotations

import unittest
from dataclasses import replace

from ledger.application.service import ServiceError
from tests.helpers import correlation_id, profile_payload, service_with_memory
from tests.integration.test_spending_plan import CountingPlanAdvisor, plan_payload


class PlanReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.advisor = CountingPlanAdvisor()
        self.service, self.repository, self.privacy, self.judge = service_with_memory(plan_advisor=self.advisor)
        self.user = "usr_plan_reliability"
        self.service.upsert_profile(self.user, profile_payload(), idempotency_key="profile", correlation_id=correlation_id())

    def activate(self):
        return self.service.activate_spending_plan(self.user, {**plan_payload(), "confirmed": True}, idempotency_key="activate", correlation_id=correlation_id())

    def expense(self, amount=70_000):
        return self.service.create_transaction(self.user, {"amount_krw": amount, "category": "health", "occurred_at": "2026-09-20T03:00:00Z"}, idempotency_key=f"expense-{amount}", correlation_id=correlation_id()).data["transaction"]

    def test_reviewed_activation_reuses_advice_and_generated_id(self):
        payload = {**plan_payload(), "planned_expenses": [{"name": "운동", "amount_krw": 30_000, "due_date": "2026-09-20", "category": "health"}]}
        preview = self.service.preview_spending_plan(self.user, payload).data
        saved = self.service.activate_spending_plan(self.user, {**payload, "confirmed": True, "preview_token": preview["preview_token"]}, idempotency_key="review-activate", correlation_id=correlation_id()).data
        self.assertEqual(self.advisor.calls, 1)
        self.assertEqual(saved["narrative"], preview["narrative"])
        self.assertEqual(saved["plan"]["planned_expenses"], preview["plan"]["planned_expenses"])
        self.assertNotIn("운동", preview["preview_token"])

    def test_revision_token_reuses_preview_and_idempotent_confirmation(self):
        self.activate()
        payload = {**plan_payload(budget=350_000), "base_version": 1, "reason": "변경"}
        preview = self.service.preview_spending_plan_revision(self.user, payload).data
        confirmed = {**payload, "apply": True, "preview_token": preview["preview_token"]}
        saved = self.service.apply_spending_plan_revision(self.user, confirmed, idempotency_key="review-revise", correlation_id=correlation_id())
        repeated = self.service.apply_spending_plan_revision(self.user, confirmed, idempotency_key="review-revise", correlation_id=correlation_id())
        self.assertEqual(saved.data["narrative"], preview["revision_preview"]["narrative"])
        self.assertEqual(saved.data, repeated.data)
        self.assertEqual(self.advisor.calls, 2)

    def test_tampered_or_other_owner_preview_is_rejected(self):
        payload = plan_payload()
        token = self.service.preview_spending_plan(self.user, payload).data["preview_token"]
        for owner, supplied in [(self.user, token[:-3] + "xyz"), ("usr_other", token)]:
            with self.assertRaises(ServiceError) as caught:
                self.service.activate_spending_plan(owner, {**payload, "confirmed": True, "preview_token": supplied}, idempotency_key="bad-token", correlation_id=correlation_id())
            self.assertEqual(caught.exception.code, "invalid_plan_preview")
            self.assertIsNone(self.repository.get_spending_plan(owner))

    def test_new_evidence_or_changed_input_requires_review_again(self):
        self.activate()
        payload = {**plan_payload(), "base_version": 1}
        token = self.service.preview_spending_plan_revision(self.user, payload).data["preview_token"]
        self.expense()
        for changed in [payload, {**payload, "confirmed_budget_krw": 999_000}]:
            with self.assertRaises(ServiceError) as caught:
                self.service.apply_spending_plan_revision(self.user, {**changed, "apply": True, "preview_token": token}, idempotency_key="changed-evidence", correlation_id=correlation_id())
            self.assertEqual(caught.exception.code, "plan_preview_conflict")
        self.assertEqual(self.repository.get_spending_plan(self.user).version, 1)
        self.assertEqual(self.advisor.calls, 2)

    def test_evidence_changed_during_advice_is_not_marked_as_reviewed(self):
        original_advise = self.advisor.advise

        def advise_while_transaction_arrives(request):
            self.expense()
            return original_advise(request)

        self.advisor.advise = advise_while_transaction_arrives
        payload = plan_payload()
        preview = self.service.preview_spending_plan(self.user, payload).data
        with self.assertRaises(ServiceError) as caught:
            self.service.activate_spending_plan(
                self.user,
                {**payload, "confirmed": True, "preview_token": preview["preview_token"]},
                idempotency_key="changed-during-review",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.code, "plan_preview_conflict")
        self.assertIsNone(self.repository.get_spending_plan(self.user))
        self.assertEqual(self.advisor.calls, 1)

    def test_removed_matched_expense_does_not_match_a_new_expense_by_position(self):
        self.activate()
        transaction = self.expense()
        self.service.match_planned_expense(self.user, "planned-class", {"transaction_id": transaction["transaction_id"]}, idempotency_key="match", correlation_id=correlation_id())
        current = self.repository.get_spending_plan(self.user)
        self.repository._users[self.user].spending_plan = self.privacy.encrypt_json(replace(current, planned_expenses=[replace(current.planned_expenses[0], planned_expense_id="planned-1")]).to_dict())
        preview = self.service.preview_spending_plan_revision(self.user, {"base_version": 1, "period_start": "2026-10-12", "period_end": "2026-10-18", "confirmed_budget_krw": 200_000, "planned_expenses": [{"name": "새 약속", "amount_krw": 30_000, "due_date": "2026-10-16", "category": "food"}]}).data
        expense = preview["plan"]["planned_expenses"][0]
        self.assertNotEqual(expense["planned_expense_id"], "planned-1")
        self.assertIsNone(expense["matched_transaction_id"])
        self.assertEqual(preview["progress"]["reserved_remaining_krw"], 30_000)
        self.assertEqual(preview["progress"]["flexible_remaining_krw"], 170_000)

    def test_client_cannot_inject_a_match_for_a_new_expense(self):
        self.activate()
        transaction = self.expense()
        with self.assertRaises(ServiceError):
            self.service.preview_spending_plan_revision(self.user, {"base_version": 1, "planned_expenses": [{"planned_expense_id": "new", "name": "새 지출", "amount_krw": 20_000, "due_date": "2026-09-20", "matched_transaction_id": transaction["transaction_id"], "matched_at": "2026-09-20T03:00:00Z"}]})

    def test_stale_narrative_uses_current_numbers_without_model_call(self):
        self.activate()
        self.expense(250_000)
        result = self.service.get_spending_plan(self.user).data
        self.assertEqual(result["progress"]["shortfall_krw"], 50_000)
        self.assertIn("부족", result["narrative"]["explanation"])
        self.assertEqual(result["narrative"]["display_reason"], "data_changed")
        self.assertEqual(self.advisor.calls, 1)
        self.assertEqual(self.repository.get_spending_plan(self.user).narrative["headline"], "확정한 계획을 차분하게 이어가요.")

    def test_legacy_english_plan_and_transaction_display_korean_without_audit_rewrite(self):
        self.activate()
        current = self.repository.get_spending_plan(self.user)
        legacy = {**current.narrative, "headline": "Review spending", "explanation": "You are over budget", "next_action": "Reduce delivery"}
        self.repository._users[self.user].spending_plan = self.privacy.encrypt_json(replace(current, narrative=legacy).to_dict())
        self.assertEqual(self.service.get_spending_plan(self.user).data["narrative"]["display_reason"], "language_repaired")
        transaction = self.expense()
        judgment = self.repository.get_judgment_for_transaction(self.user, transaction["transaction_id"])
        legacy_judgment = replace(judgment, rationale="Your budget is stretched", recommended_action="Reduce shopping", normal_message="Watch your spending")
        self.repository._users[self.user].judgments[judgment.judgment_id] = self.privacy.encrypt_json(legacy_judgment.to_dict())
        shown = self.service._render(self.user, legacy_judgment)
        self.assertNotIn("Your", shown["rationale"])
        self.assertTrue(shown["language_repaired"])
        self.assertEqual(shown["label"], judgment.label)
        self.assertEqual(shown["confidence"], judgment.confidence)
        self.assertEqual(self.repository.get_judgment(self.user, judgment.judgment_id).rationale, "Your budget is stretched")

    def test_deleted_or_excluded_matched_transaction_restores_reservation(self):
        self.activate()
        transaction = self.expense()
        self.service.match_planned_expense(self.user, "planned-class", {"transaction_id": transaction["transaction_id"]}, idempotency_key="match", correlation_id=correlation_id())
        original = self.repository.get_transaction(self.user, transaction["transaction_id"])
        self.repository._users[self.user].transactions[original.transaction_id] = self.privacy.encrypt_json(replace(original, exclude_from_budget=True).to_dict())
        result = self.service.get_spending_plan(self.user).data
        self.assertEqual(result["progress"]["actual_spent_krw"], 0)
        self.assertEqual(result["progress"]["reserved_remaining_krw"], 100_000)
        self.assertIsNone(result["plan"]["planned_expenses"][0]["matched_transaction_id"])

    def test_aggregate_evidence_is_bounded_to_the_plan_period(self):
        self.activate()
        self.expense()
        self.service.create_transaction(self.user, {"amount_krw": 999_000, "category": "shopping", "occurred_at": "2026-08-20T03:00:00Z"}, idempotency_key="outside", correlation_id=correlation_id())
        plan = self.repository.get_spending_plan(self.user)
        request = self.service._plan_advice_request(self.user, plan, self.service._plan_progress(self.user, plan))
        self.assertEqual(request.aggregate_patterns["category_spend_krw"], {"health": 70_000})
        self.assertIn("period_status", request.deterministic_progress)


if __name__ == "__main__":
    unittest.main()
