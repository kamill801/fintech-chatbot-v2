import re
import random

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
