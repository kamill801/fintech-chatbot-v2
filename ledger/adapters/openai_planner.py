"""Privacy-bounded qualitative spending-plan advisor."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable

from ledger.adapters.openai_judge import _extract_response_text
from ledger.language import validate_korean_user_text, validate_no_financial_numbers


NARRATIVE_FIELDS = {
    "headline",
    "explanation",
    "segment_focuses",
    "next_action",
    "assumptions",
    "confidence",
}
PLAN_NARRATIVE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(NARRATIVE_FIELDS),
    "properties": {
        "headline": {"type": "string", "minLength": 1},
        "explanation": {"type": "string", "minLength": 1},
        "segment_focuses": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["allocation_id", "focus"],
                "properties": {
                    "allocation_id": {"type": "string", "minLength": 1},
                    "focus": {"type": "string", "minLength": 1},
                },
            },
        },
        "next_action": {"type": "string", "minLength": 1},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
    },
}


@dataclass(frozen=True)
class PlanNarrative:
    headline: str
    explanation: str
    segment_focuses: list[dict[str, str]]
    next_action: str
    assumptions: list[str]
    confidence: str
    fallback_used: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanAdviceRequest:
    period_start: str
    period_end: str
    confirmed_budget_krw: int
    deterministic_progress: dict[str, Any]
    allocations: list[dict[str, Any]]
    planned_expenses: list[dict[str, Any]]
    priorities: list[str]
    spending_rules: list[str]
    aggregate_patterns: dict[str, Any]

    def allowlisted_payload(self) -> dict[str, Any]:
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "confirmed_budget_krw": self.confirmed_budget_krw,
            "deterministic_progress": self.deterministic_progress,
            "allocations": self.allocations,
            "planned_expenses": self.planned_expenses,
            "priorities": self.priorities,
            "spending_rules": self.spending_rules,
            "aggregate_patterns": self.aggregate_patterns,
        }


def deterministic_plan_narrative(request: PlanAdviceRequest) -> PlanNarrative:
    shortfall = int(request.deterministic_progress.get("shortfall_krw", 0))
    current_segment = request.deterministic_progress.get("current_segment_id")
    period_status = str(request.deterministic_progress.get("period_status") or "")
    current_allocation = next(
        (
            item
            for item in request.allocations
            if item.get("allocation_id") == current_segment
        ),
        None,
    )
    current_segment_shortfall = (
        isinstance(current_allocation, dict)
        and int(current_allocation.get("flexible_remaining_krw", 0)) < 0
    )
    priority_text = " ".join(request.priorities)
    rules_text = " ".join(request.spending_rules)
    delivery_priority = "배달" in priority_text or "배달" in rules_text
    social_priority = any(keyword in priority_text for keyword in ("친구", "식사", "약속", "만남"))
    category_reflections = request.aggregate_patterns.get("category_reflection_counts", {})
    food_reflections = category_reflections.get("food", {}) if isinstance(category_reflections, dict) else {}
    regretted_food = int(food_reflections.get("regretted", 0)) if isinstance(food_reflections, dict) else 0
    well_spent_food = int(food_reflections.get("well_spent", 0)) if isinstance(food_reflections, dict) else 0
    if shortfall > 0:
        headline = "지금 계획을 한 번 조정할 때예요."
        explanation = "입력된 지출과 남은 예약을 함께 보면 자유롭게 쓸 생활비가 부족해요."
        next_action = "예정 지출 하나의 시기나 우선순위를 다시 확인하세요."
        confidence = "high"
    elif period_status == "completed":
        headline = "이번 계획은 정리해도 좋아요."
        explanation = "마무리된 기간의 입력 내역을 기준으로 생활비 흐름을 정리했어요."
        next_action = "다음 계획에는 지키고 싶은 소비와 줄일 소비를 나눠 적어 두세요."
        confidence = "medium"
    elif period_status == "upcoming":
        headline = "다가오는 계획을 준비할 때예요."
        explanation = "아직 시작 전이라 예정된 지출과 우선순위를 먼저 맞춰 봤어요."
        next_action = "시작 전에 꼭 남겨야 할 예정 지출부터 생활비 안에 확보하세요."
        confidence = "medium"
    elif current_segment:
        if current_segment_shortfall:
            headline = "이번 구간의 소비 속도를 조정해요."
            explanation = "전체 계획과 별도로 현재 구간의 사용 흐름을 다시 확인했어요."
        else:
            headline = "현재 구간은 계획 안에서 움직이고 있어요."
            explanation = "입력된 거래와 아직 남은 예약을 분리해 생활비 흐름을 확인했어요."
        if delivery_priority and social_priority:
            next_action = "약속처럼 남기고 싶은 소비는 지키고, 배달처럼 줄이기로 한 소비부터 한 번 미루세요."
        elif delivery_priority:
            next_action = "다음 식비 지출 전에 배달 대신 이미 정한 대안을 먼저 확인하세요."
        elif regretted_food > well_spent_food:
            next_action = "좋았던 식비는 남기고, 후회한 식비부터 한 번 줄여 보세요."
        elif current_segment_shortfall:
            next_action = "다음 구간으로 넘어가기 전 예정 지출과 우선순위를 먼저 다시 확인하세요."
        else:
            next_action = "다음 지출 전에 현재 구간의 남은 생활비를 확인하세요."
        confidence = "medium"
    else:
        headline = "계획 기간과 입력 시점을 확인해 주세요."
        explanation = "현재 날짜가 계획 구간 밖이라 이번 주 판단은 보수적으로 두었어요."
        next_action = "계획 기간이 맞는지 먼저 확인하세요."
        confidence = "low"
    return PlanNarrative(
        headline=headline,
        explanation=explanation,
        segment_focuses=[
            {"allocation_id": item["allocation_id"], "focus": "우선순위와 예약을 먼저 확인하세요."}
            for item in request.allocations
        ],
        next_action=next_action,
        assumptions=["사용자가 직접 입력한 거래가 최신 상태라고 가정했어요."],
        confidence=confidence,
        fallback_used=True,
    )


def parse_plan_narrative(payload: dict[str, Any], allocation_ids: set[str]) -> PlanNarrative:
    if set(payload) != NARRATIVE_FIELDS:
        raise ValueError("invalid narrative fields")
    strings = [payload.get("headline"), payload.get("explanation"), payload.get("next_action")]
    assumptions = payload.get("assumptions")
    focuses = payload.get("segment_focuses")
    cleaned_strings = [
        validate_korean_user_text(item, field_name=field_name)
        for item, field_name in zip(strings, ("headline", "explanation", "next_action"), strict=True)
    ]
    if not isinstance(assumptions, list) or not all(isinstance(item, str) for item in assumptions):
        raise ValueError("invalid assumptions")
    cleaned_assumptions = [
        validate_korean_user_text(item, field_name="assumption")
        for item in assumptions
        if item.strip()
    ]
    if not isinstance(focuses, list):
        raise ValueError("invalid segment focuses")
    cleaned_focuses: list[dict[str, str]] = []
    for item in focuses:
        if not isinstance(item, dict) or set(item) != {"allocation_id", "focus"}:
            raise ValueError("invalid segment focus")
        if item["allocation_id"] not in allocation_ids or not isinstance(item["focus"], str):
            raise ValueError("unknown allocation focus")
        cleaned_focuses.append(
            {
                "allocation_id": item["allocation_id"],
                "focus": validate_korean_user_text(item["focus"], field_name="segment_focus"),
            }
        )
    all_text = [*cleaned_strings, *cleaned_assumptions, *(item["focus"] for item in cleaned_focuses)]
    for item in all_text:
        validate_no_financial_numbers(item, field_name="narrative")
    confidence = payload.get("confidence")
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("invalid confidence")
    return PlanNarrative(
        headline=cleaned_strings[0],
        explanation=cleaned_strings[1],
        segment_focuses=cleaned_focuses,
        next_action=cleaned_strings[2],
        assumptions=cleaned_assumptions,
        confidence=confidence,
        fallback_used=False,
    )


class OpenAIResponsesPlanAdvisor:
    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_seconds: float = 20.0,
        max_attempts: int = 2,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.model = model or os.getenv("OPENAI_LEDGER_PLAN_MODEL") or os.getenv("OPENAI_LEDGER_MODEL", "gpt-4o")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = min(2, max(1, max_attempts))
        self._uses_default_client = client_factory is None
        self._client_factory = client_factory or self._default_client
        self._client: Any | None = None

    @staticmethod
    def _default_client() -> Any:
        from openai import OpenAI

        return OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=20.0, max_retries=0)

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def advise(self, request: PlanAdviceRequest) -> PlanNarrative:
        if self._uses_default_client and not os.getenv("OPENAI_API_KEY"):
            return deterministic_plan_narrative(request)
        for _attempt in range(self.max_attempts):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    store=False,
                    input=[
                        {
                            "role": "system",
                            "content": (
                                "You are a Korean spending-plan coach. Use only the supplied aggregate facts. "
                                "Return qualitative guidance in strict JSON. Every user-visible prose field "
                                "must be Korean only; short technical terms such as AI are allowed only when "
                                "necessary. Never calculate, restate, infer, "
                                "round, or compare numeric values. Do not ask for or invent merchants, memos, "
                                "reasons, notes, accounts, identities, or transactions."
                            ),
                        },
                        {"role": "user", "content": json.dumps(request.allowlisted_payload(), ensure_ascii=False)},
                    ],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "ledger_plan_narrative_v1",
                            "schema": PLAN_NARRATIVE_SCHEMA,
                            "strict": True,
                        }
                    },
                    max_output_tokens=500,
                    timeout=self.timeout_seconds,
                )
                return parse_plan_narrative(
                    json.loads(_extract_response_text(response)),
                    {item["allocation_id"] for item in request.allocations},
                )
            except Exception:
                continue
        return deterministic_plan_narrative(request)
