from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask
from dotenv import load_dotenv

from ledger.auth import create_production_verifier, parse_cors_origins
from ledger.adapters.memory import InMemoryLedgerRepository
from ledger.adapters.openai_judge import OpenAIResponsesJudge
from ledger.adapters.openai_planner import OpenAIResponsesPlanAdvisor
from ledger.adapters.redis_store import RedisLedgerRepository
from ledger.adapters.synthetic import DisabledProductionAccountAdapter
from ledger.api import create_api_blueprint
from ledger.application.service import LedgerService
from ledger.privacy import PrivacyConfig, PrivacyError, PrivacyService
from ledger.quota import JudgmentQuotaConfig, RedisJudgmentQuotaLimiter
from ledger.web import create_web_blueprint
from sheets_logger import save_telemetry_event


def create_ledger_runtime(config: dict[str, Any] | None = None) -> tuple[
    LedgerService, PrivacyService, Any, Any
]:
    load_dotenv()
    values = dict(os.environ)
    if config:
        values.update({key: str(value) for key, value in config.items()})
    app_env = values.get("APP_ENV", "development")
    store_kind = values.get(
        "LEDGER_STORE", "redis" if app_env == "production" else "memory"
    )
    privacy = PrivacyService(PrivacyConfig.from_env(values))

    if app_env == "production" and store_kind != "redis":
        raise PrivacyError("production requires LEDGER_STORE=redis")
    if store_kind == "memory":
        repository = InMemoryLedgerRepository(privacy)
        ready_check = lambda: True
        judgment_quota = None
    elif store_kind == "redis":
        redis_url = values.get("REDIS_URL")
        if not redis_url:
            raise PrivacyError("REDIS_URL is required for Redis storage")
        if app_env == "production" and not redis_url.startswith("rediss://"):
            raise PrivacyError("production REDIS_URL must use rediss:// TLS")
        repository = RedisLedgerRepository.from_url(redis_url, privacy)
        ready_check = lambda: bool(repository._redis.ping())
        judgment_quota = (
            RedisJudgmentQuotaLimiter(
                repository._redis, JudgmentQuotaConfig.from_env(values)
            )
            if app_env == "production"
            else None
        )
    else:
        raise PrivacyError("LEDGER_STORE must be memory or redis")

    telemetry_sink = save_telemetry_event if values.get("GOOGLE_SHEET_ID") else None
    service = LedgerService(
        repository,
        OpenAIResponsesJudge(model=values.get("OPENAI_LEDGER_MODEL")),
        DisabledProductionAccountAdapter(),
        telemetry_sink=telemetry_sink,
        judgment_quota=judgment_quota,
        plan_advisor=OpenAIResponsesPlanAdvisor(
            model=values.get("OPENAI_LEDGER_PLAN_MODEL") or values.get("OPENAI_LEDGER_MODEL")
        ),
    )
    return service, privacy, repository, ready_check


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    if config:
        app.config.update(config)
    service, privacy, repository, ready_check = create_ledger_runtime(config)
    app_env = str((config or {}).get("APP_ENV", os.getenv("APP_ENV", "development")))
    allow_dev_auth = str(
        (config or {}).get("ALLOW_DEV_AUTH", os.getenv("ALLOW_DEV_AUTH", "0"))
    ) == "1"
    values = dict(os.environ)
    if config:
        values.update(
            {key: str(value) for key, value in config.items() if isinstance(value, (str, int, float, bool))}
        )
    production = app_env == "production"
    cors_allowed_origins = parse_cors_origins(
        values.get("CORS_ALLOWED_ORIGINS", ""),
        production=production,
    )
    configured_verifier = (config or {}).get("AUTH_VERIFIER")
    if configured_verifier is not None:
        auth_verifier = configured_verifier
    elif production:
        auth_verifier = create_production_verifier(values).verify_subject
    else:
        auth_verifier = None
    app.extensions["ledger_service"] = service
    app.extensions["ledger_privacy"] = privacy
    app.extensions["ledger_repository"] = repository
    app.extensions["ledger_ready_check"] = ready_check
    app.register_blueprint(
        create_api_blueprint(
            service,
            privacy,
            app_env=app_env,
            allow_dev_auth=allow_dev_auth,
            auth_verifier=auth_verifier,
            cors_allowed_origins=cors_allowed_origins,
        )
    )
    build_dir = Path(
        str(
            (config or {}).get(
                "FRONTEND_DIST",
                Path(__file__).resolve().parents[1] / "frontend" / "dist",
            )
        )
    )
    app.register_blueprint(create_web_blueprint(build_dir))
    return app
