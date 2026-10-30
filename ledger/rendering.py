"""Mode-specific rendering from one immutable judgment artifact."""

from __future__ import annotations

from dataclasses import dataclass
import re
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
    display_fallback_used: bool = False
    display_fallback_reason: str | None = None

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
            "display_fallback_used": self.display_fallback_used,
            "display_fallback_reason": self.display_fallback_reason,
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
        display_fallback_used=not valid,
        display_fallback_reason=reason if not valid else None,
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
    explanation = _spoken_rationale(rationale)
    action = re.sub(r"보세요[.]?$", "보자꾸나.", recommended_action.strip())
    if label == "justified":
        return f"그래, 잘 썼다. {explanation} 다음엔 이걸 챙겨라: {action}"
    if label == "insufficient_context":
        return f"아이구, 장부만 보고 속단할 순 없지. {explanation} 다음엔 이걸 챙겨라: {action}"
    if label == "overspending":
        return f"아이고, 이 지출은 짚고 가자꾸나. {explanation} 다음엔 이 약속부터 지켜라: {action}"
    return f"쯧, 이번 지출은 한 번 살펴보자꾸나. {explanation} 다음엔 이걸 챙겨라: {action}"


def _spoken_rationale(rationale: str) -> str:
    explanation = rationale.strip()
    for written, spoken in (("것입니다", "것이구나"), ("합니다", "하구나"), ("되었습니다", "되었구나"), ("습니다", "구나"), ("입니다", "이구나"), ("이에요", "이구나")):
        explanation = re.sub(re.escape(written) + r"(?=[.!?]|$)", spoken, explanation)
    for written, spoken in (
        ("있다.", "있구나."),
        ("없다.", "없구나."),
        ("높다.", "높구나."),
        ("낮다.", "낮구나."),
        ("이다.", "이구나."),
    ):
        if explanation.endswith(written):
            return explanation[:-len(written)] + spoken
    return explanation


def validate_normal_tone(message: str) -> tuple[bool, str]:
    valid, reason = validate_message_safety(message)
    if not valid:
        return valid, reason
    forbidden = ("바보",)
    for phrase in forbidden:
        if phrase in message:
            return False, f"unsafe tone: {phrase}"
    return True, ""
