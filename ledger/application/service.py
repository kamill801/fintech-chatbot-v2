from __future__ import annotations

import logging
from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from math import ceil
from typing import Any, Callable, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from ledger.adapters.manual import ManualTransactionDraft, ManualTransactionSource
from ledger.adapters.openai_judge import JudgmentRequest
from ledger.adapters.openai_planner import (
    PlanAdviceRequest,
    PlanNarrative,
    deterministic_plan_narrative,
)
from ledger.adapters.synthetic import ProviderUnavailableError
from ledger.application.signals import POLICY_VERSION, SignalInputs, clamp, compute_signal_set
from ledger.domain.models import (
    ALLOWED_JUDGMENT_LABELS,
    ALLOWED_SPENDING_REFLECTIONS,
    DomainValidationError,
    FinancialGoal,
    FinancialProfile,
    JudgmentResult,
    LedgerAccount,
    PendingQuestion,
    Transaction,
    UserSettings,
    parse_date,
    parse_utc_datetime,
    utc_now_iso,
)
from ledger.domain.ports import LedgerRepository, ReadOnlyAccountAdapter
from ledger.domain.plans import (
    PlanCheckIn,
    PlannedExpense,
    PlanPriority,
    PlanRevision,
    SpendingPlan,
    compute_plan_progress,
    default_allocations,
)
from ledger.privacy import sanitize_free_text, sanitize_share_payload
from ledger.quota import JudgmentQuotaLimiter, QuotaExceededError, QuotaUnavailableError
from ledger.rendering import render_judgment
from ledger.telemetry import TelemetryEvent, confidence_band

logger = logging.getLogger(__name__)

CATEGORY_NAMES_KO = {
    "cafe": "카페·간식",
    "food": "식비",
    "food_delivery": "배달",
    "transport": "교통",
    "shopping": "쇼핑",
    "housing": "주거",
    "health": "건강",
    "other": "기타",
    "unknown": "기타",
}


class Judge(Protocol):
    def judge(self, request: JudgmentRequest) -> JudgmentResult: ...


class PlanAdvisor(Protocol):
    def advise(self, request: PlanAdviceRequest) -> PlanNarrative: ...


class DeterministicPlanAdvisor:
    def advise(self, request: PlanAdviceRequest) -> PlanNarrative:
        return deterministic_plan_narrative(request)


class ServiceError(RuntimeError):
    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class JudgmentQuotaError(ServiceError):
    pass


@dataclass(frozen=True)
class ServiceResult:
    status: int
    data: dict[str, Any] | None = None


