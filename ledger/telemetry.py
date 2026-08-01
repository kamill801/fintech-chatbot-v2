from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


ALLOWED_TELEMETRY_FIELDS = frozenset(
    {
        "event_type",
        "event_id",
        "user_ref",
        "label",
        "confidence_band",
        "adapter_source",
        "reason_question_asked",
        "fallback_used",
        "correction_flag",
        "share_flag",
        "latency_ms",
        "redaction_status",
        "policy_version",
    }
)

FORBIDDEN_TELEMETRY_FIELDS = frozenset(
    {
        "user_id",
        "user_message",
        "assistant_reply",
        "amount_krw",
        "merchant",
        "description",
        "reason",
        "monthly_income_krw",
        "liquid_assets_krw",
        "fixed_expenses_krw",
        "monthly_debt_payment_krw",
        "discretionary_budget_krw",
        "account_number",
        "source_reference",
        "provider_token",
    }
)


class TelemetryValidationError(ValueError):
    pass


@dataclass(frozen=True)
class TelemetryEvent:
    event_type: str
    event_id: str
    user_ref: str
    label: str | None = None
    confidence_band: str | None = None
    adapter_source: str | None = None
    reason_question_asked: bool = False
    fallback_used: bool = False
    correction_flag: bool = False
    share_flag: bool = False
    latency_ms: int | None = None
    redaction_status: str = "allowlisted"
    policy_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def confidence_band(confidence: float | None) -> str | None:
    if confidence is None:
        return None
    if confidence < 0.5:
        return "low"
    if confidence < 0.8:
        return "medium"
    return "high"


def validate_telemetry_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    keys = set(payload)
    forbidden = keys & FORBIDDEN_TELEMETRY_FIELDS
    unknown = keys - ALLOWED_TELEMETRY_FIELDS
    if forbidden:
        raise TelemetryValidationError(
            "forbidden telemetry fields: " + ", ".join(sorted(forbidden))
        )
    if unknown:
        raise TelemetryValidationError(
            "unapproved telemetry fields: " + ", ".join(sorted(unknown))
        )
    return dict(payload)
