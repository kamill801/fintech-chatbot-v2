from __future__ import annotations

import uuid
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from ledger.domain.events import (
    EVENT_ACCOUNT_REVOKED,
    EVENT_DATA_DELETION_REQUESTED,
    EVENT_JUDGMENT_COMPLETED,
    EVENT_JUDGMENT_CORRECTED,
    EVENT_JUDGMENT_REASON_REQUESTED,
    EVENT_LEGACY_IMPORTED,
    EVENT_PROFILE_UPSERTED,
    EVENT_SETTINGS_ROAST_CHANGED,
    EVENT_SHARE_CLICKED,
    EVENT_SHARE_SUCCEEDED,
    EVENT_SHARE_VIEWED,
    EVENT_TRANSACTION_REASON_ADDED,
    EVENT_TRANSACTION_RECORDED,
    EventEnvelope,
)
from ledger.domain.models import (
    SCHEMA_VERSION,
    ALLOWED_JUDGMENT_LABELS,
    DomainValidationError,
    FinancialProfile,
    JudgmentCorrection,
    JudgmentResult,
    PendingQuestion,
    Transaction,
    UserSettings,
    utc_now_iso,
)
from ledger.domain.ports import LedgerRepository, StoredResult
from ledger.privacy import PrivacyService


@dataclass
class _UserStore:
    events: list[EventEnvelope] = field(default_factory=list)
    profile: str | None = None
    settings: str | None = None
    transactions: dict[str, str] = field(default_factory=dict)
    transaction_order: dict[str, str] = field(default_factory=dict)
    judgments: dict[str, str] = field(default_factory=dict)
    corrections: dict[str, str] = field(default_factory=dict)
    pending_question: str | None = None
    idempotency: dict[str, str] = field(default_factory=dict)
    legacy_imported: bool = False
    metrics: dict[str, int] = field(
        default_factory=lambda: {
            "transactions_recorded": 0,
            "judgments_completed": 0,
            "corrections": 0,
            "share_views": 0,
            "share_clicks": 0,
            "share_successes": 0,
            "accounts_revoked": 0,
            "legacy_imports": 0,
        }
    )


