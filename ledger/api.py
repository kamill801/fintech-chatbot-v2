from __future__ import annotations

from functools import wraps
from typing import Any, Callable
from uuid import uuid4

from flask import Blueprint, Response, current_app, g, jsonify, request

from ledger.application.service import LedgerService, ServiceError, ServiceResult
from ledger.domain.models import DomainValidationError
from ledger.privacy import PrivacyService


def create_api_blueprint(
    service: LedgerService,
    privacy: PrivacyService,
    *,
    app_env: str,
    allow_dev_auth: bool,
) -> Blueprint:
    api = Blueprint("ledger_api", __name__)

    @api.before_app_request
    def assign_correlation_id() -> None:
        g.correlation_id = request.headers.get("X-Correlation-Id") or str(uuid4())

    @api.get("/health")
    def health() -> Response:
        return _success(ServiceResult(200, {"status": "ok"}))

    @api.get("/ready")
    def ready() -> Response:
        checker: Callable[[], bool] = current_app.extensions["ledger_ready_check"]
        if not checker():
            return _error("not_ready", "repository is not ready", 503)
        return _success(ServiceResult(200, {"status": "ready"}))

    def authenticated(handler: Callable[..., Response]) -> Callable[..., Response]:
        @wraps(handler)
        def wrapped(*args: Any, **kwargs: Any) -> Response:
            if app_env == "production":
                return _error(
                    "AUTH_NOT_CONFIGURED",
                    "trusted production authentication is not configured",
                    503,
                )
            if not allow_dev_auth:
                return _error("unauthorized", "development authentication is disabled", 401)
            raw_user_id = request.headers.get("X-User-Id")
            if not raw_user_id:
                return _error("unauthorized", "X-User-Id is required", 401)
            g.user_ref = privacy.user_ref(raw_user_id)
            return handler(*args, **kwargs)

        return wrapped

    @api.get("/api/v1/me/profile")
    @authenticated
    def get_profile() -> Response:
        return _success(service.get_profile(g.user_ref))

    @api.put("/api/v1/me/profile")
    @authenticated
    def put_profile() -> Response:
        return _mutating(
            lambda key: service.upsert_profile(
                g.user_ref,
                _json_body(),
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.get("/api/v1/me/settings")
    @authenticated
    def get_settings() -> Response:
        return _success(service.get_settings(g.user_ref))

    @api.put("/api/v1/me/settings")
    @authenticated
    def put_settings() -> Response:
        return _mutating(
            lambda key: service.update_settings(
                g.user_ref,
                _json_body(),
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.get("/api/v1/me/transactions")
    @authenticated
    def list_transactions() -> Response:
        return _success(service.list_transactions(g.user_ref))

    @api.post("/api/v1/me/transactions")
    @authenticated
    def create_transaction() -> Response:
        return _mutating(
            lambda key: service.create_transaction(
                g.user_ref,
                _json_body(),
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.get("/api/v1/me/transactions/<transaction_id>")
    @authenticated
    def get_transaction(transaction_id: str) -> Response:
        return _success(service.get_transaction(g.user_ref, transaction_id))

    @api.post("/api/v1/me/transactions/<transaction_id>/reason")
    @authenticated
    def add_reason(transaction_id: str) -> Response:
        return _mutating(
            lambda key: service.add_reason(
                g.user_ref,
                transaction_id,
                _json_body(),
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.post("/api/v1/me/judgments/<judgment_id>/corrections")
    @authenticated
    def correct_judgment(judgment_id: str) -> Response:
        return _mutating(
            lambda key: service.correct_judgment(
                g.user_ref,
                judgment_id,
                _json_body(),
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.post("/api/v1/me/judgments/<judgment_id>/share-view")
    @authenticated
    def share_view(judgment_id: str) -> Response:
        return _mutating(
            lambda key: service.record_share_view(
                g.user_ref,
                judgment_id,
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.post("/api/v1/me/judgments/<judgment_id>/share")
    @authenticated
    def share(judgment_id: str) -> Response:
        return _mutating(
            lambda key: service.share_judgment(
                g.user_ref,
                judgment_id,
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.get("/api/v1/me/summary")
    @authenticated
    def summary() -> Response:
        return _success(service.get_summary(g.user_ref))

    @api.get("/api/v1/me/metrics")
    @authenticated
    def metrics() -> Response:
        return _success(service.get_metrics(g.user_ref))

    @api.post("/api/v1/me/accounts/<connection_id>/revoke")
    @authenticated
    def revoke_account(connection_id: str) -> Response:
        return _mutating(
            lambda key: service.revoke_account(
                g.user_ref,
                connection_id,
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.delete("/api/v1/me/data")
    @authenticated
    def delete_data() -> Response:
        return _mutating(
            lambda key: service.delete_user_data(
                g.user_ref,
                idempotency_key=key,
                correlation_id=g.correlation_id,
            )
        )

    @api.app_errorhandler(ServiceError)
    def handle_service_error(error: ServiceError) -> Response:
        return _error(error.code, str(error), error.status)

    @api.app_errorhandler(DomainValidationError)
    def handle_domain_error(error: DomainValidationError) -> Response:
        return _error("invalid_request", str(error), 400)

    @api.app_errorhandler(ValueError)
    def handle_value_error(error: ValueError) -> Response:
        return _error("invalid_request", str(error), 400)

    return api


def _mutating(operation: Callable[[str], ServiceResult]) -> Response:
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return _error(
            "idempotency_key_required", "Idempotency-Key header is required", 400
        )
    return _success(operation(idempotency_key))


def _json_body() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ServiceError("invalid_json", "a JSON object is required", 400)
    return payload


def _success(result: ServiceResult) -> Response:
    correlation_id = getattr(g, "correlation_id", str(uuid4()))
    if result.status == 204:
        response = Response(status=204)
        response.headers["X-Correlation-Id"] = correlation_id
        return response
    return jsonify(
        {
            "data": result.data or {},
            "meta": {"correlation_id": correlation_id},
        }
    ), result.status


def _error(code: str, message: str, status: int) -> Response:
    return jsonify(
        {
            "error": {"code": code, "message": message},
            "meta": {
                "correlation_id": getattr(g, "correlation_id", str(uuid4()))
            },
        }
    ), status
