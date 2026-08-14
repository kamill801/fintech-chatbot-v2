from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


class QuotaExceededError(RuntimeError):
    pass


class QuotaUnavailableError(RuntimeError):
    pass


class JudgmentQuotaLimiter(Protocol):
    def check_and_increment(self, user_ref: str) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class JudgmentQuotaConfig:
    daily_limit: int = 50
    daily_window_seconds: int = 86400
    rate_limit: int = 10
    rate_window_seconds: int = 60

    @classmethod
    def from_env(cls, values: dict[str, str] | None = None) -> JudgmentQuotaConfig:
        source = values or os.environ
        return cls(
            daily_limit=_positive_int(source.get("AI_JUDGMENT_DAILY_QUOTA"), 50),
            daily_window_seconds=_positive_int(
                source.get("AI_JUDGMENT_DAILY_WINDOW_SECONDS"), 86400
            ),
            rate_limit=_positive_int(source.get("AI_JUDGMENT_RATE_LIMIT"), 10),
            rate_window_seconds=_positive_int(
                source.get("AI_JUDGMENT_RATE_WINDOW_SECONDS"), 60
            ),
        )


class RedisJudgmentQuotaLimiter:
    def __init__(
        self, redis_client: Any, config: JudgmentQuotaConfig, *, key_prefix: str = "ledger"
    ) -> None:
        self._redis = redis_client
        self._config = config
        self._key_prefix = key_prefix

    def check_and_increment(self, user_ref: str) -> None:
        windows = (
            (
                self._key(user_ref, "quota:daily"),
                self._config.daily_limit,
                self._config.daily_window_seconds,
            ),
            (
                self._key(user_ref, "quota:rate"),
                self._config.rate_limit,
                self._config.rate_window_seconds,
            ),
        )
        try:
            counts: list[int] = []
            with self._redis.pipeline(transaction=True) as pipe:
                for key, _limit, ttl in windows:
                    pipe.incr(key)
                    pipe.ttl(key)
                raw = pipe.execute()
            for index in range(0, len(raw), 2):
                counts.append(int(raw[index]))
                if int(raw[index + 1]) < 0:
                    self._redis.expire(windows[index // 2][0], windows[index // 2][2])
        except Exception as exc:
            raise QuotaUnavailableError("AI judgment quota is temporarily unavailable") from exc

        if any(count > limit for count, (_key, limit, _ttl) in zip(counts, windows)):
            raise QuotaExceededError("AI judgment quota exceeded")

    def _key(self, user_ref: str, suffix: str) -> str:
        return f"{self._key_prefix}:{user_ref}:{suffix}"


def _positive_int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("quota values must be positive integers")
    return parsed
