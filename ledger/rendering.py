"""Mode-specific rendering from one immutable judgment artifact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from validators import validate_message_safety, validate_roast_tone


class JudgmentLike(Protocol):
    judgment_id: str
    transaction_id: str
    label: str
    confidence: float
    rationale: str
    recommended_action: str
    normal_message: str
    roast_message: str
    fallback_used: bool
    model: str
    policy_version: str


@dataclass(frozen=True)
class RenderedJudgment:
    judgment_id: str
    transaction_id: str
    mode: str
    label: str
    confidence: float
    rationale: str
    recommended_action: str
    message: str
    fallback_used: bool
    model: str
    policy_version: str

    def to_dict(self) -> dict:
        return {
            "judgment_id": self.judgment_id,
            "transaction_id": self.transaction_id,
            "mode": self.mode,
            "label": self.label,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "recommended_action": self.recommended_action,
            "message": self.message,
            "fallback_used": self.fallback_used,
            "model": self.model,
            "policy_version": self.policy_version,
        }


def render_judgment(judgment: JudgmentLike, *, roast_enabled: bool) -> RenderedJudgment:
    mode = "roast" if roast_enabled else "normal"
    message = judgment.roast_message if roast_enabled else judgment.normal_message
    if roast_enabled:
        valid, reason = validate_roast_tone(message, label=judgment.label)
    else:
        valid, reason = validate_normal_tone(message)
    if not valid:
        message = _safe_fallback_message(judgment, roast_enabled=roast_enabled)
    return RenderedJudgment(
        judgment_id=judgment.judgment_id,
        transaction_id=judgment.transaction_id,
        mode=mode,
        label=judgment.label,
        confidence=judgment.confidence,
        rationale=judgment.rationale,
        recommended_action=judgment.recommended_action,
        message=message,
        fallback_used=judgment.fallback_used,
        model=judgment.model,
        policy_version=judgment.policy_version,
    )


def _safe_fallback_message(
    judgment: JudgmentLike, *, roast_enabled: bool
) -> str:
    if not roast_enabled:
        return f"{judgment.rationale} {judgment.recommended_action}"
    return grandma_mode_fallback(
        label=judgment.label,
        rationale=judgment.rationale,
        recommended_action=judgment.recommended_action,
    )


def grandma_mode_fallback(*, label: str, rationale: str, recommended_action: str) -> str:
    if label == "justified":
        return f"그래, 이건 필요한 데 제대로 썼다. 지갑 닫을 일은 아니니 {recommended_action}"
    if label == "insufficient_context":
        return f"아이구, 장부에 이유가 비었잖아. {recommended_action}"
    if label == "overspending":
        return f"아이고 이 화상아, 장부 바닥이 보이는데 또 퍼 쓰면 어쩌자는 거냐. {rationale} {recommended_action}"
    return f"쯧쯧, 냄비 넘치기 전에 불부터 줄여라. {rationale} {recommended_action}"


def validate_normal_tone(message: str) -> tuple[bool, str]:
    valid, reason = validate_message_safety(message)
    if not valid:
        return valid, reason
    forbidden = ("바보",)
    for phrase in forbidden:
        if phrase in message:
            return False, f"unsafe tone: {phrase}"
    return True, ""
