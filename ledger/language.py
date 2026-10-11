from __future__ import annotations

import re


_HANGUL_RE = re.compile(r"[가-힣]")
_ASCII_WORD_RE = re.compile(r"\b[A-Za-z]+\b")
_DIGIT_OR_CURRENCY_RE = re.compile(r"\d|₩")
_KOREAN_AMOUNT_RE = re.compile(
    r"(?:[일이삼사오육칠팔구십백천만억조]+|한|두|세|네|다섯|여섯|일곱|여덟|아홉|열)\s*원"
)
_ALLOWED_SHORT_TERMS = {"AI", "API", "JSON"}


def has_korean_text(value: str) -> bool:
    return bool(_HANGUL_RE.search(value))


def has_english_sentence(value: str) -> bool:
    words = [word.upper() for word in _ASCII_WORD_RE.findall(value)]
    return any(word not in _ALLOWED_SHORT_TERMS for word in words)


def is_korean_user_text(value: str) -> bool:
    return has_korean_text(value) and not has_english_sentence(value)


def has_financial_number_text(value: str) -> bool:
    return bool(_DIGIT_OR_CURRENCY_RE.search(value) or _KOREAN_AMOUNT_RE.search(value))


def validate_korean_user_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid {field_name}")
    cleaned = value.strip()
    if not is_korean_user_text(cleaned):
        raise ValueError(f"{field_name} must be Korean")
    return cleaned


def validate_no_financial_numbers(value: str, *, field_name: str) -> None:
    if has_financial_number_text(value):
        raise ValueError(f"{field_name} must not calculate or restate numeric values")
