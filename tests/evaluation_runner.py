from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ledger.adapters.openai_judge import JudgmentRequest
from ledger.application.signals import SignalInputs, compute_signal_set


class JudgeLike(Protocol):
    def judge(self, request: JudgmentRequest) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class LabelAgreementReport:
    fixture_version: int
    policy_version: str
    total: int
    matches: int
    agreement: float
    live_model_used: bool


def load_fixture(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_label_agreement(
    fixture: dict[str, Any], judge: JudgeLike, *, live_model_used: bool = False
) -> LabelAgreementReport:
    cases = list(fixture["cases"])
    matches = 0
    for case in cases:
        request = _request_for_case(case, str(fixture["policy_version"]))
        actual = judge.judge(request).label
        if actual == case["expected_label"]:
            matches += 1
    total = len(cases)
    return LabelAgreementReport(
        fixture_version=int(fixture["schema_version"]),
        policy_version=str(fixture["policy_version"]),
        total=total,
        matches=matches,
        agreement=round(matches / total, 4) if total else 0.0,
        live_model_used=live_model_used,
    )


def _request_for_case(case: dict[str, Any], policy_version: str) -> JudgmentRequest:
    transaction = case["transaction"]
    amount = int(transaction["amount_krw"])
    category = str(transaction["category"])
    reason = transaction.get("reason")
    signals = compute_signal_set(
        SignalInputs(
            transaction_amount_krw=amount,
            discretionary_budget_krw=800000,
            spent_before_transaction_krw=420000,
            category=category,
            goal_pressure=0.55,
            baseline_deviation=1.2,
            recurrence_30d=3 if category in {"cafe", "food_delivery", "shopping"} else 0,
            has_reason=bool(reason),
            history_complete=True,
        )
    )
    return JudgmentRequest(
        transaction_id=str(case["case_id"]),
        amount_krw=amount,
        category=category,
        signals=signals,
        user_reason=reason,
        policy_version=policy_version,
    )
