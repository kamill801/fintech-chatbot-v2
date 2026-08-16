"""OpenAI Responses API judge with strict schema and deterministic fallback."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from ledger.application.signals import POLICY_VERSION
from ledger.domain.models import DeterministicSignalSet, JudgmentResult
from ledger.privacy import build_prompt_payload
from ledger.rendering import grandma_mode_fallback


ALLOWED_LABELS = {"justified", "caution", "overspending", "insufficient_context"}
REQUIRED_OUTPUT_FIELDS = {
    "label",
    "confidence",
    "rationale",
    "recommended_action",
    "decision_factors",
    "normal_message",
    "roast_message",
}

JUDGMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": sorted(REQUIRED_OUTPUT_FIELDS),
    "properties": {
        "label": {"type": "string", "enum": sorted(ALLOWED_LABELS)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string", "minLength": 1},
        "recommended_action": {"type": "string", "minLength": 1},
        "decision_factors": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "normal_message": {"type": "string", "minLength": 1},
        "roast_message": {"type": "string", "minLength": 1},
    },
}


@dataclass(frozen=True)
class JudgmentRequest:
    transaction_id: str
    amount_krw: int
    category: str
    signals: DeterministicSignalSet
    user_reason: str | None = None
    policy_version: str = POLICY_VERSION

    def allowlisted_payload(self) -> dict:
        return build_prompt_payload(
            amount_krw=self.amount_krw,
            category=self.category,
            signals=self.signals.to_dict(),
            user_reason=self.user_reason,
            policy_version=self.policy_version,
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_openai_client_factory() -> Any:
    from openai import OpenAI

    return OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=_env_float("OPENAI_TIMEOUT_SECONDS", 20.0),
        max_retries=0,
    )


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    if isinstance(response, dict):
        if isinstance(response.get("output_text"), str):
            return response["output_text"]
        output = response.get("output") or []
    else:
        output = getattr(response, "output", []) or []
    for item in output:
        content = item.get("content", []) if isinstance(item, dict) else getattr(item, "content", [])
        for part in content or []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                return part["text"]
            text = getattr(part, "text", None)
            if isinstance(text, str):
                return text
    raise ValueError("missing response text")


def parse_judgment_payload(payload: dict) -> dict:
    missing = REQUIRED_OUTPUT_FIELDS - set(payload)
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")
    extra = set(payload) - REQUIRED_OUTPUT_FIELDS
    if extra:
        raise ValueError(f"unexpected fields: {sorted(extra)}")
    if payload["label"] not in ALLOWED_LABELS:
        raise ValueError("invalid label")
    confidence = payload["confidence"]
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        raise ValueError("invalid confidence")
    factors = payload["decision_factors"]
    if not isinstance(factors, list) or not factors or not all(isinstance(item, str) for item in factors):
        raise ValueError("invalid decision_factors")
    cleaned_factors = [item.strip() for item in factors if item.strip()]
    if not cleaned_factors:
        raise ValueError("invalid decision_factors")
    for field in ("rationale", "recommended_action", "normal_message", "roast_message"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise ValueError(f"invalid {field}")
    return {
        "label": payload["label"],
        "confidence": float(confidence),
        "rationale": payload["rationale"].strip(),
        "recommended_action": payload["recommended_action"].strip(),
        "decision_factors": cleaned_factors,
        "normal_message": payload["normal_message"].strip(),
        "roast_message": payload["roast_message"].strip(),
    }


def deterministic_fallback_judgment(request: JudgmentRequest) -> JudgmentResult:
    risk = request.signals.risk_score
    confidence_cap = 0.69 if request.signals.requires_reason and not request.user_reason else 0.90
    if risk >= 0.75:
        label = "overspending"
        confidence = min(confidence_cap, max(0.76, risk))
        rationale = "예산 사용량과 목표 부담 신호가 모두 높다."
        recommended_action = "이번 주 같은 카테고리의 다음 소비를 한 번 건너뛴다."
    elif risk >= 0.35:
        label = "caution"
        confidence = min(confidence_cap, max(0.60, risk))
        rationale = "예산 또는 목표에 주는 부담이 중간 수준이다."
        recommended_action = "다음 유사 소비 전에 대체할 지출 하나를 정한다."
    else:
        label = "justified"
        confidence = min(confidence_cap, max(0.70, 1.0 - risk))
        rationale = "현재 신호만으로는 예산이나 목표에 큰 부담이 없다."
        recommended_action = "이 소비는 유지하되 같은 카테고리를 계속 기록한다."

    factors = list(request.signals.factors or ["risk_score"])
    if request.user_reason and "user_reason" not in factors:
        factors.append("user_reason")
    normal_message = f"{rationale} {recommended_action}"
    roast_message = grandma_mode_fallback(
        label=label,
        rationale=rationale,
        recommended_action=recommended_action,
    )
    return JudgmentResult(
        judgment_id=str(uuid4()),
        transaction_id=request.transaction_id,
        label=label,
        confidence=round(confidence, 4),
        rationale=rationale,
        recommended_action=recommended_action,
        decision_factors=factors,
        normal_message=normal_message,
        roast_message=roast_message,
        fallback_used=True,
        model="deterministic-fallback-v1",
        policy_version=request.policy_version,
        created_at=_utc_now(),
    )


class OpenAIResponsesJudge:
    def __init__(
        self,
        *,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        max_output_tokens: int | None = None,
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.model = model or os.getenv("OPENAI_LEDGER_MODEL", "gpt-4o")
        self.timeout_seconds = timeout_seconds or _env_float("OPENAI_TIMEOUT_SECONDS", 20.0)
        self.max_attempts = _bounded_attempts(max_retries)
        self.max_output_tokens = max_output_tokens or _env_int(
            "OPENAI_LEDGER_MAX_OUTPUT_TOKENS", 700
        )
        self._client_factory = client_factory or default_openai_client_factory
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def judge(self, request: JudgmentRequest) -> JudgmentResult:
        if self._client_factory is default_openai_client_factory and not os.getenv("OPENAI_API_KEY"):
            return deterministic_fallback_judgment(request)
        last_error: Exception | None = None
        for _attempt in range(self.max_attempts):
            try:
                payload = self._call_model(request)
                parsed = parse_judgment_payload(payload)
                return JudgmentResult(
                    judgment_id=str(uuid4()),
                    transaction_id=request.transaction_id,
                    fallback_used=False,
                    model=self.model,
                    policy_version=request.policy_version,
                    created_at=_utc_now(),
                    **parsed,
                )
            except Exception as exc:
                last_error = exc
        fallback = deterministic_fallback_judgment(request)
        if last_error is not None:
            return fallback
        return fallback

    def _call_model(self, request: JudgmentRequest) -> dict:
        response = self.client.responses.create(
            model=self.model,
            store=False,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You judge Korean household-ledger spending from allowlisted "
                        "signals only. Return strict JSON. normal_message and roast_message "
                        "must share the same label and recommendation. roast_message is the "
                        "user-facing '욕쟁이 할머니 모드': write 1-3 Korean sentences in a "
                        "sharp but caring market-grandmother ledger-inspection voice. Ground it "
                        "in supplied evidence, use one household metaphor such as 장부, 지갑, "
                        "통장, 국밥, 밥솥, or 냄비, and end with an action consistent with "
                        "recommended_action. For justified spending, grudgingly acknowledge it; "
                        "for caution, point out the exact pattern and scold; for overspending, "
                        "scold strongly without threats. Style examples only: '그래, 이건 필요한 "
                        "데 제대로 썼다. 지갑 닫을 일은 아니다.'; '아이고 이 화상아, 이번 주 "
                        "카페가 벌써 세 번째다. 다음 만남은 산책으로 돌려.'; '이 녀석아, "
                        "장부 바닥이 보이는데 또 퍼 쓰면 어쩌자는 거냐.' Never use threats, "
                        "death or self-harm language, slurs, protected-trait attacks, appearance "
                        "insults, sexual humiliation, or invented personal facts."
                        " When user_reason is absent, make a best-effort label from the supplied "
                        "signals and do not ask the user to add a reason. Reserve "
                        "insufficient_context for data_confidence below 0.35."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(request.allowlisted_payload(), ensure_ascii=False),
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "ledger_judgment_v1",
                    "schema": JUDGMENT_SCHEMA,
                    "strict": True,
                }
            },
            max_output_tokens=self.max_output_tokens,
            timeout=self.timeout_seconds,
        )
        return json.loads(_extract_response_text(response))


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    parsed = int(value)
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    return parsed


def _bounded_attempts(value: int | None) -> int:
    attempts = value
    if attempts is None:
        attempts = _env_int("OPENAI_JUDGMENT_ATTEMPTS", 2)
    if attempts < 1:
        raise ValueError("OPENAI_JUDGMENT_ATTEMPTS must be at least 1")
    return min(attempts, 2)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    parsed = float(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive")
    return parsed
