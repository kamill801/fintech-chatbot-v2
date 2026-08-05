from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from ledger.domain.models import SCHEMA_VERSION, DomainValidationError, parse_utc_datetime


EVENT_PROFILE_UPSERTED = "profile.upserted"
EVENT_SETTINGS_ROAST_CHANGED = "settings.roast_changed"
EVENT_TRANSACTION_RECORDED = "transaction.recorded"
EVENT_JUDGMENT_REASON_REQUESTED = "judgment.reason_requested"
EVENT_TRANSACTION_REASON_ADDED = "transaction.reason_added"
EVENT_JUDGMENT_COMPLETED = "judgment.completed"
EVENT_JUDGMENT_CORRECTED = "judgment.corrected"
EVENT_SHARE_VIEWED = "share.viewed"
EVENT_SHARE_CLICKED = "share.clicked"
EVENT_ACCOUNT_REVOKED = "account.revoked"
EVENT_LEGACY_IMPORTED = "legacy.imported"
EVENT_DATA_DELETION_REQUESTED = "data.deletion_requested"

ALLOWED_EVENT_TYPES = frozenset(
    {
        EVENT_PROFILE_UPSERTED,
        EVENT_SETTINGS_ROAST_CHANGED,
        EVENT_TRANSACTION_RECORDED,
        EVENT_JUDGMENT_REASON_REQUESTED,
        EVENT_TRANSACTION_REASON_ADDED,
        EVENT_JUDGMENT_COMPLETED,
        EVENT_JUDGMENT_CORRECTED,
        EVENT_SHARE_VIEWED,
        EVENT_SHARE_CLICKED,
        EVENT_ACCOUNT_REVOKED,
        EVENT_LEGACY_IMPORTED,
        EVENT_DATA_DELETION_REQUESTED,
    }
)


@dataclass(frozen=True)
class EventEnvelope:
    event_id: str
    user_ref: str
    event_type: str
    schema_version: int
    created_at: str
    source: str
    correlation_id: str
    idempotency_key: str
    redacted_metadata: dict[str, Any] = field(default_factory=dict)
    encrypted_payload: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            raise DomainValidationError("event_id is required")
        if not self.user_ref:
            raise DomainValidationError("user_ref is required")
        if self.event_type not in ALLOWED_EVENT_TYPES:
            raise DomainValidationError("unsupported event_type")
        if self.schema_version != SCHEMA_VERSION:
            raise DomainValidationError("unsupported event schema_version")
        parse_utc_datetime(self.created_at, "created_at")
        if not self.source:
            raise DomainValidationError("source is required")
        if not self.correlation_id:
            raise DomainValidationError("correlation_id is required")
        if not self.idempotency_key:
            raise DomainValidationError("idempotency_key is required")
        if not isinstance(self.redacted_metadata, dict):
            raise DomainValidationError("redacted_metadata must be a dict")
        if not isinstance(self.encrypted_payload, str) or not self.encrypted_payload:
            raise DomainValidationError("encrypted_payload is required")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> EventEnvelope:
        metadata = payload.get("redacted_metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return cls(
            event_id=str(payload["event_id"]),
            user_ref=str(payload["user_ref"]),
            event_type=str(payload["event_type"]),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
            created_at=str(payload["created_at"]),
            source=str(payload["source"]),
            correlation_id=str(payload["correlation_id"]),
            idempotency_key=str(payload["idempotency_key"]),
            redacted_metadata=dict(metadata),
            encrypted_payload=str(payload["encrypted_payload"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