class LedgerService:
    def __init__(
        self,
        repository: LedgerRepository,
        judge: Judge,
        account_adapter: ReadOnlyAccountAdapter,
        *,
        telemetry_sink: Callable[[dict[str, Any]], Any] | None = None,
        judgment_quota: JudgmentQuotaLimiter | None = None,
        plan_advisor: PlanAdvisor | None = None,
    ) -> None:
        self.repository = repository
        self.judge = judge
        self.account_adapter = account_adapter
        self.manual_source = ManualTransactionSource()
        self.telemetry_sink = telemetry_sink
        self.judgment_quota = judgment_quota
        self.plan_advisor = plan_advisor or DeterministicPlanAdvisor()

    def get_profile(self, user_ref: str) -> ServiceResult:
        profile = self.repository.get_profile(user_ref)
        return ServiceResult(200, {"profile": profile.to_dict() if profile else None})

    def upsert_profile(
        self,
        user_ref: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        existing = self.repository.get_profile(user_ref)
        now = utc_now_iso()
        goal_payload = dict(payload.get("goal") or {})
        goal = FinancialGoal(
            goal_id=str(goal_payload.get("goal_id") or uuid4()),
            name=str(goal_payload.get("name") or ""),
            target_amount_krw=_integer(goal_payload, "target_amount_krw"),
            current_amount_krw=_integer(goal_payload, "current_amount_krw"),
            target_date=str(goal_payload.get("target_date") or ""),
        )
        if existing is None and parse_date(goal.target_date, "goal.target_date") < date.today():
            raise ServiceError(
                "invalid_goal_date", "goal target date cannot be in the past", 400
            )
        profile = FinancialProfile(
            user_ref=user_ref,
            monthly_income_krw=_integer(payload, "monthly_income_krw"),
            liquid_assets_krw=_integer(payload, "liquid_assets_krw"),
            fixed_expenses_krw=_integer(payload, "fixed_expenses_krw"),
            monthly_debt_payment_krw=_integer(
                payload, "monthly_debt_payment_krw"
            ),
            discretionary_budget_krw=_integer(
                payload, "discretionary_budget_krw"
            ),
            goal=goal,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        stored = self.repository.upsert_profile(
            profile,
            idempotency_key=_key("profile", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, stored.body)

    def get_settings(self, user_ref: str) -> ServiceResult:
        return ServiceResult(200, {"settings": self.repository.get_settings(user_ref).to_dict()})

    def update_settings(
        self,
        user_ref: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        current = self.repository.get_settings(user_ref)
        settings = UserSettings(
            roast_enabled=payload.get("roast_enabled", current.roast_enabled),
            locale=str(payload.get("locale", current.locale)),
            timezone=str(payload.get("timezone", current.timezone)),
            spending_rules=_spending_rules(
                payload.get("spending_rules", current.spending_rules)
            ),
            accounts=_ledger_accounts(payload.get("accounts", current.accounts)),
            category_budgets_krw=_category_budgets(
                payload.get("category_budgets_krw", current.category_budgets_krw)
            ),
        )
        stored = self.repository.update_settings(
            user_ref,
            settings,
            idempotency_key=_key("settings", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, stored.body)

    def get_spending_plan(self, user_ref: str) -> ServiceResult:
        plan = self.repository.get_spending_plan(user_ref)
        if plan is None:
            return ServiceResult(200, {"plan": None})
        return ServiceResult(200, self._spending_plan_payload(user_ref, plan))

    def preview_spending_plan(
        self, user_ref: str, payload: dict[str, Any]
    ) -> ServiceResult:
        if self.repository.get_spending_plan(user_ref) is not None:
            raise ServiceError(
                "active_plan_exists",
                "활성 계획은 수정 미리보기를 통해 바꿔 주세요.",
                409,
            )
        plan = self._with_plan_narrative(
            user_ref, self._build_spending_plan(user_ref, payload, status="draft")
        )
        return ServiceResult(200, self._spending_plan_payload(user_ref, plan, preview=True))

    def activate_spending_plan(
        self,
        user_ref: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        response_key = _key("plan-activate-response", idempotency_key)
        cached = self.repository.get_cached_result(user_ref, response_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        if payload.get("confirmed") is not True:
            raise ServiceError("confirmation_required", "계획 내용을 확인해 주세요.", 400)
        if self.repository.get_spending_plan(user_ref) is not None:
            raise ServiceError("active_plan_exists", "이미 활성 계획이 있어요.", 409)
        plan = self._with_plan_narrative(
            user_ref, self._build_spending_plan(user_ref, payload, status="active")
        )
        stored = self.repository.activate_spending_plan(
            plan,
            idempotency_key=_key("plan-activate", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        saved = SpendingPlan.from_dict(stored.body["plan"])
        return self._cache_service_result(
            user_ref,
            response_key,
            ServiceResult(201, self._spending_plan_payload(user_ref, saved)),
        )

    def preview_spending_plan_revision(
        self, user_ref: str, payload: dict[str, Any]
    ) -> ServiceResult:
        current = self._require_spending_plan(user_ref)
        candidate = self._with_plan_narrative(
            user_ref, self._build_revision_candidate(current, payload)
        )
        return ServiceResult(
            200,
            {
                "revision_preview": self._revision_diff(user_ref, current, candidate),
                "plan": candidate.to_dict(),
                "progress": self._plan_progress(user_ref, candidate),
            },
        )

    def apply_spending_plan_revision(
        self,
        user_ref: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        response_key = _key("plan-revise-response", idempotency_key)
        cached = self.repository.get_cached_result(user_ref, response_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        if payload.get("apply") is not True:
            raise ServiceError("confirmation_required", "변경 내용을 적용해 주세요.", 400)
        current = self._require_spending_plan(user_ref)
        candidate = self._with_plan_narrative(
            user_ref, self._build_revision_candidate(current, payload)
        )
        applied_at = utc_now_iso()
        revision = PlanRevision(
            revision_id=str(uuid4()),
            from_version=current.version,
            to_version=candidate.version,
            reason=_optional_text(payload.get("reason"), max_length=200),
            applied_at=applied_at,
            before=current.snapshot(),
            after=candidate.snapshot(),
        )
        candidate = replace(
            candidate,
            revisions=[*current.revisions, revision],
            check_ins=list(current.check_ins),
            updated_at=applied_at,
        )
        stored = self.repository.revise_spending_plan(
            candidate,
            idempotency_key=_key("plan-revise", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        saved = SpendingPlan.from_dict(stored.body["plan"])
        return self._cache_service_result(
            user_ref,
            response_key,
            ServiceResult(200, self._spending_plan_payload(user_ref, saved)),
        )

    def check_in_spending_plan(
        self,
        user_ref: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        response_key = _key("plan-check-in-response", idempotency_key)
        cached = self.repository.get_cached_result(user_ref, response_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        current = self._require_spending_plan(user_ref)
        decision = str(payload.get("decision", "")).strip()
        check_in = PlanCheckIn(
            check_in_id=str(uuid4()),
            decision=decision,
            note=_optional_text(payload.get("note"), max_length=200),
            checked_in_at=utc_now_iso(),
            plan_version=current.version,
        )
        updated = replace(
            current,
            check_ins=[*current.check_ins, check_in],
            updated_at=check_in.checked_in_at,
        )
        stored = self.repository.check_in_spending_plan(
            updated,
            idempotency_key=_key("plan-check-in", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        saved = SpendingPlan.from_dict(stored.body["plan"])
        data = self._spending_plan_payload(user_ref, saved)
        data["check_in"] = check_in.to_dict()
        data["next_step"] = "revision_preview" if decision == "adjust" else "continue"
        return self._cache_service_result(
            user_ref, response_key, ServiceResult(200, data)
        )

    def match_planned_expense(
        self,
        user_ref: str,
        planned_expense_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        response_key = _key("plan-match-response", idempotency_key)
        cached = self.repository.get_cached_result(user_ref, response_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        current = self._require_spending_plan(user_ref)
        transaction_id = str(payload.get("transaction_id", "")).strip()
        transaction = self._require_transaction(user_ref, transaction_id)
        if transaction.transaction_type != "expense" or transaction.exclude_from_budget:
            raise ServiceError(
                "ineligible_transaction",
                "예산에 포함된 지출만 예정 지출과 연결할 수 있어요.",
                400,
            )
        settings = self.repository.get_settings(user_ref)
        local_date = parse_utc_datetime(transaction.occurred_at, "occurred_at").astimezone(
            _safe_timezone(settings.timezone)
        ).date()
        if not parse_date(current.period_start, "period_start") <= local_date <= parse_date(current.period_end, "period_end"):
            raise ServiceError("transaction_outside_plan", "계획 기간 안의 지출을 선택해 주세요.", 400)
        if any(
            item.matched_transaction_id == transaction_id
            for item in current.planned_expenses
            if item.planned_expense_id != planned_expense_id
        ):
            raise ServiceError("transaction_already_matched", "이미 다른 예정 지출과 연결됐어요.", 409)
        found = False
        matched_at = utc_now_iso()
        expenses: list[PlannedExpense] = []
        for item in current.planned_expenses:
            if item.planned_expense_id != planned_expense_id:
                expenses.append(item)
                continue
            found = True
            if item.matched_transaction_id and item.matched_transaction_id != transaction_id:
                raise ServiceError("planned_expense_already_matched", "이미 실제 지출과 연결됐어요.", 409)
            expenses.append(replace(item, matched_transaction_id=transaction_id, matched_at=matched_at))
        if not found:
            raise ServiceError("planned_expense_not_found", "예정 지출을 찾지 못했어요.", 404)
        updated = replace(current, planned_expenses=expenses, updated_at=matched_at)
        stored = self.repository.match_planned_expense(
            updated,
            planned_expense_id,
            transaction_id,
            idempotency_key=_key("plan-match", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        saved = SpendingPlan.from_dict(stored.body["plan"])
        data = self._spending_plan_payload(user_ref, saved)
        data["matched_planned_expense_id"] = planned_expense_id
        data["matched_transaction_id"] = transaction_id
        return self._cache_service_result(
            user_ref, response_key, ServiceResult(200, data)
        )

    def list_transactions(self, user_ref: str) -> ServiceResult:
        transactions = [
            item.to_dict()
            for item in sorted(
                self.repository.list_transactions(user_ref),
                key=lambda item: (item.occurred_at, item.created_at, item.transaction_id),
                reverse=True,
            )
        ]
        return ServiceResult(200, {"transactions": transactions})

    def get_transaction(self, user_ref: str, transaction_id: str) -> ServiceResult:
        transaction = self._require_transaction(user_ref, transaction_id)
        data: dict[str, Any] = {"transaction": transaction.to_dict()}
        judgment = self.repository.get_judgment_for_transaction(user_ref, transaction_id)
        if judgment:
            rendered = self._render(user_ref, judgment)
            correction = self.repository.get_judgment_correction(
                user_ref, judgment.judgment_id
            )
            rendered["original_label"] = judgment.label
            rendered["effective_label"] = (
                correction.corrected_label if correction else judgment.label
            )
            rendered["correction"] = correction.to_dict() if correction else None
            data["judgment"] = rendered
        pending = self.repository.get_pending_question(user_ref)
        if pending and pending.transaction_id == transaction_id and pending.answered_at is None:
            data["pending_question"] = pending.to_dict()
        return ServiceResult(200, data)

    def create_transaction(
        self,
        user_ref: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        response_key = _key("transaction-response", idempotency_key)
        cached = self.repository.get_cached_result(user_ref, response_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        profile = self.repository.get_profile(user_ref)
        if profile is None:
            raise ServiceError(
                "profile_required",
                "complete the financial profile before recording transactions",
                409,
            )
        settings = self.repository.get_settings(user_ref)
        transaction_type = _transaction_type(payload.get("transaction_type"))
        active_pending = self.repository.get_pending_question(user_ref)
        if (
            transaction_type == "expense"
            and settings.roast_enabled
            and active_pending is not None
            and active_pending.answered_at is None
        ):
            raise ServiceError(
                "pending_reason_required",
                "먼저 이전 지출의 이유를 답해 주세요.",
                409,
            )
        occurred_at = str(payload.get("occurred_at") or utc_now_iso())
        draft = ManualTransactionDraft(
            user_ref=user_ref,
            amount_krw=_integer(payload, "amount_krw"),
            category=_normalized_category(payload.get("category")),
            occurred_at=occurred_at,
            merchant=_optional_text(payload.get("merchant"), max_length=120),
            description=_optional_text(payload.get("description"), max_length=500),
            reason=_optional_text(payload.get("reason"), max_length=500),
            idempotency_key=idempotency_key,
            transaction_type=transaction_type,
            account_id=_account_id(payload.get("account_id"), default="cash"),
            destination_account_id=_account_id(
                payload.get("destination_account_id"), default=None
            ),
            exclude_from_budget=_boolean(
                payload.get("exclude_from_budget", False), "exclude_from_budget"
            ),
        )
        transaction = self.manual_source.create_record(draft)
        _validate_transaction_accounts(settings, transaction)
        transaction_record_key = _key("transaction-record", idempotency_key)
        recorded = self.repository.get_cached_result(user_ref, transaction_record_key)
        quota_prechecked = False
        requires_interactive_reason = (
            transaction.transaction_type == "expense"
            and settings.roast_enabled
            and not transaction.reason
        )
        if recorded is None:
            if transaction.transaction_type == "expense" and not requires_interactive_reason:
                self._consume_judgment_quota(user_ref)
                quota_prechecked = True
            recorded = self.repository.record_transaction(
                transaction,
                idempotency_key=transaction_record_key,
                correlation_id=correlation_id,
                source=source,
            )
        transaction = Transaction.from_dict(recorded.body["transaction"])
        if transaction.transaction_type != "expense":
            result = ServiceResult(201, {"transaction": transaction.to_dict()})
            return self._cache_service_result(user_ref, response_key, result)
        existing = self._existing_transaction_result(user_ref, transaction)
        if existing:
            return self._cache_service_result(
                user_ref, response_key, self._attach_plan_impact(user_ref, transaction, existing)
            )

        signals = self._compute_signals(profile, transaction)
        if requires_interactive_reason:
            question = PendingQuestion(
                question_id=str(uuid4()),
                transaction_id=transaction.transaction_id,
                question="그래, 이 돈은 왜 썼는지 한 번 말해봐.",
                asked_at=utc_now_iso(),
            )
            pending = self.repository.save_pending_question(
                user_ref,
                question,
                idempotency_key=_key("reason-question", idempotency_key),
                correlation_id=correlation_id,
                source=source,
            )
            self._emit_telemetry(
                user_ref,
                event_type="judgment.reason_requested",
                event_id=question.question_id,
                adapter_source=transaction.source,
                reason_question_asked=True,
                policy_version=POLICY_VERSION,
            )
            result = ServiceResult(
                202,
                {
                    "transaction": self.repository.get_transaction(
                        user_ref, transaction.transaction_id
                    ).to_dict(),
                    "signals": signals.to_dict(),
                    **pending.body,
                },
            )
            return self._cache_service_result(
                user_ref, response_key, self._attach_plan_impact(user_ref, transaction, result)
            )
        result = self._complete_judgment(
            user_ref,
            transaction,
            signals,
            idempotency_key=_key("judgment", idempotency_key),
            correlation_id=correlation_id,
            source=source,
            quota_prechecked=quota_prechecked,
        )
        return self._cache_service_result(
            user_ref, response_key, self._attach_plan_impact(user_ref, transaction, result)
        )

    def update_transaction(
        self,
        user_ref: str,
        transaction_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        response_key = _key(f"transaction-update-response:{transaction_id}", idempotency_key)
        cached = self.repository.get_cached_result(user_ref, response_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        existing = self._require_transaction(user_ref, transaction_id)
        settings = self.repository.get_settings(user_ref)
        profile = self.repository.get_profile(user_ref)
        transaction_type = _transaction_type(
            payload.get("transaction_type", existing.transaction_type)
        )
        updated = Transaction(
            transaction_id=existing.transaction_id,
            user_ref=user_ref,
            amount_krw=_integer(payload, "amount_krw")
            if "amount_krw" in payload
            else existing.amount_krw,
            category=_normalized_category(payload.get("category", existing.category)),
            occurred_at=str(payload.get("occurred_at", existing.occurred_at)),
            source=existing.source,
            source_reference=existing.source_reference,
            merchant=_optional_text(
                payload.get("merchant", existing.merchant), max_length=120
            ),
            description=_optional_text(
                payload.get("description", existing.description), max_length=500
            ),
            reason=(
                _optional_text(payload.get("reason", existing.reason), max_length=500)
                if transaction_type == "expense"
                else None
            ),
            status="recorded",
            created_at=existing.created_at,
            reflection=existing.reflection if transaction_type == "expense" else None,
            reflection_note=(
                existing.reflection_note if transaction_type == "expense" else None
            ),
            reflected_at=existing.reflected_at if transaction_type == "expense" else None,
            transaction_type=transaction_type,
            account_id=_account_id(
                payload.get("account_id", existing.account_id), default="cash"
            ),
            destination_account_id=(
                _account_id(
                    payload.get(
                        "destination_account_id", existing.destination_account_id
                    ),
                    default=None,
                )
                if transaction_type == "transfer"
                else None
            ),
            exclude_from_budget=(
                _boolean(
                    payload.get("exclude_from_budget", existing.exclude_from_budget),
                    "exclude_from_budget",
                )
                if transaction_type == "expense"
                else False
            ),
            updated_at=utc_now_iso(),
        )
        _validate_transaction_accounts(settings, updated)
        requires_interactive_reason = (
            transaction_type == "expense"
            and settings.roast_enabled
            and not updated.reason
        )
        quota_prechecked = False
        if transaction_type == "expense":
            if profile is None:
                raise ServiceError("profile_required", "financial profile is missing", 409)
            if not requires_interactive_reason:
                self._consume_judgment_quota(user_ref)
                quota_prechecked = True
        stored = self.repository.update_transaction(
            updated,
            idempotency_key=_key(f"transaction-update:{transaction_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        updated = Transaction.from_dict(stored.body["transaction"])
        if transaction_type != "expense":
            return self._cache_service_result(
                user_ref,
                response_key,
                ServiceResult(200, {"transaction": updated.to_dict()}),
            )
        signals = self._compute_signals(profile, updated)
        if requires_interactive_reason:
            question = PendingQuestion(
                question_id=str(uuid4()),
                transaction_id=updated.transaction_id,
                question="고친 지출도 이유는 남겨야지. 왜 썼는지 말해봐.",
                asked_at=utc_now_iso(),
            )
            pending = self.repository.save_pending_question(
                user_ref,
                question,
                idempotency_key=_key(f"transaction-update-question:{transaction_id}", idempotency_key),
                correlation_id=correlation_id,
                source=source,
            )
            return self._cache_service_result(
                user_ref,
                response_key,
                ServiceResult(
                    202,
                    {
                        "transaction": self.repository.get_transaction(
                            user_ref, transaction_id
                        ).to_dict(),
                        "signals": signals.to_dict(),
                        **pending.body,
                    },
                ),
            )
        judged = self._complete_judgment(
            user_ref,
            updated,
            signals,
            idempotency_key=_key(f"transaction-update-judgment:{transaction_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
            quota_prechecked=quota_prechecked,
        )
        return self._cache_service_result(
            user_ref, response_key, ServiceResult(200, judged.data)
        )

    def delete_transaction(
        self,
        user_ref: str,
        transaction_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        operation_key = _key(
            f"transaction-delete:{transaction_id}", idempotency_key
        )
        cached = self.repository.get_cached_result(user_ref, operation_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        self._require_transaction(user_ref, transaction_id)
        stored = self.repository.delete_transaction(
            user_ref,
            transaction_id,
            idempotency_key=operation_key,
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, stored.body)

    def add_reason(
        self,
        user_ref: str,
        transaction_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        response_key = _key(f"reason-response:{transaction_id}", idempotency_key)
        cached = self.repository.get_cached_result(user_ref, response_key)
        if cached:
            return ServiceResult(cached.status, cached.body)
        transaction = self._require_transaction(user_ref, transaction_id)
        existing = self.repository.get_judgment_for_transaction(user_ref, transaction_id)
        if existing:
            return self._cache_service_result(user_ref, response_key, ServiceResult(
                200,
                {"transaction": transaction.to_dict(), "judgment": self._render(user_ref, existing)},
            ))
        pending = self.repository.get_pending_question(user_ref)
        if pending is None or pending.transaction_id != transaction_id:
            raise ServiceError(
                "reason_not_requested", "this transaction is not awaiting a reason", 409
            )
        reason = _optional_text(payload.get("reason"), max_length=500)
        if not reason:
            raise ServiceError("reason_required", "reason is required", 400)
        profile = self.repository.get_profile(user_ref)
        if profile is None:
            raise ServiceError("profile_required", "financial profile is missing", 409)
        reason_record_key = _key(f"reason:{transaction_id}", idempotency_key)
        stored = self.repository.get_cached_result(user_ref, reason_record_key)
        quota_prechecked = False
        if stored is None:
            self._consume_judgment_quota(user_ref)
            quota_prechecked = True
            stored = self.repository.add_transaction_reason(
                user_ref,
                transaction_id,
                reason,
                answered_at=utc_now_iso(),
                idempotency_key=reason_record_key,
                correlation_id=correlation_id,
                source=source,
            )
        transaction = Transaction.from_dict(stored.body["transaction"])
        signals = self._compute_signals(profile, transaction)
        result = self._complete_judgment(
            user_ref,
            transaction,
            signals,
            idempotency_key=_key(f"reason-judgment:{transaction_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
            quota_prechecked=quota_prechecked,
        )
        return self._cache_service_result(user_ref, response_key, result)

    def correct_judgment(
        self,
        user_ref: str,
        judgment_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        if self.repository.get_judgment(user_ref, judgment_id) is None:
            raise ServiceError("judgment_not_found", "judgment was not found", 404)
        corrected_label = str(payload.get("corrected_label") or "")
        if corrected_label not in ALLOWED_JUDGMENT_LABELS:
            raise ServiceError("invalid_label", "corrected_label is not allowed", 400)
        stored = self.repository.correct_judgment(
            user_ref,
            judgment_id,
            corrected_label,
            correction_reason=_optional_text(
                payload.get("correction_reason"), max_length=500
            ),
            idempotency_key=_key(f"correction:{judgment_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        self._emit_telemetry(
            user_ref,
            event_type="judgment.corrected",
            event_id=str(uuid4()),
            correction_flag=True,
            policy_version=POLICY_VERSION,
        )
        return ServiceResult(stored.status, stored.body)

    def reflect_transaction(
        self,
        user_ref: str,
        transaction_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        transaction = self._require_transaction(user_ref, transaction_id)
        if transaction.transaction_type != "expense":
            raise ServiceError(
                "reflection_not_allowed",
                "only expense transactions can have a spending reflection",
                409,
            )
        reflection = str(payload.get("reflection") or "")
        if reflection not in ALLOWED_SPENDING_REFLECTIONS:
            raise ServiceError(
                "invalid_reflection",
                "reflection must be well_spent, unsure, or regretted",
                400,
            )
        stored = self.repository.reflect_transaction(
            user_ref,
            transaction_id,
            reflection,
            reflection_note=_optional_text(
                payload.get("reflection_note"), max_length=160
            ),
            reflected_at=utc_now_iso(),
            idempotency_key=_key(f"reflection:{transaction_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, stored.body)

    def record_share_view(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        self._require_roast_judgment(user_ref, judgment_id)
        stored = self.repository.record_share_view(
            user_ref,
            judgment_id,
            idempotency_key=_key(f"share-view:{judgment_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, stored.body)

    def share_judgment(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        judgment = self._require_roast_judgment(user_ref, judgment_id)
        transaction = self._require_transaction(user_ref, judgment.transaction_id)
        correction = self.repository.get_judgment_correction(user_ref, judgment_id)
        effective_label = correction.corrected_label if correction else judgment.label
        stored = self.repository.record_share_click(
            user_ref,
            judgment_id,
            idempotency_key=_key(f"share:{judgment_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        share = sanitize_share_payload(
            {
                "label": effective_label,
                "roast_message": (
                    _corrected_share_message(effective_label)
                    if correction
                    else render_judgment(judgment, roast_enabled=True).message
                ),
                "category": transaction.category,
                "recommended_action": judgment.recommended_action,
            }
        )
        self._emit_telemetry(
            user_ref,
            event_type="share.clicked",
            event_id=str(uuid4()),
            label=effective_label,
            share_flag=True,
            policy_version=judgment.policy_version,
        )
        return ServiceResult(stored.status, {"share": share})

    def record_share_success(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        judgment = self._require_roast_judgment(user_ref, judgment_id)
        correction = self.repository.get_judgment_correction(user_ref, judgment_id)
        effective_label = correction.corrected_label if correction else judgment.label
        stored = self.repository.record_share_success(
            user_ref,
            judgment_id,
            idempotency_key=_key(f"share-success:{judgment_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        self._emit_telemetry(
            user_ref,
            event_type="share.succeeded",
            event_id=str(uuid4()),
            label=effective_label,
            share_flag=True,
            policy_version=judgment.policy_version,
        )
        return ServiceResult(stored.status, stored.body)

    def get_summary(self, user_ref: str) -> ServiceResult:
        profile = self.repository.get_profile(user_ref)
        transactions = list(self.repository.list_transactions(user_ref))
        settings = self.repository.get_settings(user_ref)
        try:
            timezone = ZoneInfo(settings.timezone)
        except Exception:
            timezone = ZoneInfo("Asia/Seoul")
        now = datetime.now(UTC).astimezone(timezone)
        current = [
            transaction
            for transaction in transactions
            if _same_month(
                parse_utc_datetime(transaction.occurred_at, "occurred_at").astimezone(timezone),
                now,
            )
        ]
        previous_month_anchor = (now.replace(day=1) - timedelta(days=1))
        previous = [
            transaction
            for transaction in transactions
            if _same_month(
                parse_utc_datetime(transaction.occurred_at, "occurred_at").astimezone(timezone),
                previous_month_anchor,
            )
        ]
        current_expenses = [
            item for item in current if item.transaction_type == "expense"
        ]
        current_income = [item for item in current if item.transaction_type == "income"]
        current_transfers = [
            item for item in current if item.transaction_type == "transfer"
        ]
        budget_expenses = [
            item for item in current_expenses if not item.exclude_from_budget
        ]
        previous_expenses = [
            item for item in previous if item.transaction_type == "expense"
        ]
        by_category: dict[str, int] = {}
        for transaction in current_expenses:
            by_category[transaction.category] = (
                by_category.get(transaction.category, 0) + transaction.amount_krw
            )
        total = sum(transaction.amount_krw for transaction in current_expenses)
        budget_spent = sum(transaction.amount_krw for transaction in budget_expenses)
        income_total = sum(transaction.amount_krw for transaction in current_income)
        transfer_total = sum(transaction.amount_krw for transaction in current_transfers)
        previous_total = sum(transaction.amount_krw for transaction in previous_expenses)
        days_remaining = monthrange(now.year, now.month)[1] - now.day + 1
        category_budgets = {
            category: {
                "budget_krw": budget,
                "spent_krw": sum(
                    item.amount_krw
                    for item in budget_expenses
                    if item.category == category
                ),
            }
            for category, budget in settings.category_budgets_krw.items()
        }
        for values in category_budgets.values():
            values["remaining_krw"] = max(0, values["budget_krw"] - values["spent_krw"])
            values["usage"] = round(values["spent_krw"] / values["budget_krw"], 4)
            values["daily_allowance_krw"] = values["remaining_krw"] // max(1, days_remaining)
        summary: dict[str, Any] = {
            "month": now.strftime("%Y-%m"),
            "total_spent_krw": total,
            "budget_spent_krw": budget_spent,
            "total_income_krw": income_total,
            "net_cashflow_krw": income_total - total,
            "transfer_total_krw": transfer_total,
            "by_category_krw": by_category,
            "transaction_count": len(current),
            "expense_count": len(current_expenses),
            "income_count": len(current_income),
            "transfer_count": len(current_transfers),
            "previous_month": {
                "month": previous_month_anchor.strftime("%Y-%m"),
                "total_spent_krw": previous_total,
                "change_krw": total - previous_total,
                "change_rate": round((total - previous_total) / previous_total, 4)
                if previous_total
                else None,
            },
            "category_budgets": category_budgets,
            "account_balances": _account_balances(settings.accounts, transactions),
            "reflection_summary": self._reflection_summary(
                current_expenses,
                profile,
                as_of=now.date(),
            ),
            "weekly_briefing": self._weekly_briefing(
                user_ref,
                [item for item in transactions if item.transaction_type == "expense"],
                now=now,
                timezone=timezone,
                profile=profile,
            ),
        }
        if profile:
            summary.update(
                {
                    "discretionary_budget_krw": profile.discretionary_budget_krw,
                    "budget_usage": round(
                        budget_spent / profile.discretionary_budget_krw, 4
                    ),
                    "goal": profile.goal.to_dict(),
                }
            )
        return ServiceResult(200, {"summary": summary})

    def _reflection_summary(
        self,
        transactions: list[Transaction],
        profile: FinancialProfile | None,
        *,
        as_of: date,
    ) -> dict[str, Any]:
        reflected = [item for item in transactions if item.reflection is not None]
        regretted = [item for item in reflected if item.reflection == "regretted"]
        regretted_by_category: dict[str, tuple[int, int]] = {}
        for transaction in regretted:
            count, amount = regretted_by_category.get(transaction.category, (0, 0))
            regretted_by_category[transaction.category] = (
                count + 1,
                amount + transaction.amount_krw,
            )
        strongest_category = (
            max(
                regretted_by_category,
                key=lambda category: (
                    regretted_by_category[category][0],
                    regretted_by_category[category][1],
                ),
            )
            if regretted_by_category
            else None
        )
        regretted_spent = sum(item.amount_krw for item in regretted)
        return {
            "reflected_count": len(reflected),
            "well_spent_count": sum(
                item.reflection == "well_spent" for item in reflected
            ),
            "unsure_count": sum(item.reflection == "unsure" for item in reflected),
            "regretted_count": len(regretted),
            "regretted_spent_krw": regretted_spent,
            "regret_rate": round(len(regretted) / len(reflected), 4)
            if reflected
            else 0.0,
            "strongest_regret_category": strongest_category,
            "goal_delay_days": _goal_delay_days(regretted_spent, profile, as_of),
        }

    def _weekly_briefing(
        self,
        user_ref: str,
        transactions: list[Transaction],
        *,
        now: datetime,
        timezone: ZoneInfo,
        profile: FinancialProfile | None,
    ) -> dict[str, Any]:
        week_start = now.date() - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        weekly = [
            transaction
            for transaction in transactions
            if week_start
            <= parse_utc_datetime(transaction.occurred_at, "occurred_at")
            .astimezone(timezone)
            .date()
            <= week_end
        ]
        by_category: dict[str, int] = {}
        for transaction in weekly:
            by_category[transaction.category] = (
                by_category.get(transaction.category, 0) + transaction.amount_krw
            )
        top_category, top_amount = (
            max(by_category.items(), key=lambda item: item[1])
            if by_category
            else (None, 0)
        )

        reviewed: list[tuple[Transaction, JudgmentResult, str]] = []
        label_counts = {
            "justified": 0,
            "caution": 0,
            "overspending": 0,
            "insufficient_context": 0,
        }
        for transaction in weekly:
            judgment = self.repository.get_judgment_for_transaction(
                user_ref, transaction.transaction_id
            )
            if judgment is None:
                continue
            correction = self.repository.get_judgment_correction(
                user_ref, judgment.judgment_id
            )
            effective_label = (
                correction.corrected_label if correction else judgment.label
            )
            label_counts[effective_label] += 1
            reviewed.append((transaction, judgment, effective_label))

        priority = {
            "overspending": 3,
            "caution": 2,
            "insufficient_context": 1,
            "justified": 0,
        }
        concern = max(
            reviewed,
            key=lambda item: (priority[item[2]], item[0].amount_krw),
            default=None,
        )
        total = sum(transaction.amount_krw for transaction in weekly)
        reflected = [item for item in weekly if item.reflection is not None]
        regretted = [item for item in reflected if item.reflection == "regretted"]
        regretted_by_category: dict[str, tuple[int, int]] = {}
        for transaction in regretted:
            count, amount = regretted_by_category.get(transaction.category, (0, 0))
            regretted_by_category[transaction.category] = (
                count + 1,
                amount + transaction.amount_krw,
            )
        regret_category = (
            max(
                regretted_by_category,
                key=lambda category: (
                    regretted_by_category[category][0],
                    regretted_by_category[category][1],
                ),
            )
            if regretted_by_category
            else None
        )
        regret_pattern = None
        if regret_category:
            regret_count, regret_amount = regretted_by_category[regret_category]
            regret_pattern = {
                "category": regret_category,
                "category_name": _category_name(regret_category),
                "count": regret_count,
                "spent_krw": regret_amount,
            }
        if len(reflected) >= 2:
            evidence_state = "learned"
        elif reflected:
            evidence_state = "feedback_sparse"
        elif reviewed:
            evidence_state = "judgment_only"
        else:
            evidence_state = "empty"

        if regret_pattern:
            headline = (
                f"이번 주 {_category_name(regret_category)}에서 "
                f"후회한 소비 {regret_pattern['count']}건이 보여요."
            )
        elif label_counts["overspending"]:
            headline = f"이번 주 과소비 {label_counts['overspending']}건을 먼저 점검해요."
        elif label_counts["caution"]:
            headline = f"주의가 필요한 지출 {label_counts['caution']}건이 보여요."
        elif reviewed:
            headline = "이번 주 지출은 대체로 계획 안에 있어요."
        elif weekly:
            headline = "기록은 모였고 AI 판단을 정리하고 있어요."
        else:
            headline = "이번 주 첫 지출을 기록해 보세요."

        if weekly:
            top_category_name = _category_name(top_category)
            summary_text = (
                f"이번 주 {len(weekly)}건에 {total:,}원을 썼어요."
                + (
                    f" 가장 큰 지출 분류는 {top_category_name} {top_amount:,}원이에요."
                    if top_category
                    else ""
                )
            )
        else:
            summary_text = "거래를 기록하면 이번 주 흐름을 자동으로 묶어 드려요."

        concern_payload = None
        if regret_pattern:
            goal_name = profile.goal.name if profile else "목표"
            improvement = (
                f"이번 주 {_category_name(regret_category)} 지출을 1회 줄이고, "
                f"절약한 금액을 {goal_name}에 남겨둬요."
            )
        elif concern is not None and concern[2] != "justified":
            transaction, judgment, effective_label = concern
            concern_payload = {
                "transaction_id": transaction.transaction_id,
                "label": effective_label,
                "category": transaction.category,
                "merchant": transaction.merchant,
                "amount_krw": transaction.amount_krw,
                "rationale": judgment.rationale,
            }
            improvement = judgment.recommended_action
        elif top_category:
            improvement = (
                f"다음 지출 전에는 {_category_name(top_category)} 예산이 얼마나 남았는지 먼저 확인해요."
            )
        else:
            improvement = "지출 한 건을 기록하면 다음 행동을 구체적으로 제안해 드려요."

        return {
            "period_start": week_start.isoformat(),
            "period_end": week_end.isoformat(),
            "total_spent_krw": total,
            "transaction_count": len(weekly),
            "top_category": top_category,
            "top_category_spent_krw": top_amount,
            "judged_count": len(reviewed),
            "justified_count": label_counts["justified"],
            "caution_count": label_counts["caution"],
            "overspending_count": label_counts["overspending"],
            "insufficient_context_count": label_counts["insufficient_context"],
            "headline": headline,
            "summary": summary_text,
            "improvement": improvement,
            "concern": concern_payload,
            "evidence_state": evidence_state,
            "regret_pattern": regret_pattern,
            "goal_impact_days": _goal_delay_days(
                sum(item.amount_krw for item in regretted), profile, now.date()
            ),
        }

    def get_metrics(self, user_ref: str) -> ServiceResult:
        metrics = self.repository.get_metrics(user_ref)
        views = int(metrics.get("share_views", 0))
        clicks = int(metrics.get("share_clicks", 0))
        metrics["roast_share_rate"] = round(clicks / views, 4) if views else 0.0
        metrics["share_successes"] = int(metrics.get("share_successes", 0))
        metrics["roast_share_success_rate"] = (
            round(metrics["share_successes"] / views, 4) if views else 0.0
        )
        return ServiceResult(200, {"metrics": metrics})

    def revoke_account(
        self,
        user_ref: str,
        connection_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        try:
            self.account_adapter.revoke_connection(user_ref, connection_id)
        except ProviderUnavailableError as exc:
            raise ServiceError(exc.code, str(exc), 503) from exc
        stored = self.repository.revoke_account(
            user_ref,
            connection_id,
            idempotency_key=_key(f"revoke:{connection_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, stored.body)

    def delete_user_data(
        self,
        user_ref: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> ServiceResult:
        if (
            self.repository.get_profile(user_ref) is None
            and self.repository.get_spending_plan(user_ref) is None
            and not self.repository.list_transactions(user_ref)
            and not self.repository.list_events(user_ref)
        ):
            return ServiceResult(204, None)
        stored = self.repository.request_data_deletion(
            user_ref,
            idempotency_key=_key("data-delete", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, None)

    def import_legacy_metadata(
        self,
        user_ref: str,
        metadata: dict[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
    ) -> ServiceResult:
        stored = self.repository.import_legacy_metadata(
            user_ref,
            metadata,
            idempotency_key=_key("legacy-import", idempotency_key),
            correlation_id=correlation_id,
            source="kakao",
        )
        return ServiceResult(stored.status, stored.body)

    def _complete_judgment(
        self,
        user_ref: str,
        transaction: Transaction,
        signals: Any,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str,
        quota_prechecked: bool = False,
    ) -> ServiceResult:
        existing = self.repository.get_judgment_for_transaction(
            user_ref, transaction.transaction_id
        )
        if existing:
            return ServiceResult(
                200,
                {
                    "transaction": self.repository.get_transaction(
                        user_ref, transaction.transaction_id
                    ).to_dict(),
                    "signals": signals.to_dict(),
                    "judgment": self._render(user_ref, existing),
                },
            )
        if not quota_prechecked:
            self._consume_judgment_quota(user_ref)
        judgment = self.judge.judge(
            JudgmentRequest(
                transaction_id=transaction.transaction_id,
                amount_krw=transaction.amount_krw,
                category=transaction.category,
                signals=signals,
                user_reason=transaction.reason,
                spending_rules=self.repository.get_settings(user_ref).spending_rules,
                reflection_context=self._category_reflection_context(
                    user_ref, transaction.category
                ),
            )
        )
        stored = self.repository.save_judgment(
            user_ref,
            judgment,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )
        judgment = JudgmentResult.from_dict(stored.body["judgment"])
        self._emit_telemetry(
            user_ref,
            event_type="judgment.completed",
            event_id=judgment.judgment_id,
            label=judgment.label,
            confidence=judgment.confidence,
            adapter_source=transaction.source,
            fallback_used=judgment.fallback_used,
            policy_version=judgment.policy_version,
        )
        return ServiceResult(
            201,
            {
                "transaction": self.repository.get_transaction(
                    user_ref, transaction.transaction_id
                ).to_dict(),
                "signals": signals.to_dict(),
                "judgment": self._render(user_ref, judgment),
            },
        )

    def _existing_transaction_result(
        self, user_ref: str, transaction: Transaction
    ) -> ServiceResult | None:
        judgment = self.repository.get_judgment_for_transaction(
            user_ref, transaction.transaction_id
        )
        if judgment:
            return ServiceResult(
                200,
                {"transaction": transaction.to_dict(), "judgment": self._render(user_ref, judgment)},
            )
        pending = self.repository.get_pending_question(user_ref)
        if pending and pending.transaction_id == transaction.transaction_id and pending.answered_at is None:
            return ServiceResult(
                202,
                {"transaction": transaction.to_dict(), "pending_question": pending.to_dict()},
            )
        return None

    def _category_reflection_context(
        self, user_ref: str, category: str
    ) -> dict[str, int | float]:
        reflected = [
            item
            for item in self.repository.list_transactions(user_ref)
            if item.transaction_type == "expense"
            and item.category == category
            and item.reflection is not None
        ]
        if not reflected:
            return {}
        regretted_count = sum(item.reflection == "regretted" for item in reflected)
        return {
            "category_reflected_count": len(reflected),
            "category_regretted_count": regretted_count,
            "category_regret_rate": round(regretted_count / len(reflected), 4),
        }

    def _build_spending_plan(
        self,
        user_ref: str,
        payload: dict[str, Any],
        *,
        status: str,
        existing: SpendingPlan | None = None,
        version: int = 1,
    ) -> SpendingPlan:
        period_start = str(payload.get("period_start") or (existing.period_start if existing else ""))
        period_end = str(payload.get("period_end") or (existing.period_end if existing else ""))
        budget_value = payload.get(
            "confirmed_budget_krw",
            existing.confirmed_budget_krw if existing else None,
        )
        if not isinstance(budget_value, int) or isinstance(budget_value, bool):
            raise ServiceError("invalid_request", "confirmed_budget_krw must be an integer", 400)
        raw_priorities = payload.get("priorities", existing.priorities if existing else [])
        if not isinstance(raw_priorities, list):
            raise ServiceError("invalid_request", "priorities must be a list", 400)
        priorities: list[PlanPriority] = []
        for index, item in enumerate(raw_priorities):
            if isinstance(item, PlanPriority):
                priorities.append(item)
            elif isinstance(item, str):
                name = sanitize_free_text(item, max_length=60)
                if name:
                    priorities.append(PlanPriority(f"priority-{index + 1}", name, index + 1))
            elif isinstance(item, dict):
                priorities.append(
                    PlanPriority(
                        priority_id=str(item.get("priority_id") or f"priority-{index + 1}"),
                        name=str(item.get("name", "")).strip(),
                        rank=int(item.get("rank", index + 1)),
                    )
                )
            else:
                raise ServiceError("invalid_request", "priorities must contain text or objects", 400)
        raw_expenses = payload.get(
            "planned_expenses", existing.planned_expenses if existing else []
        )
        if not isinstance(raw_expenses, list):
            raise ServiceError("invalid_request", "planned_expenses must be a list", 400)
        previous_expenses = {
            item.planned_expense_id: item for item in (existing.planned_expenses if existing else [])
        }
        planned_expenses: list[PlannedExpense] = []
        for index, item in enumerate(raw_expenses):
            if isinstance(item, PlannedExpense):
                planned_expenses.append(item)
                continue
            if not isinstance(item, dict):
                raise ServiceError("invalid_request", "planned_expenses must contain objects", 400)
            expense_id = str(item.get("planned_expense_id") or f"planned-{index + 1}")
            previous = previous_expenses.get(expense_id)
            planned_expenses.append(
                PlannedExpense(
                    planned_expense_id=expense_id,
                    name=str(item.get("name", "")).strip(),
                    amount_krw=int(item.get("amount_krw", 0)),
                    due_date=str(item.get("due_date", "")),
                    category=_normalized_category(item.get("category", "other")),
                    matched_transaction_id=(
                        previous.matched_transaction_id if previous else item.get("matched_transaction_id")
                    ),
                    matched_at=previous.matched_at if previous else item.get("matched_at"),
                )
            )
        raw_allocations = payload.get("allocations")
        if raw_allocations is None:
            allocations = default_allocations(period_start, period_end, budget_value)
        elif not isinstance(raw_allocations, list):
            raise ServiceError("invalid_request", "allocations must be a list", 400)
        else:
            from ledger.domain.plans import PlanAllocation

            allocations = [
                item if isinstance(item, PlanAllocation) else PlanAllocation.from_dict(item)
                for item in raw_allocations
            ]
        now = utc_now_iso()
        return SpendingPlan(
            plan_id=existing.plan_id if existing else str(payload.get("plan_id") or uuid4()),
            user_ref=user_ref,
            period_start=period_start,
            period_end=period_end,
            confirmed_budget_krw=budget_value,
            priorities=priorities,
            allocations=allocations,
            planned_expenses=planned_expenses,
            status=status,
            version=version,
            confirmed_at=(existing.confirmed_at if existing else now) if status == "active" else None,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            narrative=None,
            revisions=list(existing.revisions) if existing else [],
            check_ins=list(existing.check_ins) if existing else [],
        )

    def _attach_plan_impact(
        self, user_ref: str, transaction: Transaction, result: ServiceResult
    ) -> ServiceResult:
        if transaction.transaction_type != "expense" or transaction.exclude_from_budget:
            return result
        plan = self.repository.get_spending_plan(user_ref)
        if plan is None or result.data is None:
            return result
        settings = self.repository.get_settings(user_ref)
        transaction_date = parse_utc_datetime(transaction.occurred_at, "occurred_at").astimezone(
            _safe_timezone(settings.timezone)
        ).date()
        if not parse_date(plan.period_start, "period_start") <= transaction_date <= parse_date(plan.period_end, "period_end"):
            return result
        progress = self._plan_progress(user_ref, plan)
        remaining = progress["flexible_remaining_krw"]
        message = (
            f"계획상 쓸 수 있는 생활비가 {abs(remaining):,}원 부족해졌어요."
            if remaining < 0
            else f"계획상 쓸 수 있는 생활비가 {remaining:,}원 남았어요."
        )
        return ServiceResult(
            result.status,
            {
                **result.data,
                "plan_impact": {
                    "transaction_id": transaction.transaction_id,
                    "amount_krw": transaction.amount_krw,
                    "total_remaining_krw": progress["total_remaining_krw"],
                    "reserved_remaining_krw": progress["reserved_remaining_krw"],
                    "flexible_remaining_krw": remaining,
                    "shortfall_krw": progress["shortfall_krw"],
                    "message": message,
                },
            },
        )

    def _build_revision_candidate(
        self, current: SpendingPlan, payload: dict[str, Any]
    ) -> SpendingPlan:
        base_version = payload.get("base_version")
        if base_version != current.version:
            raise ServiceError(
                "plan_version_conflict",
                "계획이 이미 바뀌었어요. 최신 계획을 다시 확인해 주세요.",
                409,
            )
        return self._build_spending_plan(
            current.user_ref,
            payload,
            status="active",
            existing=current,
            version=current.version + 1,
        )

    def _require_spending_plan(self, user_ref: str) -> SpendingPlan:
        plan = self.repository.get_spending_plan(user_ref)
        if plan is None:
            raise ServiceError("plan_not_found", "먼저 생활비 계획을 만들어 주세요.", 404)
        return plan

    def _plan_progress(self, user_ref: str, plan: SpendingPlan) -> dict[str, Any]:
        settings = self.repository.get_settings(user_ref)
        timezone = _safe_timezone(settings.timezone)
        today = datetime.now(UTC).astimezone(timezone).date()
        return compute_plan_progress(
            plan,
            self.repository.list_transactions(user_ref),
            timezone_name=timezone.key,
            as_of=today,
        )

    def _spending_plan_payload(
        self, user_ref: str, plan: SpendingPlan, *, preview: bool = False
    ) -> dict[str, Any]:
        progress = self._plan_progress(user_ref, plan)
        original = plan.revisions[0].before if plan.revisions else plan.snapshot()
        current_segment = next(
            (
                item
                for item in progress["segments"]
                if item["allocation_id"] == progress["current_segment_id"]
            ),
            None,
        )
        if progress["shortfall_krw"]:
            next_action = "예정 지출이나 생활비 한도를 다시 확인해 계획을 조정하세요."
        elif current_segment is not None:
            next_action = "이번 구간 남은 생활비 안에서 다음 지출 한 건을 기록하세요."
        else:
            next_action = "계획 기간과 현재 날짜를 확인하세요."
        narrative = plan.narrative
        if narrative is None:
            narrative = deterministic_plan_narrative(
                self._plan_advice_request(user_ref, plan, progress)
            ).to_dict()
        return {
            "plan": plan.to_dict(),
            "original_plan": original,
            "progress": progress,
            "next_action": next_action,
            "narrative": narrative,
            "preview": preview,
        }

    def _with_plan_narrative(
        self, user_ref: str, plan: SpendingPlan
    ) -> SpendingPlan:
        progress = self._plan_progress(user_ref, plan)
        narrative = self._plan_narrative(user_ref, plan, progress).to_dict()
        return replace(plan, narrative=narrative)

    def _plan_narrative(
        self, user_ref: str, plan: SpendingPlan, progress: dict[str, Any]
    ) -> PlanNarrative:
        request = self._plan_advice_request(user_ref, plan, progress)
        try:
            return self.plan_advisor.advise(request)
        except Exception:
            return deterministic_plan_narrative(request)

    def _plan_advice_request(
        self, user_ref: str, plan: SpendingPlan, progress: dict[str, Any]
    ) -> PlanAdviceRequest:
        settings = self.repository.get_settings(user_ref)
        transactions = [
            item
            for item in self.repository.list_transactions(user_ref)
            if item.transaction_type == "expense" and not item.exclude_from_budget
        ]
        category_spend: dict[str, int] = {}
        reflection_counts = {"well_spent": 0, "unsure": 0, "regretted": 0}
        judgment_counts = {
            "justified": 0,
            "caution": 0,
            "overspending": 0,
            "insufficient_context": 0,
        }
        for item in transactions:
            category_spend[item.category] = category_spend.get(item.category, 0) + item.amount_krw
            if item.reflection in reflection_counts:
                reflection_counts[item.reflection] += 1
            judgment = self.repository.get_judgment_for_transaction(user_ref, item.transaction_id)
            if judgment and judgment.label in judgment_counts:
                judgment_counts[judgment.label] += 1
        return PlanAdviceRequest(
            period_start=plan.period_start,
            period_end=plan.period_end,
            confirmed_budget_krw=plan.confirmed_budget_krw,
            deterministic_progress={
                key: progress[key]
                for key in (
                    "actual_spent_krw",
                    "reserved_remaining_krw",
                    "total_remaining_krw",
                    "flexible_remaining_krw",
                    "shortfall_krw",
                    "current_segment_id",
                )
            },
            allocations=[
                {
                    key: item[key]
                    for key in (
                        "allocation_id",
                        "start_date",
                        "end_date",
                        "amount_krw",
                        "actual_spent_krw",
                        "reserved_remaining_krw",
                        "flexible_remaining_krw",
                    )
                }
                for item in progress["segments"]
            ],
            planned_expenses=[
                {
                    "category": item.category,
                    "amount_krw": item.amount_krw,
                    "due_date": item.due_date,
                    "matched": item.matched_transaction_id is not None,
                }
                for item in plan.planned_expenses
            ],
            priorities=[item.name for item in plan.priorities],
            spending_rules=list(settings.spending_rules),
            aggregate_patterns={
                "category_spend_krw": category_spend,
                "reflection_counts": reflection_counts,
                "judgment_counts": judgment_counts,
            },
        )

    def _revision_diff(
        self, user_ref: str, current: SpendingPlan, candidate: SpendingPlan
    ) -> dict[str, Any]:
        before_progress = self._plan_progress(user_ref, current)
        after_progress = self._plan_progress(user_ref, candidate)
        return {
            "from_version": current.version,
            "to_version": candidate.version,
            "before": current.snapshot(),
            "after": candidate.snapshot(),
            "before_progress": before_progress,
            "after_progress": after_progress,
            "budget_change_krw": candidate.confirmed_budget_krw - current.confirmed_budget_krw,
            "flexible_remaining_change_krw": (
                after_progress["flexible_remaining_krw"]
                - before_progress["flexible_remaining_krw"]
            ),
            "narrative": candidate.narrative
            or deterministic_plan_narrative(
                self._plan_advice_request(user_ref, candidate, after_progress)
            ).to_dict(),
        }

    def _compute_signals(
        self, profile: FinancialProfile, transaction: Transaction
    ) -> Any:
        settings = self.repository.get_settings(profile.user_ref)
        timezone = _safe_timezone(settings.timezone)
        prior = [
            item
            for item in self.repository.list_transactions(profile.user_ref)
            if item.transaction_type == "expense"
            and not item.exclude_from_budget
            and item.transaction_id != transaction.transaction_id
        ]
        occurred = parse_utc_datetime(transaction.occurred_at, "occurred_at").astimezone(timezone)
        monthly_spend = sum(
            item.amount_krw
            for item in prior
            if _same_month(
                parse_utc_datetime(item.occurred_at, "occurred_at").astimezone(timezone),
                occurred,
            )
        )
        category_history = [item for item in prior if item.category == transaction.category]
        average = (
            sum(item.amount_krw for item in category_history) / len(category_history)
            if category_history
            else max(transaction.amount_krw, 1)
        )
        signal_amount = 0 if transaction.exclude_from_budget else transaction.amount_krw
        baseline_deviation = signal_amount / max(average, 1)
        since = occurred - timedelta(days=30)
        recurrence = sum(
            1
            for item in category_history
            if since <= parse_utc_datetime(item.occurred_at, "occurred_at") <= occurred
        )
        return compute_signal_set(
            SignalInputs(
                transaction_amount_krw=signal_amount,
                discretionary_budget_krw=profile.discretionary_budget_krw,
                spent_before_transaction_krw=monthly_spend,
                category=transaction.category,
                goal_pressure=_goal_pressure(profile, occurred.date()),
                baseline_deviation=baseline_deviation,
                recurrence_30d=recurrence,
                has_reason=bool(transaction.reason),
                profile_complete=True,
                history_complete=len(prior) >= 3,
            )
        )

    def _render(self, user_ref: str, judgment: JudgmentResult) -> dict[str, Any]:
        settings = self.repository.get_settings(user_ref)
        return render_judgment(
            judgment, roast_enabled=settings.roast_enabled
        ).to_dict()

    def _require_transaction(
        self, user_ref: str, transaction_id: str
    ) -> Transaction:
        transaction = self.repository.get_transaction(user_ref, transaction_id)
        if transaction is None:
            raise ServiceError("transaction_not_found", "transaction was not found", 404)
        return transaction

    def _require_roast_judgment(
        self, user_ref: str, judgment_id: str
    ) -> JudgmentResult:
        judgment = self.repository.get_judgment(user_ref, judgment_id)
        if judgment is None:
            raise ServiceError("judgment_not_found", "judgment was not found", 404)
        if not self.repository.get_settings(user_ref).roast_enabled:
            raise ServiceError(
                "roast_required", "Roast mode must be enabled for Roast sharing", 409
            )
        return judgment

    def _emit_telemetry(
        self,
        user_ref: str,
        *,
        event_type: str,
        event_id: str,
        label: str | None = None,
        confidence: float | None = None,
        adapter_source: str | None = None,
        reason_question_asked: bool = False,
        fallback_used: bool = False,
        correction_flag: bool = False,
        share_flag: bool = False,
        policy_version: str | None = None,
    ) -> None:
        if self.telemetry_sink is None:
            return
        event = TelemetryEvent(
            event_type=event_type,
            event_id=event_id,
            user_ref=user_ref,
            label=label,
            confidence_band=confidence_band(confidence),
            adapter_source=adapter_source,
            reason_question_asked=reason_question_asked,
            fallback_used=fallback_used,
            correction_flag=correction_flag,
            share_flag=share_flag,
            policy_version=policy_version,
        )
        try:
            self.telemetry_sink(event.to_dict())
        except Exception:
            if fallback_used:
                logger.warning(
                    "OpenAI fallback used and telemetry sink failed",
                    extra={
                        "event_type": event_type,
                        "fallback_used": True,
                        "policy_version": policy_version,
                        "redaction_status": "allowlisted",
                    },
                )
            return

    def _cache_service_result(
        self, user_ref: str, cache_key: str, result: ServiceResult
    ) -> ServiceResult:
        from ledger.domain.ports import StoredResult

        self.repository.cache_result(
            user_ref,
            cache_key,
            StoredResult(result.status, result.data or {}),
        )
        return result

    def _consume_judgment_quota(self, user_ref: str) -> None:
        if self.judgment_quota is None:
            return
        try:
            self.judgment_quota.check_and_increment(user_ref)
        except QuotaExceededError as exc:
            raise JudgmentQuotaError(
                "ai_judgment_quota_exceeded",
                "오늘 사용할 수 있는 AI 판단 횟수를 모두 썼어요. 잠시 후 다시 시도해 주세요.",
                429,
            ) from exc
        except QuotaUnavailableError as exc:
            raise JudgmentQuotaError(
                "ai_judgment_quota_unavailable",
                "AI 판단 한도를 확인하지 못했어요. 잠시 후 다시 시도해 주세요.",
                429,
            ) from exc


def _corrected_share_message(label: str) -> str:
    messages = {
        "justified": "다시 장부를 보니 납득할 만한 지출이구나. 다음에도 이유와 예산을 같이 확인해라.",
        "caution": "다시 장부를 보니 주의가 필요한 지출이구나. 다음 소비 전에는 예산부터 한 번 더 확인해라.",
        "overspending": "다시 장부를 보니 과소비가 맞구나. 다음 지출은 멈추고 예산부터 확인해라.",
        "insufficient_context": "다시 장부를 봐도 정보가 더 필요하구나. 판단 전에 이유를 조금 더 남겨라.",
    }
    return messages.get(label, messages["insufficient_context"])


def _safe_timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except Exception:
        return ZoneInfo("Asia/Seoul")


def _integer(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ServiceError("invalid_request", f"{field_name} must be an integer", 400)
    return value


def _boolean(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ServiceError("invalid_request", f"{field_name} must be a boolean", 400)
    return value


def _optional_text(value: Any, *, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ServiceError("invalid_request", "text fields must be strings", 400)
    return sanitize_free_text(value, max_length=max_length)


def _spending_rules(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ServiceError("invalid_request", "spending_rules must be a list", 400)
    if len(value) > 8:
        raise ServiceError(
            "invalid_request", "spending_rules can contain at most 8 items", 400
        )
    rules: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ServiceError(
                "invalid_request", "spending_rules must contain strings", 400
            )
        rule = sanitize_free_text(item, max_length=120)
        if rule and rule not in rules:
            rules.append(rule)
    return rules


def _ledger_accounts(value: Any) -> list[LedgerAccount]:
    if not isinstance(value, list):
        raise ServiceError("invalid_request", "accounts must be a list", 400)
    accounts: list[LedgerAccount] = []
    for item in value:
        if isinstance(item, LedgerAccount):
            accounts.append(item)
        elif isinstance(item, dict):
            accounts.append(LedgerAccount.from_dict(item))
        else:
            raise ServiceError(
                "invalid_request", "accounts must contain objects", 400
            )
    return accounts


def _category_budgets(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ServiceError(
            "invalid_request", "category_budgets_krw must be an object", 400
        )
    budgets: dict[str, int] = {}
    for raw_category, raw_budget in value.items():
        category = _normalized_category(raw_category)
        if not isinstance(raw_budget, int) or isinstance(raw_budget, bool):
            raise ServiceError(
                "invalid_request", "category budget must be an integer", 400
            )
        budgets[category] = raw_budget
    return budgets


def _transaction_type(value: Any) -> str:
    transaction_type = str(value or "expense").strip().lower()
    if transaction_type not in {"expense", "income", "transfer"}:
        raise ServiceError("invalid_request", "unsupported transaction_type", 400)
    return transaction_type


def _account_id(value: Any, *, default: str | None) -> str | None:
    if value is None or value == "":
        return default
    if not isinstance(value, str):
        raise ServiceError("invalid_request", "account_id must be a string", 400)
    account_id = value.strip()
    if not account_id or len(account_id) > 64:
        raise ServiceError(
            "invalid_request", "account_id must be 1 to 64 characters", 400
        )
    return account_id


def _validate_transaction_accounts(
    settings: UserSettings, transaction: Transaction
) -> None:
    known_ids = {account.account_id for account in settings.accounts if not account.archived}
    if transaction.account_id not in known_ids:
        raise ServiceError("invalid_account", "source account was not found", 400)
    if (
        transaction.destination_account_id is not None
        and transaction.destination_account_id not in known_ids
    ):
        raise ServiceError("invalid_account", "destination account was not found", 400)


def _account_balances(
    accounts: list[LedgerAccount], transactions: list[Transaction]
) -> list[dict[str, Any]]:
    balances = {
        account.account_id: account.opening_balance_krw for account in accounts
    }
    for transaction in transactions:
        if transaction.account_id not in balances:
            continue
        if transaction.transaction_type == "income":
            balances[transaction.account_id] += transaction.amount_krw
        elif transaction.transaction_type == "expense":
            balances[transaction.account_id] -= transaction.amount_krw
        elif transaction.transaction_type == "transfer":
            balances[transaction.account_id] -= transaction.amount_krw
            if transaction.destination_account_id in balances:
                balances[transaction.destination_account_id] += transaction.amount_krw
    return [
        {
            **account.to_dict(),
            "balance_krw": balances[account.account_id],
        }
        for account in accounts
    ]


def _normalized_category(value: Any) -> str:
    if value is None:
        return "unknown"
    if not isinstance(value, str):
        raise ServiceError("invalid_request", "category must be a string", 400)
    normalized = value.strip().lower().replace(" ", "_")
    return normalized or "unknown"


def _category_name(category: str | None) -> str:
    if category is None:
        return "기타"
    return CATEGORY_NAMES_KO.get(category, category)


def _same_month(left: datetime, right: datetime) -> bool:
    return left.year == right.year and left.month == right.month


def _goal_pressure(profile: FinancialProfile, as_of: date) -> float:
    fixed_and_debt = profile.fixed_expenses_krw + profile.monthly_debt_payment_krw
    if fixed_and_debt >= profile.monthly_income_krw:
        return 1.0
    goal_date = parse_date(profile.goal.target_date, "goal.target_date")
    months_remaining = max(1.0, (goal_date - as_of).days / 30.4375)
    savings_gap = max(
        0, profile.goal.target_amount_krw - profile.goal.current_amount_krw
    )
    required_monthly = savings_gap / months_remaining
    disposable = max(1, profile.monthly_income_krw - fixed_and_debt)
    return clamp(required_monthly / disposable)


def _goal_delay_days(
    regretted_spent_krw: int,
    profile: FinancialProfile | None,
    as_of: date,
) -> int:
    if profile is None or regretted_spent_krw <= 0:
        return 0
    savings_gap = max(
        0, profile.goal.target_amount_krw - profile.goal.current_amount_krw
    )
    days_remaining = max(
        1, (parse_date(profile.goal.target_date, "goal.target_date") - as_of).days
    )
    if savings_gap == 0:
        return 0
    required_daily_savings = savings_gap / days_remaining
    return ceil(regretted_spent_krw / max(required_daily_savings, 1))


def _key(scope: str, client_key: str) -> str:
    return f"{scope}:{client_key}"
