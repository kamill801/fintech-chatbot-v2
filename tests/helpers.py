from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ledger.adapters.memory import InMemoryLedgerRepository
from ledger.adapters.openai_judge import JudgmentRequest, deterministic_fallback_judgment
from ledger.adapters.synthetic import DisabledProductionAccountAdapter
from ledger.application.service import LedgerService
from ledger.privacy import PrivacyConfig, PrivacyService


FERNET_KEY = b"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
USER_REF_SECRET = b"unit-test-user-ref-secret"


def fixed_privacy() -> PrivacyService:
    return PrivacyService(
        PrivacyConfig(
            encryption_key=FERNET_KEY,
            user_ref_secret=USER_REF_SECRET,
            app_env="test",
        )
    )


class FallbackJudge:
    def __init__(self) -> None:
        self.requests: list[JudgmentRequest] = []

    def judge(self, request: JudgmentRequest):
        self.requests.append(request)
        return deterministic_fallback_judgment(request)


def service_with_memory(
    *,
    account_adapter: Any | None = None,
    telemetry_sink: Any | None = None,
    judgment_quota: Any | None = None,
) -> tuple[LedgerService, InMemoryLedgerRepository, PrivacyService, FallbackJudge]:
    privacy = fixed_privacy()
    repository = InMemoryLedgerRepository(privacy)
    judge = FallbackJudge()
    service = LedgerService(
        repository,
        judge,
        account_adapter or DisabledProductionAccountAdapter(),
        telemetry_sink=telemetry_sink,
        judgment_quota=judgment_quota,
    )
    return service, repository, privacy, judge


def profile_payload() -> dict[str, Any]:
    return {
        "monthly_income_krw": 3500000,
        "liquid_assets_krw": 10000000,
        "fixed_expenses_krw": 1400000,
        "monthly_debt_payment_krw": 300000,
        "discretionary_budget_krw": 800000,
        "goal": {
            "goal_id": "goal-1",
            "name": "비상금",
            "target_amount_krw": 10000000,
            "current_amount_krw": 3000000,
            "target_date": "2027-12-31",
        },
    }


def utc(value: str = "2026-08-01T00:00:00Z") -> str:
    return value


def correlation_id() -> str:
    return "corr-test"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
