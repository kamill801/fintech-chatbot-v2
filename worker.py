from __future__ import annotations

import os

from redis import Redis
from rq import Queue, Worker


def main() -> None:
    if os.getenv("LEDGER_STORE", "memory") != "redis":
        raise RuntimeError("Kakao RQ worker requires LEDGER_STORE=redis")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    connection = Redis.from_url(redis_url)
    worker = Worker([Queue("kakao", connection=connection)], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
