from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Callable, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

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
from ledger.quota import JudgmentQuotaLimiter, QuotaExceededError, QuotaUnavailableError
from ledger.rendering import render_judgment
from ledger.telemetry import TelemetryEvent, confidence_band

logger = logging.getLogger(__name__)

CATEGORY_NAMES_KO = {
    "cafe": "카페·간식",
    "food": "식비",
    "transport": "교통",
    "shopping": "쇼핑",
    "housing": "주거",
    "health": "건강",
    "other": "기타",
    "unknown": "기타",
}


class Judge(Protocol):
    def judge(self, request: JudgmentRequest) -> JudgmentResult: ...


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
    ) -> None:
        self.repository = repository
        self.judge = judge
        self.account_adapter = account_adapter
        self.manual_source = ManualTransactionSource()
        self.telemetry_sink = telemetry_sink
        self.judgment_quota = judgment_quota

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
        active_pending = self.repository.get_pending_question(user_ref)
        if (
            settings.roast_enabled
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
        )
        transaction = self.manual_source.create_record(draft)
        transaction_record_key = _key("transaction-record", idempotency_key)
        recorded = self.repository.get_cached_result(user_ref, transaction_record_key)
        quota_prechecked = False
        requires_interactive_reason = settings.roast_enabled and not transaction.reason
        if recorded is None:
            signals = self._compute_signals(profile, transaction)
            if not requires_interactive_reason:
                self._consume_judgment_quota(user_ref)
                quota_prechecked = True
            recorded = self.repository.record_transaction(
                transaction,
                idempotency_key=transaction_record_key,
                correlation_id=correlation_id,
                source=source,
            )
        transaction = Transaction.from_dict(recorded.body["transaction"])
        existing = self._existing_transaction_result(user_ref, transaction)
        if existing:
            return self._cache_service_result(user_ref, response_key, existing)

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
            return self._cache_service_result(user_ref, response_key, result)
        result = self._complete_judgment(
            user_ref,
            transaction,
            signals,
            idempotency_key=_key("judgment", idempotency_key),
            correlation_id=correlation_id,
            source=source,
            quota_prechecked=quota_prechecked,
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
            "weekly_briefing": self._weekly_briefing(
                user_ref,
                transactions,
                now=now,
                timezone=timezone,
            ),
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

    def _weekly_briefing(
        self,
        user_ref: str,
        transactions: list[Transaction],
        *,
        now: datetime,
        timezone: ZoneInfo,
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
        if label_counts["overspending"]:
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
        if concern is not None and concern[2] != "justified":
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


def _key(scope: str, client_key: str) -> str:
    return f"{scope}:{client_key}"
