from __future__ import annotations

import os
import secrets
from urllib.parse import urlsplit
from uuid import uuid4

from flask import jsonify, request

from ledger.factory import create_app
from tasks import process_kakao_message


app = create_app()


def _queue():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url or os.getenv("LEDGER_STORE", "memory") != "redis":
        return None
    from redis import Redis
    from rq import Queue

    return Queue("kakao", connection=Redis.from_url(redis_url))


@app.post("/question")
def question():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "invalid Kakao payload"}), 400
    user_request = body.get("userRequest")
    if not isinstance(user_request, dict):
        return jsonify({"error": "missing userRequest"}), 400
    user = user_request.get("user")
    if not isinstance(user, dict) or not user.get("id"):
        return jsonify({"error": "missing Kakao user"}), 400
    callback_url = user_request.get("callbackUrl")
    if not isinstance(callback_url, str) or not callback_url.startswith("https://"):
        return jsonify({"error": "valid Kakao callbackUrl is required"}), 400
    transport_error = _verify_kakao_transport(callback_url)
    if transport_error:
        return transport_error
    utterance = user_request.get("utterance")
    if not isinstance(utterance, str) or not utterance.strip():
        return jsonify({"error": "utterance is required"}), 400
    platform_request_id = user_request.get("requestId") or request.headers.get(
        "X-Kakao-Request-Id"
    )
    if os.getenv("APP_ENV", "development") == "production" and not platform_request_id:
        return jsonify({"error": "verified Kakao request id is required"}), 400
    request_id = str(platform_request_id or uuid4())
    args = (
        str(user["id"]),
        utterance.strip(),
        callback_url,
        None,
        f"kakao:{request_id}",
    )
    queue = _queue()
    if queue is None or app.config.get("TESTING"):
        process_kakao_message(*args)
    else:
        queue.enqueue(process_kakao_message, *args, job_id=request_id)
    return jsonify({"version": "2.0", "useCallback": True})


def _verify_kakao_transport(callback_url: str):
    if os.getenv("APP_ENV", "development") != "production":
        return None
    expected_secret = os.getenv("KAKAO_WEBHOOK_SECRET")
    allowed_hosts = {
        host.strip().lower()
        for host in os.getenv("KAKAO_CALLBACK_HOSTS", "").split(",")
        if host.strip()
    }
    if not expected_secret or not allowed_hosts:
        return jsonify({"error": "Kakao transport is not configured"}), 503
    received_secret = request.headers.get("X-Kakao-Webhook-Secret", "")
    if not secrets.compare_digest(received_secret, expected_secret):
        return jsonify({"error": "unauthorized Kakao request"}), 401
    callback_host = (urlsplit(callback_url).hostname or "").lower()
    if callback_host not in allowed_hosts:
        return jsonify({"error": "callback host is not allowed"}), 400
    return None
