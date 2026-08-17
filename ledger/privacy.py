from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import warnings
from dataclasses import dataclass
from typing import Any, Mapping

from cryptography.fernet import Fernet


OPENAI_PROMPT_ALLOWLIST = frozenset(
    {
        "amount_bucket",
        "amount_krw",
        "category",
        "budget_usage_after",
        "transaction_budget_share",
        "goal_pressure",
        "baseline_deviation",
        "recurrence_30d",
        "essentiality",
        "risk_score",
        "data_confidence",
        "requires_reason",
        "factors",
        "user_reason",
        "spending_rules",
        "reflection_context",
        "policy_version",
    }
)

TELEMETRY_ALLOWLIST = frozenset(
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

SHARE_ALLOWLIST = frozenset(
    {"label", "roast_message", "category", "recommended_action"}
)

FORBIDDEN_EXTERNAL_FIELDS = frozenset(
    {
        "raw_user_id",
        "user_id",
        "account_number",
        "provider_token",
        "source_reference",
        "merchant",
        "description",
        "reason",
        "raw_reason",
        "monthly_income_krw",
        "liquid_assets_krw",
        "fixed_expenses_krw",
        "monthly_debt_payment_krw",
        "discretionary_budget_krw",
    }
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?82[-\s]?)?0?1[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)")
_LONG_NUMBER_RE = re.compile(r"(?<!\d)\d(?:[-\s]?\d){7,}(?!\d)")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACE_RE = re.compile(r"\s+")


class PrivacyError(ValueError):
    pass


@dataclass(frozen=True)
class PrivacyConfig:
    encryption_key: bytes
    user_ref_secret: bytes
    app_env: str = "development"
    retention_days: int = 365

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> PrivacyConfig:
        source = os.environ if environ is None else environ
        app_env = source.get("APP_ENV", "development")
        try:
            retention_days = int(source.get("LEDGER_RETENTION_DAYS", "365"))
        except ValueError as exc:
            raise PrivacyError("LEDGER_RETENTION_DAYS must be an integer") from exc
        if retention_days <= 0:
            raise PrivacyError("LEDGER_RETENTION_DAYS must be positive")
        encryption_key = source.get("LEDGER_ENCRYPTION_KEY")
        user_ref_secret = source.get("LEDGER_USER_REF_SECRET")
        if app_env == "production":
            if not encryption_key:
                raise PrivacyError("LEDGER_ENCRYPTION_KEY is required in production")
            if not user_ref_secret:
                raise PrivacyError("LEDGER_USER_REF_SECRET is required in production")
        if not encryption_key:
            warnings.warn(
                "Using ephemeral development LEDGER_ENCRYPTION_KEY",
                RuntimeWarning,
                stacklevel=2,
            )
            encryption_key = Fernet.generate_key().decode("ascii")
        if not user_ref_secret:
            warnings.warn(
                "Using ephemeral development LEDGER_USER_REF_SECRET",
                RuntimeWarning,
                stacklevel=2,
            )
            user_ref_secret = secrets.token_urlsafe(32)
        return cls(
            encryption_key=encryption_key.encode("ascii"),
            user_ref_secret=user_ref_secret.encode("utf-8"),
            app_env=app_env,
            retention_days=retention_days,
        )


class PrivacyService:
    def __init__(self, config: PrivacyConfig) -> None:
        self._fernet = Fernet(config.encryption_key)
        self._user_ref_secret = config.user_ref_secret
        self.retention_days = config.retention_days
        self.retention_seconds = config.retention_days * 24 * 60 * 60

    def user_ref(self, raw_identifier: str) -> str:
        if not raw_identifier:
            raise PrivacyError("raw identifier is required")
        digest = hmac.new(
            self._user_ref_secret,
            raw_identifier.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        token = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
        return f"usr_{token[:43]}"

    def encrypt_json(self, payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return self._fernet.encrypt(encoded).decode("ascii")

    def decrypt_json(self, ciphertext: str) -> dict[str, Any]:
        if not ciphertext:
            raise PrivacyError("ciphertext is required")
        decoded = self._fernet.decrypt(ciphertext.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict):
            raise PrivacyError("encrypted payload must decode to an object")
        return payload


def sanitize_free_text(value: str | None, *, max_length: int = 500) -> str | None:
    if value is None:
        return None
    sanitized = _CONTROL_RE.sub(" ", value)
    sanitized = _EMAIL_RE.sub("[redacted-email]", sanitized)
    sanitized = _PHONE_RE.sub("[redacted-phone]", sanitized)
    sanitized = _LONG_NUMBER_RE.sub("[redacted-number]", sanitized)
    sanitized = _SPACE_RE.sub(" ", sanitized).strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    return sanitized


def amount_bucket(amount_krw: int) -> str:
    if amount_krw < 10_000:
        return "under_10000"
    if amount_krw < 50_000:
        return "10000_to_49999"
    if amount_krw < 100_000:
        return "50000_to_99999"
    if amount_krw < 300_000:
        return "100000_to_299999"
    return "300000_plus"


def enforce_allowlist(
    payload: Mapping[str, Any],
    allowlist: frozenset[str],
    *,
    sink_name: str,
) -> dict[str, Any]:
    keys = set(payload)
    forbidden = keys & FORBIDDEN_EXTERNAL_FIELDS
    unknown = keys - allowlist
    if forbidden:
        raise PrivacyError(
            f"{sink_name} payload contains forbidden fields: "
            + ", ".join(sorted(forbidden))
        )
    if unknown:
        raise PrivacyError(
            f"{sink_name} payload contains unapproved fields: "
            + ", ".join(sorted(unknown))
        )
    return dict(payload)


def build_prompt_payload(
    *,
    amount_krw: int | None,
    category: str,
    signals: Mapping[str, Any],
    user_reason: str | None,
    spending_rules: list[str] | None = None,
    reflection_context: Mapping[str, int | float] | None = None,
    policy_version: str,
    include_exact_amount: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "amount_bucket": amount_bucket(amount_krw or 0),
        "category": category,
        "policy_version": policy_version,
    }
    if user_reason:
        payload["user_reason"] = sanitize_free_text(user_reason)
    if spending_rules:
        sanitized_rules = []
        for rule in spending_rules[:8]:
            sanitized_rule = sanitize_free_text(rule, max_length=120)
            if sanitized_rule:
                sanitized_rules.append(sanitized_rule)
        payload["spending_rules"] = sanitized_rules
    if reflection_context:
        payload["reflection_context"] = {
            key: reflection_context[key]
            for key in (
                "category_reflected_count",
                "category_regretted_count",
                "category_regret_rate",
            )
            if key in reflection_context
        }
    if include_exact_amount and amount_krw is not None:
        payload["amount_krw"] = amount_krw
    for key in (
        "budget_usage_after",
        "transaction_budget_share",
        "goal_pressure",
        "baseline_deviation",
        "recurrence_30d",
        "essentiality",
        "risk_score",
        "data_confidence",
        "requires_reason",
        "factors",
    ):
        payload[key] = signals[key]
    return enforce_allowlist(payload, OPENAI_PROMPT_ALLOWLIST, sink_name="prompt")


def sanitize_telemetry_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    return enforce_allowlist(payload, TELEMETRY_ALLOWLIST, sink_name="telemetry")


def sanitize_share_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    allowed = enforce_allowlist(payload, SHARE_ALLOWLIST, sink_name="share")
    if "roast_message" in allowed:
        allowed["roast_message"] = sanitize_free_text(str(allowed["roast_message"]))
    return allowed