class InMemoryLedgerRepository(LedgerRepository):
    def __init__(self, privacy: PrivacyService) -> None:
        self._privacy = privacy
        self._users: defaultdict[str, _UserStore] = defaultdict(_UserStore)
        self.deletion_metrics: list[dict[str, str]] = []

    def get_profile(self, user_ref: str) -> FinancialProfile | None:
        encrypted = self._users[user_ref].profile
        if encrypted is None:
            return None
        return FinancialProfile.from_dict(self._privacy.decrypt_json(encrypted))

    def get_cached_result(
        self, user_ref: str, idempotency_key: str
    ) -> StoredResult | None:
        encrypted = self._users[user_ref].idempotency.get(idempotency_key)
        return self._decode_result(encrypted) if encrypted else None

    def cache_result(
        self, user_ref: str, idempotency_key: str, result: StoredResult
    ) -> None:
        self._users[user_ref].idempotency[idempotency_key] = self._privacy.encrypt_json(
            {"status": result.status, "body": result.body}
        )

    def upsert_profile(
        self,
        profile: FinancialProfile,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            profile.user_ref,
            idempotency_key,
            lambda store: self._upsert_profile(
                store, profile, idempotency_key, correlation_id, source
            ),
        )

    def get_settings(self, user_ref: str) -> UserSettings:
        encrypted = self._users[user_ref].settings
        if encrypted is None:
            return UserSettings()
        return UserSettings.from_dict(self._privacy.decrypt_json(encrypted))

    def update_settings(
        self,
        user_ref: str,
        settings: UserSettings,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._update_settings(
                store, user_ref, settings, idempotency_key, correlation_id, source
            ),
        )

    def record_transaction(
        self,
        transaction: Transaction,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            transaction.user_ref,
            idempotency_key,
            lambda store: self._record_transaction(
                store, transaction, idempotency_key, correlation_id, source
            ),
        )

    def get_transaction(self, user_ref: str, transaction_id: str) -> Transaction | None:
        encrypted = self._users[user_ref].transactions.get(transaction_id)
        if encrypted is None:
            return None
        return Transaction.from_dict(self._privacy.decrypt_json(encrypted))

    def list_transactions(self, user_ref: str) -> Sequence[Transaction]:
        store = self._users[user_ref]
        ids = sorted(
            store.transaction_order,
            key=lambda item: (store.transaction_order[item], item),
        )
        return [Transaction.from_dict(self._privacy.decrypt_json(store.transactions[i])) for i in ids]

    def save_pending_question(
        self,
        user_ref: str,
        pending_question: PendingQuestion,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._save_pending_question(
                store,
                user_ref,
                pending_question,
                idempotency_key,
                correlation_id,
                source,
            ),
        )

    def get_pending_question(self, user_ref: str) -> PendingQuestion | None:
        encrypted = self._users[user_ref].pending_question
        if encrypted is None:
            return None
        return PendingQuestion.from_dict(self._privacy.decrypt_json(encrypted))

    def add_transaction_reason(
        self,
        user_ref: str,
        transaction_id: str,
        reason: str,
        *,
        answered_at: str,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._add_transaction_reason(
                store,
                user_ref,
                transaction_id,
                reason,
                answered_at,
                idempotency_key,
                correlation_id,
                source,
            ),
        )

    def save_judgment(
        self,
        user_ref: str,
        judgment: JudgmentResult,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._save_judgment(
                store, user_ref, judgment, idempotency_key, correlation_id, source
            ),
        )

    def get_judgment(self, user_ref: str, judgment_id: str) -> JudgmentResult | None:
        encrypted = self._users[user_ref].judgments.get(judgment_id)
        if encrypted is None:
            return None
        return JudgmentResult.from_dict(self._privacy.decrypt_json(encrypted))

    def get_judgment_for_transaction(
        self, user_ref: str, transaction_id: str
    ) -> JudgmentResult | None:
        for encrypted in self._users[user_ref].judgments.values():
            judgment = JudgmentResult.from_dict(self._privacy.decrypt_json(encrypted))
            if judgment.transaction_id == transaction_id:
                return judgment
        return None

    def get_judgment_correction(
        self, user_ref: str, judgment_id: str
    ) -> JudgmentCorrection | None:
        encrypted = self._users[user_ref].corrections.get(judgment_id)
        if encrypted is None:
            return None
        return JudgmentCorrection.from_dict(self._privacy.decrypt_json(encrypted))

    def correct_judgment(
        self,
        user_ref: str,
        judgment_id: str,
        corrected_label: str,
        *,
        correction_reason: str | None,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._correct_judgment(
                store,
                user_ref,
                judgment_id,
                corrected_label,
                correction_reason,
                idempotency_key,
                correlation_id,
                source,
            ),
        )

    def record_share_view(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._record_metric_event(
            user_ref,
            judgment_id,
            EVENT_SHARE_VIEWED,
            "share_views",
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )

    def record_share_click(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._record_metric_event(
            user_ref,
            judgment_id,
            EVENT_SHARE_CLICKED,
            "share_clicks",
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )

    def record_share_success(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._record_metric_event(
            user_ref,
            judgment_id,
            EVENT_SHARE_SUCCEEDED,
            "share_successes",
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )

    def revoke_account(
        self,
        user_ref: str,
        connection_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._revoke_account(
                store, user_ref, connection_id, idempotency_key, correlation_id, source
            ),
        )

    def import_legacy_metadata(
        self,
        user_ref: str,
        metadata: Mapping[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._import_legacy_metadata(
                store, user_ref, metadata, idempotency_key, correlation_id, source
            ),
        )

    def request_data_deletion(
        self,
        user_ref: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        return self._request_data_deletion(
            self._users[user_ref],
            user_ref,
            idempotency_key,
            correlation_id,
            source,
        )

    def get_metrics(self, user_ref: str) -> dict[str, Any]:
        return deepcopy(self._users[user_ref].metrics)

    def list_events(self, user_ref: str) -> Sequence[EventEnvelope]:
        return list(self._users[user_ref].events)

    def _mutate(
        self,
        user_ref: str,
        idempotency_key: str,
        operation: Callable[[_UserStore], StoredResult],
    ) -> StoredResult:
        if not idempotency_key:
            raise DomainValidationError("idempotency_key is required")
        store = self._users[user_ref]
        cached = store.idempotency.get(idempotency_key)
        if cached is not None:
            return self._decode_result(cached)
        result = operation(store)
        store.idempotency[idempotency_key] = self._privacy.encrypt_json(
            {"status": result.status, "body": result.body}
        )
        return result

    def _append_event(
        self,
        store: _UserStore,
        user_ref: str,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str,
        redacted_metadata: Mapping[str, Any] | None = None,
    ) -> EventEnvelope:
        event = EventEnvelope(
            event_id=str(uuid.uuid4()),
            user_ref=user_ref,
            event_type=event_type,
            schema_version=SCHEMA_VERSION,
            created_at=utc_now_iso(),
            source=source,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            redacted_metadata=dict(redacted_metadata or {}),
            encrypted_payload=self._privacy.encrypt_json(dict(payload)),
        )
        store.events.append(event)
        return event

    def _upsert_profile(
        self,
        store: _UserStore,
        profile: FinancialProfile,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = profile.to_dict()
        self._append_event(
            store,
            profile.user_ref,
            EVENT_PROFILE_UPSERTED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )
        store.profile = self._privacy.encrypt_json(payload)
        return StoredResult(200, {"profile": payload})

    def _update_settings(
        self,
        store: _UserStore,
        user_ref: str,
        settings: UserSettings,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = settings.to_dict()
        self._append_event(
            store,
            user_ref,
            EVENT_SETTINGS_ROAST_CHANGED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
            redacted_metadata={"roast_enabled": settings.roast_enabled},
        )
        store.settings = self._privacy.encrypt_json(payload)
        return StoredResult(200, {"settings": payload})

    def _record_transaction(
        self,
        store: _UserStore,
        transaction: Transaction,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = transaction.to_dict()
        self._append_event(
            store,
            transaction.user_ref,
            EVENT_TRANSACTION_RECORDED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
            redacted_metadata={"adapter_source": transaction.source},
        )
        store.transactions[transaction.transaction_id] = self._privacy.encrypt_json(payload)
        store.transaction_order[transaction.transaction_id] = transaction.occurred_at
        store.metrics["transactions_recorded"] += 1
        return StoredResult(201, {"transaction": payload})

    def _save_pending_question(
        self,
        store: _UserStore,
        user_ref: str,
        pending_question: PendingQuestion,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        existing = self.get_pending_question(user_ref)
        if existing and existing.transaction_id == pending_question.transaction_id:
            return StoredResult(202, {"pending_question": existing.to_dict()})
        if existing and existing.answered_at is None:
            raise DomainValidationError("a pending question already exists")
        payload = pending_question.to_dict()
        self._append_event(
            store,
            user_ref,
            EVENT_JUDGMENT_REASON_REQUESTED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
            redacted_metadata={"reason_question_asked": True},
        )
        transaction = self.get_transaction(user_ref, pending_question.transaction_id)
        if transaction is not None:
            updated = Transaction.from_dict({**transaction.to_dict(), "status": "awaiting_reason"})
            store.transactions[updated.transaction_id] = self._privacy.encrypt_json(updated.to_dict())
        store.pending_question = self._privacy.encrypt_json(payload)
        return StoredResult(202, {"pending_question": payload})

    def _add_transaction_reason(
        self,
        store: _UserStore,
        user_ref: str,
        transaction_id: str,
        reason: str,
        answered_at: str,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        transaction = self.get_transaction(user_ref, transaction_id)
        if transaction is None:
            raise DomainValidationError("transaction not found")
        updated = Transaction.from_dict(
            {**transaction.to_dict(), "reason": reason, "status": "recorded"}
        )
        payload = {"transaction_id": transaction_id, "reason": reason, "answered_at": answered_at}
        self._append_event(
            store,
            user_ref,
            EVENT_TRANSACTION_REASON_ADDED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )
        pending = self.get_pending_question(user_ref)
        if pending and pending.transaction_id == transaction_id:
            answered = PendingQuestion.from_dict(
                {
                    **pending.to_dict(),
                    "answered_at": answered_at,
                    "attempt_count": pending.attempt_count + 1,
                }
            )
            store.pending_question = self._privacy.encrypt_json(answered.to_dict())
        store.transactions[transaction_id] = self._privacy.encrypt_json(updated.to_dict())
        return StoredResult(200, {"transaction": updated.to_dict()})

    def _save_judgment(
        self,
        store: _UserStore,
        user_ref: str,
        judgment: JudgmentResult,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = judgment.to_dict()
        self._append_event(
            store,
            user_ref,
            EVENT_JUDGMENT_COMPLETED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
            redacted_metadata={
                "label": judgment.label,
                "fallback_used": judgment.fallback_used,
                "policy_version": judgment.policy_version,
            },
        )
        store.judgments[judgment.judgment_id] = self._privacy.encrypt_json(payload)
        transaction = self.get_transaction(user_ref, judgment.transaction_id)
        if transaction is not None:
            updated = Transaction.from_dict({**transaction.to_dict(), "status": "judged"})
            store.transactions[updated.transaction_id] = self._privacy.encrypt_json(updated.to_dict())
        store.metrics["judgments_completed"] += 1
        return StoredResult(201, {"judgment": payload})

    def _correct_judgment(
        self,
        store: _UserStore,
        user_ref: str,
        judgment_id: str,
        corrected_label: str,
        correction_reason: str | None,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        if corrected_label not in ALLOWED_JUDGMENT_LABELS:
            raise DomainValidationError("unsupported corrected_label")
        judgment = self.get_judgment(user_ref, judgment_id)
        if judgment is None:
            raise DomainValidationError("judgment not found")
        correction = JudgmentCorrection(
            judgment_id=judgment_id,
            original_label=judgment.label,
            corrected_label=corrected_label,
            correction_reason=correction_reason,
            corrected_at=utc_now_iso(),
        )
        payload = correction.to_dict()
        self._append_event(
            store,
            user_ref,
            EVENT_JUDGMENT_CORRECTED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
            redacted_metadata={"correction_flag": True},
        )
        transaction = self.get_transaction(user_ref, judgment.transaction_id)
        if transaction is not None:
            updated = Transaction.from_dict({**transaction.to_dict(), "status": "corrected"})
            store.transactions[updated.transaction_id] = self._privacy.encrypt_json(updated.to_dict())
        store.corrections[judgment_id] = self._privacy.encrypt_json(payload)
        store.metrics["corrections"] += 1
        return StoredResult(200, {"correction": payload})

    def _record_metric_event(
        self,
        user_ref: str,
        judgment_id: str,
        event_type: str,
        metric_name: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        return self._mutate(
            user_ref,
            idempotency_key,
            lambda store: self._record_metric_event_uncached(
                store,
                user_ref,
                judgment_id,
                event_type,
                metric_name,
                idempotency_key,
                correlation_id,
                source,
            ),
        )

    def _record_metric_event_uncached(
        self,
        store: _UserStore,
        user_ref: str,
        judgment_id: str,
        event_type: str,
        metric_name: str,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = {"judgment_id": judgment_id, "recorded_at": utc_now_iso()}
        self._append_event(
            store,
            user_ref,
            event_type,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
            redacted_metadata={"share_flag": True},
        )
        store.metrics[metric_name] += 1
        return StoredResult(200, {metric_name: store.metrics[metric_name]})

    def _revoke_account(
        self,
        store: _UserStore,
        user_ref: str,
        connection_id: str,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = {"connection_id": connection_id, "revoked_at": utc_now_iso()}
        self._append_event(
            store,
            user_ref,
            EVENT_ACCOUNT_REVOKED,
            payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )
        store.metrics["accounts_revoked"] += 1
        return StoredResult(200, {"account_revoked": True})

    def _import_legacy_metadata(
        self,
        store: _UserStore,
        user_ref: str,
        metadata: Mapping[str, Any],
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        if store.legacy_imported:
            return StoredResult(200, {"legacy_imported": True})
        allowed = {
            key: deepcopy(metadata[key])
            for key in ("category_counts", "emotion_labels", "message_count")
            if key in metadata
        }
        self._append_event(
            store,
            user_ref,
            EVENT_LEGACY_IMPORTED,
            allowed,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )
        store.legacy_imported = True
        store.metrics["legacy_imports"] += 1
        return StoredResult(200, {"legacy_imported": True})

    def _request_data_deletion(
        self,
        store: _UserStore,
        user_ref: str,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        deletion_id = str(uuid.uuid4())
        self._append_event(
            store,
            user_ref,
            EVENT_DATA_DELETION_REQUESTED,
            {"requested_at": utc_now_iso()},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source=source,
        )
        self.deletion_metrics.append(
            {"deletion_id": deletion_id, "completed_at": utc_now_iso()}
        )
        self._users[user_ref] = _UserStore()
        return StoredResult(204, {})

    def _decode_result(self, encrypted: str) -> StoredResult:
        payload = self._privacy.decrypt_json(encrypted)
        return StoredResult(status=int(payload["status"]), body=dict(payload["body"]))
