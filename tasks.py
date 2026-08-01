from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any
from uuid import uuid4

import requests

from ledger.application.service import LedgerService, ServiceError
from ledger.factory import create_ledger_runtime
from ledger.privacy import PrivacyService


_AMOUNT_RE = re.compile(r"(?P<amount>\d[\d,]*)\s*원")
_CATEGORY_KEYWORDS = {
    "배달": "food_delivery",
    "커피": "cafe",
    "카페": "cafe",
    "택시": "transport",
    "교통": "transport",
    "장보기": "groceries",
    "마트": "groceries",
    "병원": "healthcare",
    "약": "healthcare",
    "쇼핑": "shopping",
    "옷": "shopping",
    "술": "alcohol",
}


@lru_cache(maxsize=1)
def _runtime() -> tuple[LedgerService, PrivacyService, Any]:
    service, privacy, repository, _ready = create_ledger_runtime()
    return service, privacy, repository


def process_kakao_message(
    user_id: str,
    user_message: str,
    callback_url: str,
    image_url: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    service, privacy, repository = _runtime()
    user_ref = privacy.user_ref(user_id)
    key = idempotency_key or f"kakao:{uuid4()}"
    correlation_id = str(uuid4())
    try:
        _import_legacy_metadata(
            service, repository, user_id, user_ref, correlation_id=correlation_id
        )
        reply = _route_message(
            service,
            user_ref,
            user_message.strip(),
            idempotency_key=key,
            correlation_id=correlation_id,
        )
    except ServiceError as exc:
        if exc.code == "profile_required":
            reply = "먼저 자산, 월수입, 고정비, 자유 예산과 목표를 등록해야 지출을 판단할 수 있어."
        else:
            reply = f"요청을 처리하지 못했어. ({exc.code})"
    except Exception:
        reply = "지금 장부 처리가 잠시 막혔어. 같은 내용을 잠시 뒤 다시 보내줘."
    send_to_kakao(callback_url, reply)
    return reply


def _route_message(
    service: LedgerService,
    user_ref: str,
    message: str,
    *,
    idempotency_key: str,
    correlation_id: str,
) -> str:
    compact = message.replace(" ", "")
    if compact in {"로스트켜", "roast켜", "로스트온"}:
        service.update_settings(
            user_ref,
            {"roast_enabled": True},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source="kakao",
        )
        return "로스트 모드 켰다. 판단은 그대로 하고 말투만 더 세게 간다."
    if compact in {"로스트꺼", "roast꺼", "로스트오프"}:
        service.update_settings(
            user_ref,
            {"roast_enabled": False},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source="kakao",
        )
        return "로스트 모드 껐다. 이제 일반 코칭 말투로 답할게."
    if "월간리포트" in compact or "이번달요약" in compact:
        summary = service.get_summary(user_ref).data["summary"]
        total = summary["total_spent_krw"]
        count = summary["transaction_count"]
        usage = summary.get("budget_usage")
        usage_text = f", 자유 예산의 {usage * 100:.0f}%" if usage is not None else ""
        return f"이번 달 기록은 {count}건, 총 {total:,}원{usage_text}이야."

    pending = service.repository.get_pending_question(user_ref)
    if pending and pending.answered_at is None:
        result = service.add_reason(
            user_ref,
            pending.transaction_id,
            {"reason": message},
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source="kakao",
        )
        return result.data["judgment"]["message"]

    transaction_payload = _parse_transaction(message)
    if transaction_payload:
        result = service.create_transaction(
            user_ref,
            transaction_payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            source="kakao",
        )
        if result.status == 202:
            roast = service.repository.get_settings(user_ref).roast_enabled
            if roast:
                return "쯧, 이거 왜 샀냐? 꼭 필요했던 이유만 말해봐라."
            return result.data["pending_question"]["question"]
        return result.data["judgment"]["message"]
    return "지출은 '커피 5,800원'처럼 금액과 함께 적어줘. 월간 리포트나 로스트 켜/꺼도 가능해."


def _parse_transaction(message: str) -> dict[str, Any] | None:
    match = _AMOUNT_RE.search(message)
    if not match:
        return None
    amount = int(match.group("amount").replace(",", ""))
    category = next(
        (value for keyword, value in _CATEGORY_KEYWORDS.items() if keyword in message),
        "unknown",
    )
    return {
        "amount_krw": amount,
        "category": category,
        "description": message,
    }


def _import_legacy_metadata(
    service: LedgerService,
    repository: Any,
    raw_user_id: str,
    user_ref: str,
    *,
    correlation_id: str,
) -> None:
    redis_client = getattr(repository, "_redis", None)
    if redis_client is None:
        return
    raw = redis_client.get(f"user_state:{raw_user_id}")
    if not raw:
        return
    state = json.loads(raw)
    categories = state.get("spending_categories") or {}
    emotions = state.get("emotion_tags") or []
    messages = state.get("recent_messages") or []
    service.import_legacy_metadata(
        user_ref,
        {
            "category_counts": categories,
            "emotion_labels": emotions,
            "message_count": len(messages),
        },
        idempotency_key="legacy-import-v1",
        correlation_id=correlation_id,
    )


def send_to_kakao(callback_url: str, text: str) -> None:
    response = requests.post(
        callback_url,
        json={
            "version": "2.0",
            "template": {"outputs": [{"simpleText": {"text": text}}]},
        },
        timeout=5,
    )
    response.raise_for_status()
