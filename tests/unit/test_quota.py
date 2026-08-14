from __future__ import annotations

import unittest

from ledger.quota import (
    JudgmentQuotaConfig,
    QuotaExceededError,
    RedisJudgmentQuotaLimiter,
)


class FakePipeline:
    def __init__(self, redis: "FakeRedis") -> None:
        self.redis = redis
        self.operations: list[tuple[str, str]] = []

    def __enter__(self) -> "FakePipeline":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def incr(self, key: str) -> "FakePipeline":
        self.operations.append(("incr", key))
        return self

    def ttl(self, key: str) -> "FakePipeline":
        self.operations.append(("ttl", key))
        return self

    def execute(self) -> list[int]:
        results: list[int] = []
        for operation, key in self.operations:
            if operation == "incr":
                self.redis.values[key] = self.redis.values.get(key, 0) + 1
                results.append(self.redis.values[key])
            else:
                results.append(self.redis.expirations.get(key, -1))
        return results


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    def pipeline(self, **_kwargs: object) -> FakePipeline:
        return FakePipeline(self)

    def expire(self, key: str, ttl: int) -> bool:
        self.expirations[key] = ttl
        return True


class RedisQuotaTests(unittest.TestCase):
    def test_quota_does_not_shorten_the_ledger_registry_retention(self) -> None:
        redis = FakeRedis()
        registry_key = "ledger:usr_test:keys"
        redis.expirations[registry_key] = 86400
        limiter = RedisJudgmentQuotaLimiter(
            redis,
            JudgmentQuotaConfig(daily_limit=2, rate_limit=2),
        )

        limiter.check_and_increment("usr_test")

        self.assertEqual(redis.expirations[registry_key], 86400)
        self.assertEqual(redis.expirations["ledger:usr_test:quota:daily"], 86400)
        self.assertEqual(redis.expirations["ledger:usr_test:quota:rate"], 60)

    def test_exceeding_either_window_raises_without_exposing_keys(self) -> None:
        redis = FakeRedis()
        limiter = RedisJudgmentQuotaLimiter(
            redis,
            JudgmentQuotaConfig(daily_limit=1, rate_limit=1),
        )
        limiter.check_and_increment("usr_test")

        with self.assertRaises(QuotaExceededError) as caught:
            limiter.check_and_increment("usr_test")

        self.assertNotIn("usr_test", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
