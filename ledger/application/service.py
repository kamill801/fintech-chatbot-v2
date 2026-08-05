from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable, Protocol
from uuid import uuid4

from ledger.adapters.manual import ManualTransactionDraft, ManualTransactionSource
from ledger.adapters.openai_judge import JudgmentRequest
from ledger.adapters.synthetic import ProviderUnavailableError
from ledger.application.signals import POLICY_VERSION, SignalInputs, clamp, compute_signal_set
from ledger.domain.models import (
    ALLOWED_JUDGMENT_LABELS,
    DomainValidationError,
    FinancialGoal,
    FinancialProfile,
    JudgmentResult,
    PendingQuestion,
    Transaction,
    UserSettings,
    parse_date,
    parse_utc_datetime,
    utc_now_iso,
)
from ledger.domain.ports import LedgerRepository, ReadOnlyAccountAdapter
from ledger.privacy import sanitize_free_text, sanitize_share_payload
from ledger.rendering import render_judgment
from ledger.telemetry import TelemetryEvent, confidence_band


class Judge(Protocol):
    def judge(self, request: JudgmentRequest) -> JudgmentResult: ...


class ServiceError(RuntimeError):
    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


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
    ) -> None:
        self.repository = repository
        self.judge = judge
        self.account_adapter = account_adapter
        self.manual_source = ManualTransactionSource()
        self.telemetry_sink = telemetry_sink

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
        )
        stored = self.repository.update_settings(
            user_ref,
            settings,
            idempotency_key=_key("settings", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return ServiceResult(stored.status, stored.body)

    def list_transactions(self, user_ref: str) -> ServiceResult:
        transactions = [item.to_dict() for item in self.repository.list_transactions(user_ref)]
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
        )
        transaction = self.manual_source.create_record(draft)
        recorded = self.repository.record_transaction(
            transaction,
            idempotency_key=_key("transaction-record", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        transaction = Transaction.from_dict(recorded.body["transaction"])
        existing = self._existing_transaction_result(user_ref, transaction)
        if existing:
            return self._cache_service_result(user_ref, response_key, existing)

        signals = self._compute_signals(profile, transaction)
        if signals.requires_reason and not transaction.reason:
            question = PendingQuestion(
                question_id=str(uuid4()),
                transaction_id=transaction.transaction_id,
                question="이 지출이 꼭 필요했던 이유가 뭐야?",
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
            return self._cache_service_result(user_ref, response_key, result)
        result = self._complete_judgment(
            user_ref,
            transaction,
            signals,
            idempotency_key=_key("judgment", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        return self._cache_service_result(user_ref, response_key, result)

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
        stored = self.repository.add_transaction_reason(
            user_ref,
            transaction_id,
            reason,
            answered_at=utc_now_iso(),
            idempotency_key=_key(f"reason:{transaction_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        transaction = Transaction.from_dict(stored.body["transaction"])
        profile = self.repository.get_profile(user_ref)
        if profile is None:
            raise ServiceError("profile_required", "financial profile is missing", 409)
        signals = self._compute_signals(profile, transaction)
        result = self._complete_judgment(
            user_ref,
            transaction,
            signals,
            idempotency_key=_key(f"reason-judgment:{transaction_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
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
        stored = self.repository.record_share_click(
            user_ref,
            judgment_id,
            idempotency_key=_key(f"share:{judgment_id}", idempotency_key),
            correlation_id=correlation_id,
            source=source,
        )
        share = sanitize_share_payload(
            {
                "label": judgment.label,
                "roast_message": render_judgment(
                    judgment, roast_enabled=True
                ).message,
                "category": transaction.category,
                "recommended_action": judgment.recommended_action,
            }
        )
        self._emit_telemetry(
            user_ref,
            event_type="share.clicked",
            event_id=str(uuid4()),
            label=judgment.label,
            share_flag=True,
            policy_version=judgment.policy_version,
        )
        return ServiceResult(stored.status, {"share": share})

    def get_summary(self, user_ref: str) -> ServiceResult:
        profile = self.repository.get_profile(user_ref)
        transactions = list(self.repository.list_transactions(user_ref))
        now = datetime.now(UTC)
        current = [
            transaction
            for transaction in transactions
            if _same_month(parse_utc_datetime(transaction.occurred_at, "occurred_at"), now)
        ]
        by_category: dict[str, int] = {}
        for transaction in current:
            by_category[transaction.category] = (
                by_category.get(transaction.category, 0) + transaction.amount_krw
            )
        total = sum(transaction.amount_krw for transaction in current)
        summary: dict[str, Any] = {
            "month": now.strftime("%Y-%m"),
            "total_spent_krw": total,
            "by_category_krw": by_category,
            "transaction_count": len(current),
        }
        if profile:
            summary.update(
                {
                    "discretionary_budget_krw": profile.discretionary_budget_krw,
                    "budget_usage": round(
                        total / profile.discretionary_budget_krw, 4
                    ),
                    "goal": profile.goal.to_dict(),
                }
            )
        return ServiceResult(200, {"summary": summary})

    def get_metrics(self, user_ref: str) -> ServiceResult:
        metrics = self.repository.get_metrics(user_ref)
        views = int(metrics.get("share_views", 0))
        clicks = int(metrics.get("share_clicks", 0))
        metrics["roast_share_rate"] = round(clicks / views, 4) if views else 0.0
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
        judgment = self.judge.judge(
            JudgmentRequest(
                transaction_id=transaction.transaction_id,
                amount_krw=transaction.amount_krw,
                category=transaction.category,
                signals=signals,
                user_reason=transaction.reason,
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

    def _compute_signals(
        self, profile: FinancialProfile, transaction: Transaction
    ) -> Any:
        prior = [
            item
            for item in self.repository.list_transactions(profile.user_ref)
            if item.transaction_id != transaction.transaction_id
        ]
        occurred = parse_utc_datetime(transaction.occurred_at, "occurred_at")
        monthly_spend = sum(
            item.amount_krw
            for item in prior
            if _same_month(parse_utc_datetime(item.occurred_at, "occurred_at"), occurred)
        )
        category_history = [item for item in prior if item.category == transaction.category]
        average = (
            sum(item.amount_krw for item in category_history) / len(category_history)
            if category_history
            else transaction.amount_krw
        )
        baseline_deviation = transaction.amount_krw / max(average, 1)
        since = occurred - timedelta(days=30)
        recurrence = sum(
            1
            for item in category_history
            if since <= parse_utc_datetime(item.occurred_at, "occurred_at") <= occurred
        )
        return compute_signal_set(
            SignalInputs(
                transaction_amount_krw=transaction.amount_krw,
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


def _integer(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ServiceError("invalid_request", f"{field_name} must be an integer", 400)
    return value


def _optional_text(value: Any, *, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ServiceError("invalid_request", "text fields must be strings", 400)
    return sanitize_free_text(value, max_length=max_length)


def _normalized_category(value: Any) -> str:
    if value is None:
        return "unknown"
    if not isinstance(value, str):
        raise ServiceError("invalid_request", "category must be a string", 400)
    normalized = value.strip().lower().replace(" ", "_")
    return normalized or "unknown"


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


def _key(scope: str, client_key: str) -> str:
    return f"{scope}:{client_key}"
