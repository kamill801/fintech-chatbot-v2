"""Privacy-bounded qualitative spending-plan advisor."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable

from ledger.adapters.openai_judge import _extract_response_text


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
    if shortfall > 0:
        headline = "지금 계획을 한 번 조정할 때예요."
        explanation = "입력된 지출과 남은 예약을 함께 보면 자유롭게 쓸 생활비가 부족해요."
        next_action = "예정 지출 하나의 시기나 우선순위를 다시 확인하세요."
        confidence = "high"
    elif current_segment:
        headline = "현재 구간은 계획 안에서 움직이고 있어요."
        explanation = "입력된 거래와 아직 남은 예약을 분리해 생활비 흐름을 확인했어요."
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
    if not all(isinstance(item, str) and item.strip() for item in strings):
        raise ValueError("invalid narrative text")
    if not isinstance(assumptions, list) or not all(isinstance(item, str) for item in assumptions):
        raise ValueError("invalid assumptions")
    if not isinstance(focuses, list):
        raise ValueError("invalid segment focuses")
    cleaned_focuses: list[dict[str, str]] = []
    for item in focuses:
        if not isinstance(item, dict) or set(item) != {"allocation_id", "focus"}:
            raise ValueError("invalid segment focus")
        if item["allocation_id"] not in allocation_ids or not isinstance(item["focus"], str):
            raise ValueError("unknown allocation focus")
        cleaned_focuses.append({"allocation_id": item["allocation_id"], "focus": item["focus"].strip()})
    all_text = [*strings, *assumptions, *(item["focus"] for item in cleaned_focuses)]
    if any(re.search(r"\d|[₩원]", item or "") for item in all_text):
        raise ValueError("narrative must not calculate or restate numeric values")
    confidence = payload.get("confidence")
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("invalid confidence")
    return PlanNarrative(
        headline=str(strings[0]).strip(),
        explanation=str(strings[1]).strip(),
        segment_focuses=cleaned_focuses,
        next_action=str(strings[2]).strip(),
        assumptions=[item.strip() for item in assumptions if item.strip()],
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
                                "Return qualitative guidance in strict JSON. Never calculate, restate, infer, "
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
