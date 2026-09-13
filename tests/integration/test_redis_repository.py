from __future__ import annotations

import os
import threading
import unittest
from uuid import uuid4

from ledger.adapters.redis_store import RedisLedgerRepository
from ledger.adapters.synthetic import DisabledProductionAccountAdapter
from ledger.application.service import LedgerService
from ledger.domain.events import (
    EVENT_JUDGMENT_COMPLETED,
    EVENT_JUDGMENT_CORRECTED,
    EVENT_JUDGMENT_REASON_REQUESTED,
)
from ledger.domain.models import DomainValidationError, PendingQuestion, utc_now_iso
from ledger.factory import create_app, create_ledger_runtime
from ledger.privacy import PrivacyConfig, PrivacyService
from tests.helpers import FERNET_KEY, USER_REF_SECRET, FallbackJudge, correlation_id, profile_payload


REDIS_TEST_URL = os.getenv("LEDGER_TEST_REDIS_URL")


@unittest.skipUnless(REDIS_TEST_URL, "set LEDGER_TEST_REDIS_URL for Redis integration tests")
class RedisRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        import redis

        self.redis = redis.Redis.from_url(REDIS_TEST_URL, decode_responses=True)
        self.redis.ping()
        self.privacy = PrivacyService(
            PrivacyConfig(
                encryption_key=FERNET_KEY,
                user_ref_secret=USER_REF_SECRET,
                app_env="test",
                retention_days=1,
            )
        )
        self.repository = RedisLedgerRepository(self.redis, self.privacy)
        self.service = LedgerService(
            self.repository,
            FallbackJudge(),
            DisabledProductionAccountAdapter(),
        )
        self.user_ref = f"usr_redis_{uuid4().hex}"

    def tearDown(self) -> None:
        for key in list(self.redis.scan_iter(match=f"ledger:{self.user_ref}:*")):
            self.redis.delete(key)

    def test_full_flow_persists_projection_events_idempotency_ttl_and_deletion(self) -> None:
        self.service.upsert_profile(
            self.user_ref,
            profile_payload(),
            idempotency_key="profile-1",
            correlation_id=correlation_id(),
        )
        self.service.update_settings(
            self.user_ref,
            {"roast_enabled": True},
            idempotency_key="settings-roast",
            correlation_id=correlation_id(),
        )
        plan = self.service.activate_spending_plan(
            self.user_ref,
            {
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "confirmed_budget_krw": 500000,
                "priorities": ["생활비 안정"],
                "planned_expenses": [],
                "confirmed": True,
            },
            idempotency_key="plan-1",
            correlation_id=correlation_id(),
        )
        replayed_plan = self.service.activate_spending_plan(
            self.user_ref,
            {
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "confirmed_budget_krw": 500000,
                "priorities": ["생활비 안정"],
                "planned_expenses": [],
                "confirmed": True,
            },
            idempotency_key="plan-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(plan.data["plan"], replayed_plan.data["plan"])
        self.assertEqual(
            self.repository.get_spending_plan(self.user_ref).confirmed_budget_krw,
            500000,
        )
        first = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 9876543, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        replay = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 9876543, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(first.status, 202)
        self.assertEqual(first.data, replay.data)
        transaction_id = first.data["transaction"]["transaction_id"]

        judged = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무 장비를 교체해야 했다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        judgment_id = judged.data["judgment"]["judgment_id"]
        index_key = self.repository._judgment_for_transaction_key(self.user_ref, transaction_id)
        self.assertEqual(self.redis.get(index_key), judgment_id)
        self.assertEqual(
            self.repository.get_judgment_for_transaction(
                self.user_ref, transaction_id
            ).judgment_id,
            judgment_id,
        )
        self.service.correct_judgment(
            self.user_ref,
            judgment_id,
            {"corrected_label": "justified", "correction_reason": "회사 환급"},
            idempotency_key="correction-1",
            correlation_id=correlation_id(),
        )

        current = self.service.get_transaction(self.user_ref, transaction_id).data
        self.assertEqual(current["transaction"]["status"], "corrected")
        self.assertEqual(current["judgment"]["effective_label"], "justified")
        self.assertEqual(current["judgment"]["correction"]["correction_reason"], "회사 환급")
        event_types = [event.event_type for event in self.repository.list_events(self.user_ref)]
        self.assertIn(EVENT_JUDGMENT_COMPLETED, event_types)
        self.assertIn(EVENT_JUDGMENT_CORRECTED, event_types)

        keys = list(self.redis.scan_iter(match=f"ledger:{self.user_ref}:*"))
        self.assertTrue(keys)
        self.assertIn(index_key, keys)
        self.assertIn(index_key, self.redis.smembers(self.repository._registry_key(self.user_ref)))
        self.assertTrue(all(0 < self.redis.ttl(key) <= 86400 for key in keys))
        self.assertNotIn("9876543", self._stored_payload_text(keys))

        first_delete = self.service.delete_user_data(
            self.user_ref,
            idempotency_key="delete-1",
            correlation_id=correlation_id(),
        )
        second_delete = self.service.delete_user_data(
            self.user_ref,
            idempotency_key="delete-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual((first_delete.status, second_delete.status), (204, 204))
        self.assertEqual(list(self.redis.scan_iter(match=f"ledger:{self.user_ref}:*")), [])

    def test_legacy_judgment_scan_backfills_direct_transaction_index(self) -> None:
        self.service.upsert_profile(
            self.user_ref,
            profile_payload(),
            idempotency_key="profile-legacy-index",
            correlation_id=correlation_id(),
        )
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 9876543, "category": "shopping"},
            idempotency_key="tx-legacy-index",
            correlation_id=correlation_id(),
        )
        transaction_id = pending.data["transaction"]["transaction_id"]
        judged = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무 장비"},
            idempotency_key="reason-legacy-index",
            correlation_id=correlation_id(),
        )
        index_key = self.repository._judgment_for_transaction_key(self.user_ref, transaction_id)
        self.redis.delete(index_key)

        found = self.repository.get_judgment_for_transaction(self.user_ref, transaction_id)

        self.assertEqual(found.judgment_id, judged.data["judgment"]["judgment_id"])
        self.assertEqual(self.redis.get(index_key), found.judgment_id)

    def test_pending_question_mutations_are_serialized_per_user(self) -> None:
        barrier = threading.Barrier(3)
        results: list[str] = []
        errors: list[Exception] = []

        def save(question_id: str, transaction_id: str) -> None:
            barrier.wait()
            try:
                result = self.repository.save_pending_question(
                    self.user_ref,
                    PendingQuestion(
                        question_id=question_id,
                        transaction_id=transaction_id,
                        question="왜 샀어?",
                        asked_at=utc_now_iso(),
                    ),
                    idempotency_key=f"pending:{question_id}",
                    correlation_id=correlation_id(),
                )
                results.append(result.body["pending_question"]["question_id"])
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=save, args=("q-1", "tx-1")),
            threading.Thread(target=save, args=("q-2", "tx-2")),
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], DomainValidationError)
        self.assertEqual(self.repository.get_pending_question(self.user_ref).question_id, results[0])
        events = [
            event
            for event in self.repository.list_events(self.user_ref)
            if event.event_type == EVENT_JUDGMENT_REASON_REQUESTED
        ]
        self.assertEqual(len(events), 1)

    def test_app_and_worker_runtime_share_redis_projection(self) -> None:
        config = {
            "APP_ENV": "test",
            "ALLOW_DEV_AUTH": "1",
            "LEDGER_STORE": "redis",
            "REDIS_URL": REDIS_TEST_URL,
            "LEDGER_ENCRYPTION_KEY": FERNET_KEY.decode("ascii"),
            "LEDGER_USER_REF_SECRET": USER_REF_SECRET.decode("utf-8"),
            "LEDGER_RETENTION_DAYS": "1",
            "TESTING": True,
        }
        app = create_app(config)
        raw_user_id = f"shared-{uuid4().hex}"
        user_ref = app.extensions["ledger_privacy"].user_ref(raw_user_id)
        response = app.test_client().put(
            "/api/v1/me/profile",
            json=profile_payload(),
            headers={"X-User-Id": raw_user_id, "Idempotency-Key": "profile-shared"},
        )
        self.assertEqual(response.status_code, 200)

        worker_service, _privacy, worker_repository, _ready = create_ledger_runtime(config)
        self.assertIsNotNone(worker_repository.get_profile(user_ref))
        worker_service.delete_user_data(
            user_ref,
            idempotency_key="delete-shared",
            correlation_id=correlation_id(),
        )

    def _stored_payload_text(self, keys: list[str]) -> str:
        values: list[object] = []
        for key in keys:
            key_type = self.redis.type(key)
            if key_type == "string":
                values.append(self.redis.get(key))
            elif key_type == "stream":
                values.extend(self.redis.xrange(key))
            elif key_type == "zset":
                values.extend(self.redis.zrange(key, 0, -1))
        return repr(values)


if __name__ == "__main__":
    unittest.main()
