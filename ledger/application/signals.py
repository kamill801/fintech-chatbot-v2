"""Versioned deterministic spending-risk signal policy."""

from __future__ import annotations

from dataclasses import dataclass

from ledger.domain.models import DeterministicSignalSet


POLICY_VERSION = "overspending-v1"
UNKNOWN_CATEGORY = "unknown"
HIGH_BUDGET_SHARE_THRESHOLD = 0.20
LOW_REASON_RISK_THRESHOLD = 0.35
HIGH_REASON_RISK_THRESHOLD = 0.75
MIN_DATA_CONFIDENCE = 0.75

ESSENTIALITY_BY_CATEGORY = {
    "housing": 1.0,
    "rent": 1.0,
    "utilities": 0.95,
    "medical": 0.95,
    "healthcare": 0.95,
    "groceries": 0.80,
    "transport": 0.65,
    "education": 0.60,
    "food_delivery": 0.25,
    "cafe": 0.10,
    "shopping": 0.10,
    "alcohol": 0.05,
    UNKNOWN_CATEGORY: 0.0,
}


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class SignalInputs:
    """Inputs needed by the overspending-v1 signal formula.

    baseline_deviation is a ratio where 1.0 means normal baseline spend. For the
    normalized policy term, 2.0 or above is treated as maximum deviation.
    recurrence_30d is capped at five repeats for the normalized recurrence term.
    """

    transaction_amount_krw: int
    discretionary_budget_krw: int
    spent_before_transaction_krw: int = 0
    category: str = UNKNOWN_CATEGORY
    goal_pressure: float = 0.0
    baseline_deviation: float = 1.0
    recurrence_30d: int = 0
    has_reason: bool = False
    profile_complete: bool = True
    history_complete: bool = True


def _normalized_baseline_deviation(baseline_deviation: float) -> float:
    return clamp(baseline_deviation / 2.0)


def _normalized_recurrence(recurrence_30d: int) -> float:
    return clamp(recurrence_30d / 5.0)


def _data_confidence(profile_complete: bool, history_complete: bool) -> float:
    confidence = 1.0
    if not profile_complete:
        confidence -= 0.35
    if not history_complete:
        confidence -= 0.30
    return clamp(confidence)


def _factor_names(
    *,
    budget_usage_after: float,
    transaction_budget_share: float,
    goal_pressure: float,
    normalized_baseline_deviation: float,
    normalized_recurrence: float,
    essentiality: float,
    data_confidence: float,
) -> tuple[str, ...]:
    factors: list[str] = []
    if budget_usage_after >= 0.70:
        factors.append("budget_usage")
    if transaction_budget_share >= HIGH_BUDGET_SHARE_THRESHOLD:
        factors.append("transaction_budget_share")
    if goal_pressure >= 0.60:
        factors.append("goal_pressure")
    if normalized_baseline_deviation >= 0.60:
        factors.append("baseline_deviation")
    if normalized_recurrence >= 0.40:
        factors.append("recurrence_30d")
    if essentiality >= 0.60:
        factors.append("essentiality")
    if data_confidence < MIN_DATA_CONFIDENCE:
        factors.append("data_confidence")
    return tuple(factors)


def compute_signal_set(inputs: SignalInputs) -> DeterministicSignalSet:
    if inputs.transaction_amount_krw < 0:
        raise ValueError("transaction_amount_krw must be non-negative")
    if inputs.discretionary_budget_krw <= 0:
        raise ValueError("discretionary_budget_krw must be positive")
    if inputs.spent_before_transaction_krw < 0:
        raise ValueError("spent_before_transaction_krw must be non-negative")
    if inputs.recurrence_30d < 0:
        raise ValueError("recurrence_30d must be non-negative")

    category = (inputs.category or UNKNOWN_CATEGORY).strip().lower() or UNKNOWN_CATEGORY
    budget_usage_after = clamp(
        (inputs.spent_before_transaction_krw + inputs.transaction_amount_krw)
        / inputs.discretionary_budget_krw
    )
    transaction_budget_share = clamp(
        inputs.transaction_amount_krw / inputs.discretionary_budget_krw
    )
    goal_pressure = clamp(inputs.goal_pressure)
    baseline_deviation = max(0.0, inputs.baseline_deviation)
    normalized_baseline_deviation = _normalized_baseline_deviation(baseline_deviation)
    normalized_recurrence = _normalized_recurrence(inputs.recurrence_30d)
    essentiality = clamp(ESSENTIALITY_BY_CATEGORY.get(category, 0.20))

    risk_score = clamp(
        0.30 * budget_usage_after
        + 0.25 * transaction_budget_share
        + 0.20 * goal_pressure
        + 0.15 * normalized_baseline_deviation
        + 0.10 * normalized_recurrence
        - 0.25 * essentiality
    )
    data_confidence = _data_confidence(inputs.profile_complete, inputs.history_complete)
    high_budget_share_without_reason = (
        transaction_budget_share >= HIGH_BUDGET_SHARE_THRESHOLD and not inputs.has_reason
    )
    requires_reason = (
        LOW_REASON_RISK_THRESHOLD <= risk_score <= HIGH_REASON_RISK_THRESHOLD
        or category == UNKNOWN_CATEGORY
        or high_budget_share_without_reason
        or data_confidence < MIN_DATA_CONFIDENCE
    )

    factors = _factor_names(
        budget_usage_after=budget_usage_after,
        transaction_budget_share=transaction_budget_share,
        goal_pressure=goal_pressure,
        normalized_baseline_deviation=normalized_baseline_deviation,
        normalized_recurrence=normalized_recurrence,
        essentiality=essentiality,
        data_confidence=data_confidence,
    )
    return DeterministicSignalSet(
        budget_usage_after=round(budget_usage_after, 4),
        transaction_budget_share=round(transaction_budget_share, 4),
        goal_pressure=round(goal_pressure, 4),
        baseline_deviation=round(baseline_deviation, 4),
        recurrence_30d=inputs.recurrence_30d,
        essentiality=round(essentiality, 4),
        risk_score=round(risk_score, 4),
        data_confidence=round(data_confidence, 4),
        requires_reason=requires_reason,
        factors=list(factors),
    )
