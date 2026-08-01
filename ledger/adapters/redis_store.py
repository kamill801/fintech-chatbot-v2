from __future__ import annotations

import json
import uuid
from typing import Any, Mapping, Sequence

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


class RedisLedgerRepository(LedgerRepository):
    def __init__(self, redis_client: Any, privacy: PrivacyService) -> None:
        self._redis = redis_client
        self._privacy = privacy

    @classmethod
    def from_url(cls, redis_url: str, privacy: PrivacyService) -> RedisLedgerRepository:
        import redis

        return cls(redis.Redis.from_url(redis_url, decode_responses=True), privacy)

    def get_profile(self, user_ref: str) -> FinancialProfile | None:
        encrypted = self._redis.get(self._key(user_ref, "profile"))
        if encrypted is None:
            return None
        return FinancialProfile.from_dict(self._privacy.decrypt_json(encrypted))

    def get_cached_result(
        self, user_ref: str, idempotency_key: str
    ) -> StoredResult | None:
        encrypted = self._redis.get(self._idempotency_key(user_ref, idempotency_key))
        if encrypted is None:
            return None
        payload = self._privacy.decrypt_json(encrypted)
        return StoredResult(int(payload["status"]), dict(payload["body"]))

    def cache_result(
        self, user_ref: str, idempotency_key: str, result: StoredResult
    ) -> None:
        self._redis.set(
            self._idempotency_key(user_ref, idempotency_key),
            self._privacy.encrypt_json(
                {"status": result.status, "body": result.body}
            ),
            ex=self._privacy.retention_seconds,
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
            lambda: self._upsert_profile(profile, idempotency_key, correlation_id, source),
        )

    def get_settings(self, user_ref: str) -> UserSettings:
        encrypted = self._redis.get(self._key(user_ref, "settings"))
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
            lambda: self._update_settings(
                user_ref, settings, idempotency_key, correlation_id, source
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
            lambda: self._record_transaction(
                transaction, idempotency_key, correlation_id, source
            ),
        )

    def get_transaction(self, user_ref: str, transaction_id: str) -> Transaction | None:
        encrypted = self._redis.get(self._transaction_key(user_ref, transaction_id))
        if encrypted is None:
            return None
        return Transaction.from_dict(self._privacy.decrypt_json(encrypted))

    def list_transactions(self, user_ref: str) -> Sequence[Transaction]:
        ids = self._redis.zrange(self._key(user_ref, "transactions"), 0, -1)
        transactions = []
        for transaction_id in ids:
            transaction = self.get_transaction(user_ref, transaction_id)
            if transaction is not None:
                transactions.append(transaction)
        return transactions

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
            lambda: self._save_pending_question(
                user_ref, pending_question, idempotency_key, correlation_id, source
            ),
        )

    def get_pending_question(self, user_ref: str) -> PendingQuestion | None:
        encrypted = self._redis.get(self._key(user_ref, "pending_question"))
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
            lambda: self._add_transaction_reason(
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
            lambda: self._save_judgment(
                user_ref, judgment, idempotency_key, correlation_id, source
            ),
        )

    def get_judgment(self, user_ref: str, judgment_id: str) -> JudgmentResult | None:
        encrypted = self._redis.get(self._judgment_key(user_ref, judgment_id))
        if encrypted is None:
            return None
        return JudgmentResult.from_dict(self._privacy.decrypt_json(encrypted))

    def get_judgment_for_transaction(
        self, user_ref: str, transaction_id: str
    ) -> JudgmentResult | None:
        for key in self._redis.scan_iter(match=self._key(user_ref, "judgment:*")):
            encrypted = self._redis.get(key)
            if encrypted is None:
                continue
            judgment = JudgmentResult.from_dict(self._privacy.decrypt_json(encrypted))
            if judgment.transaction_id == transaction_id:
                return judgment
        return None

    def get_judgment_correction(
        self, user_ref: str, judgment_id: str
    ) -> JudgmentCorrection | None:
        encrypted = self._redis.get(self._correction_key(user_ref, judgment_id))
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
            lambda: self._correct_judgment(
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
            lambda: self._revoke_account(
                user_ref, connection_id, idempotency_key, correlation_id, source
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
            lambda: self._import_legacy_metadata(
                user_ref, metadata, idempotency_key, correlation_id, source
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
            user_ref, idempotency_key, correlation_id, source
        )

    def get_metrics(self, user_ref: str) -> dict[str, Any]:
        encrypted = self._redis.get(self._key(user_ref, "metrics"))
        if encrypted is None:
            return {
                "transactions_recorded": 0,
                "judgments_completed": 0,
                "corrections": 0,
                "share_views": 0,
                "share_clicks": 0,
                "accounts_revoked": 0,
                "legacy_imports": 0,
            }
        return self._privacy.decrypt_json(encrypted)

    def list_events(self, user_ref: str) -> Sequence[EventEnvelope]:
        rows = self._redis.xrange(self._key(user_ref, "events"), "-", "+")
        return [EventEnvelope.from_dict(row[1]) for row in rows]

    def _mutate(
        self,
        user_ref: str,
        idempotency_key: str,
        operation: Any,
    ) -> StoredResult:
        if not idempotency_key:
            raise DomainValidationError("idempotency_key is required")
        result_key = self._idempotency_key(user_ref, idempotency_key)
        lock = self._redis.lock(
            self._key(user_ref, "mutation-lock"), timeout=15, blocking_timeout=5
        )
        with lock:
            cached = self._redis.get(result_key)
            if cached is not None:
                payload = self._privacy.decrypt_json(cached)
                return StoredResult(int(payload["status"]), dict(payload["body"]))
            result = operation()
            self._redis.set(
                result_key,
                self._privacy.encrypt_json(
                    {"status": result.status, "body": result.body}
                ),
                ex=self._privacy.retention_seconds,
            )
            self._refresh_retention(user_ref)
            return result

    def _append_event(
        self,
        pipe: Any,
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
        fields = event.to_dict()
        fields["schema_version"] = str(fields["schema_version"])
        fields["redacted_metadata"] = json.dumps(
            fields["redacted_metadata"], ensure_ascii=False, sort_keys=True
        )
        pipe.xadd(self._key(user_ref, "events"), fields)
        return event

    def _upsert_profile(
        self,
        profile: FinancialProfile,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = profile.to_dict()
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                profile.user_ref,
                EVENT_PROFILE_UPSERTED,
                payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
            )
            pipe.set(self._key(profile.user_ref, "profile"), self._privacy.encrypt_json(payload))
            pipe.execute()
        return StoredResult(200, {"profile": payload})

    def _update_settings(
        self,
        user_ref: str,
        settings: UserSettings,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = settings.to_dict()
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                user_ref,
                EVENT_SETTINGS_ROAST_CHANGED,
                payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
                redacted_metadata={"roast_enabled": settings.roast_enabled},
            )
            pipe.set(self._key(user_ref, "settings"), self._privacy.encrypt_json(payload))
            pipe.execute()
        return StoredResult(200, {"settings": payload})

    def _record_transaction(
        self,
        transaction: Transaction,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = transaction.to_dict()
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                transaction.user_ref,
                EVENT_TRANSACTION_RECORDED,
                payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
                redacted_metadata={"adapter_source": transaction.source},
            )
            pipe.set(
                self._transaction_key(transaction.user_ref, transaction.transaction_id),
                self._privacy.encrypt_json(payload),
            )
            pipe.zadd(
                self._key(transaction.user_ref, "transactions"),
                {transaction.transaction_id: self._score(transaction.occurred_at)},
            )
            self._incr_metric(pipe, transaction.user_ref, "transactions_recorded")
            pipe.execute()
        return StoredResult(201, {"transaction": payload})

    def _save_pending_question(
        self,
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
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                user_ref,
                EVENT_JUDGMENT_REASON_REQUESTED,
                payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
                redacted_metadata={"reason_question_asked": True},
            )
            pipe.set(self._key(user_ref, "pending_question"), self._privacy.encrypt_json(payload))
            transaction = self.get_transaction(user_ref, pending_question.transaction_id)
            if transaction is not None:
                updated = Transaction.from_dict({**transaction.to_dict(), "status": "awaiting_reason"})
                pipe.set(
                    self._transaction_key(user_ref, updated.transaction_id),
                    self._privacy.encrypt_json(updated.to_dict()),
                )
            pipe.execute()
        return StoredResult(202, {"pending_question": payload})

    def _add_transaction_reason(
        self,
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
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                user_ref,
                EVENT_TRANSACTION_REASON_ADDED,
                payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
            )
            pipe.set(
                self._transaction_key(user_ref, transaction_id),
                self._privacy.encrypt_json(updated.to_dict()),
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
                pipe.set(
                    self._key(user_ref, "pending_question"),
                    self._privacy.encrypt_json(answered.to_dict()),
                )
            pipe.execute()
        return StoredResult(200, {"transaction": updated.to_dict()})

    def _save_judgment(
        self,
        user_ref: str,
        judgment: JudgmentResult,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = judgment.to_dict()
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
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
            pipe.set(
                self._judgment_key(user_ref, judgment.judgment_id),
                self._privacy.encrypt_json(payload),
            )
            transaction = self.get_transaction(user_ref, judgment.transaction_id)
            if transaction is not None:
                updated = Transaction.from_dict({**transaction.to_dict(), "status": "judged"})
                pipe.set(
                    self._transaction_key(user_ref, updated.transaction_id),
                    self._privacy.encrypt_json(updated.to_dict()),
                )
            self._incr_metric(pipe, user_ref, "judgments_completed")
            pipe.execute()
        return StoredResult(201, {"judgment": payload})

    def _correct_judgment(
        self,
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
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
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
                pipe.set(
                    self._transaction_key(user_ref, updated.transaction_id),
                    self._privacy.encrypt_json(updated.to_dict()),
                )
            pipe.set(
                self._correction_key(user_ref, judgment_id),
                self._privacy.encrypt_json(payload),
            )
            self._incr_metric(pipe, user_ref, "corrections")
            pipe.execute()
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
            lambda: self._record_metric_event_uncached(
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
        user_ref: str,
        judgment_id: str,
        event_type: str,
        metric_name: str,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = {"judgment_id": judgment_id, "recorded_at": utc_now_iso()}
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                user_ref,
                event_type,
                payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
                redacted_metadata={"share_flag": True},
            )
            value = self._incr_metric(pipe, user_ref, metric_name)
            pipe.execute()
        return StoredResult(200, {metric_name: value})

    def _revoke_account(
        self,
        user_ref: str,
        connection_id: str,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        payload = {"connection_id": connection_id, "revoked_at": utc_now_iso()}
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                user_ref,
                EVENT_ACCOUNT_REVOKED,
                payload,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
            )
            self._incr_metric(pipe, user_ref, "accounts_revoked")
            pipe.execute()
        return StoredResult(200, {"account_revoked": True})

    def _import_legacy_metadata(
        self,
        user_ref: str,
        metadata: Mapping[str, Any],
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        if self._redis.get(self._key(user_ref, "legacy_imported")):
            return StoredResult(200, {"legacy_imported": True})
        allowed = {
            key: metadata[key]
            for key in ("category_counts", "emotion_labels", "message_count")
            if key in metadata
        }
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                user_ref,
                EVENT_LEGACY_IMPORTED,
                allowed,
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
            )
            pipe.set(self._key(user_ref, "legacy_imported"), "1")
            self._incr_metric(pipe, user_ref, "legacy_imports")
            pipe.execute()
        return StoredResult(200, {"legacy_imported": True})

    def _request_data_deletion(
        self,
        user_ref: str,
        idempotency_key: str,
        correlation_id: str,
        source: str,
    ) -> StoredResult:
        deletion_id = str(uuid.uuid4())
        with self._redis.pipeline(transaction=True) as pipe:
            self._append_event(
                pipe,
                user_ref,
                EVENT_DATA_DELETION_REQUESTED,
                {"requested_at": utc_now_iso()},
                idempotency_key=idempotency_key,
                correlation_id=correlation_id,
                source=source,
            )
            for key in self._user_keys(user_ref):
                pipe.delete(key)
            pipe.xadd(
                "ledger:deletion_metrics",
                {"deletion_id": deletion_id, "completed_at": utc_now_iso()},
            )
            pipe.execute()
        return StoredResult(204, {})

    def _incr_metric(self, pipe: Any, user_ref: str, metric_name: str) -> int:
        metrics = self.get_metrics(user_ref)
        metrics[metric_name] = int(metrics.get(metric_name, 0)) + 1
        pipe.set(self._key(user_ref, "metrics"), self._privacy.encrypt_json(metrics))
        return metrics[metric_name]

    @staticmethod
    def _score(occurred_at: str) -> float:
        from datetime import datetime

        return datetime.fromisoformat(occurred_at.replace("Z", "+00:00")).timestamp()

    @staticmethod
    def _key(user_ref: str, suffix: str) -> str:
        return f"ledger:{user_ref}:{suffix}"

    def _transaction_key(self, user_ref: str, transaction_id: str) -> str:
        return self._key(user_ref, f"transaction:{transaction_id}")

    def _judgment_key(self, user_ref: str, judgment_id: str) -> str:
        return self._key(user_ref, f"judgment:{judgment_id}")

    def _correction_key(self, user_ref: str, judgment_id: str) -> str:
        return self._key(user_ref, f"correction:{judgment_id}")

    def _idempotency_key(self, user_ref: str, idempotency_key: str) -> str:
        return self._key(user_ref, f"idempotency:{idempotency_key}")

    def _user_keys(self, user_ref: str) -> list[str]:
        explicit = [
            self._key(user_ref, "events"),
            self._key(user_ref, "profile"),
            self._key(user_ref, "settings"),
            self._key(user_ref, "transactions"),
            self._key(user_ref, "pending_question"),
            self._key(user_ref, "legacy_imported"),
            self._key(user_ref, "metrics"),
        ]
        patterns = [
            self._key(user_ref, "transaction:*"),
            self._key(user_ref, "judgment:*"),
            self._key(user_ref, "correction:*"),
            self._key(user_ref, "idempotency:*"),
        ]
        found: list[str] = []
        for pattern in patterns:
            found.extend(self._redis.scan_iter(match=pattern))
        return explicit + found

    def _refresh_retention(self, user_ref: str) -> None:
        keys = [key for key in self._user_keys(user_ref) if self._redis.exists(key)]
        if not keys:
            return
        with self._redis.pipeline(transaction=False) as pipe:
            for key in keys:
                pipe.expire(key, self._privacy.retention_seconds)
            pipe.execute()
