import random
import re

FORBIDDEN_PHRASES = [
    "제가 도와드릴게요", "도와드리겠습니다",
    "요약하자면", "결론적으로",
    "AI로서", "인공지능으로서",
    "안녕하세요",
    "도움이 필요하시면",
]

_FALLBACK_REPLIES = [
    "옘병, 말이 길어졌다. 다시 말해봐라, 얼마 썼고 왜 썼냐?",
    "쯧쯧, 할미 머리가 복잡해졌다. 짧게 다시 말해봐라.",
    "에이구, 할미가 잠깐 헷갈렸다. 뭘 얼마 썼냐고.",
]


def get_fallback() -> str:
    return random.choice(_FALLBACK_REPLIES)


def count_sentences(text: str) -> int:
    parts = re.split(r'[.?!]+', text)
    return sum(1 for p in parts if p.strip())


def validate_reply(text: str) -> tuple[bool, str]:
    if count_sentences(text) > 3:
        return False, "3문장 초과"
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            return False, f"금지어 포함: {phrase}"
    if text.count("?") > 1:
        return False, "질문 2개 이상"
    return True, ""


def build_rewrite_prompt(original: str, reason: str) -> str:
    return (
        f"직전 응답이 다음 기준을 어겼다: {reason}\n\n"
        f"원래 답변: {original}\n\n"
        "같은 의도로 더 짧게(1~3문장), 욕쟁이 할미 톤으로, 금지어 없이 다시 답해라."
    )


SENSITIVE_PATTERNS = [
    re.compile(r"\b\d{2,6}[- ]?\d{2,6}[- ]?\d{2,8}\b"),
    re.compile(r"\b\d{6}-\d{7}\b"),
]

ROAST_FORBIDDEN_PHRASES = [
    "죽어",
    "자살",
    "꺼져",
    "거지",
    "파산해라",
    "빚쟁이",
    "장애",
    "병신",
    "협박",
]

UNSAFE_TONE_PATTERNS = [
    re.compile(r"죽\s*(?:어|는|인다|여|을|음|이)"),
    re.compile(r"(?:뒤지|디지)"),
    re.compile(r"목숨|해치|가만\s*안\s*둬"),
]

RENDER_FORBIDDEN_FINANCIAL_FIELDS = [
    "monthly_income_krw",
    "liquid_assets_krw",
    "fixed_expenses_krw",
    "monthly_debt_payment_krw",
    "account_number",
    "provider_token",
    "source_reference",
]


def sanitize_free_text(text: str, *, max_length: int = 240) -> str:
    sanitized = " ".join(str(text).split())
    for pattern in SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    return sanitized[:max_length]


def validate_roast_tone(message: str, *, label: str | None = None) -> tuple[bool, str]:
    valid, reason = validate_message_safety(message)
    if not valid:
        return valid, reason
    if label == "justified":
        acknowledgement_markers = ("필요", "정당", "괜찮", "인정")
        if not any(marker in message for marker in acknowledgement_markers):
            return False, "justified roast must acknowledge the purchase"
    return True, ""


def validate_message_safety(message: str) -> tuple[bool, str]:
    if not isinstance(message, str) or not message.strip():
        return False, "empty message"
    for phrase in ROAST_FORBIDDEN_PHRASES:
        if phrase in message:
            return False, f"unsafe tone phrase: {phrase}"
    for pattern in UNSAFE_TONE_PATTERNS:
        if pattern.search(message):
            return False, "unsafe threat pattern"
    for field in RENDER_FORBIDDEN_FINANCIAL_FIELDS:
        if field in message:
            return False, f"sensitive field leaked: {field}"
    return True, ""


def validate_judgment_parity(normal_render: dict, roast_render: dict) -> tuple[bool, str]:
    for field in ("judgment_id", "transaction_id", "label", "confidence", "recommended_action", "policy_version"):
        if normal_render.get(field) != roast_render.get(field):
            return False, f"parity mismatch: {field}"
    return True, ""
