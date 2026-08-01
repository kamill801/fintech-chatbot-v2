from __future__ import annotations

import unittest

from ledger.application.service import ServiceError
from ledger.domain.events import (
    EVENT_JUDGMENT_COMPLETED,
    EVENT_JUDGMENT_CORRECTED,
    EVENT_JUDGMENT_REASON_REQUESTED,
    EVENT_TRANSACTION_RECORDED,
)
from tests.helpers import correlation_id, profile_payload, service_with_memory


class InMemoryLedgerFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service, self.repository, _privacy, self.judge = service_with_memory()
        self.user_ref = "usr_test"

    def upsert_profile(self) -> None:
        self.service.upsert_profile(
            self.user_ref,
            profile_payload(),
            idempotency_key="profile-1",
            correlation_id=correlation_id(),
        )

    def test_rejects_transaction_when_profile_is_missing(self) -> None:
        with self.assertRaises(ServiceError) as caught:
            self.service.create_transaction(
                self.user_ref,
                {"amount_krw": 50000, "category": "shopping"},
                idempotency_key="tx-1",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.code, "profile_required")

    def test_records_pending_question_for_sparse_transaction(self) -> None:
        self.upsert_profile()
        result = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(result.status, 202)
        self.assertIn("pending_question", result.data)

    def test_repeated_transaction_idempotency_returns_same_pending_question(self) -> None:
        self.upsert_profile()
        first = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        second = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(
            first.data["pending_question"]["question_id"],
            second.data["pending_question"]["question_id"],
        )

    def test_creates_exactly_one_reason_question_event_per_transaction(self) -> None:
        self.upsert_profile()
        self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        reason_events = [
            event
            for event in self.repository.list_events(self.user_ref)
            if event.event_type == EVENT_JUDGMENT_REASON_REQUESTED
        ]
        self.assertEqual(len(reason_events), 1)

    def test_reason_submission_completes_judgment(self) -> None:
        self.upsert_profile()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        transaction_id = pending.data["transaction"]["transaction_id"]
        judged = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(judged.status, 201)

    def test_repeated_reason_submission_is_idempotent_after_judgment(self) -> None:
        self.upsert_profile()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        transaction_id = pending.data["transaction"]["transaction_id"]
        first = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        second = self.service.add_reason(
            self.user_ref,
            transaction_id,
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        self.assertEqual(
            first.data["judgment"]["judgment_id"],
            second.data["judgment"]["judgment_id"],
        )

    def test_correction_appends_event_without_removing_original_judgment(self) -> None:
        self.upsert_profile()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        judged = self.service.add_reason(
            self.user_ref,
            pending.data["transaction"]["transaction_id"],
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        self.service.correct_judgment(
            self.user_ref,
            judged.data["judgment"]["judgment_id"],
            {"corrected_label": "justified", "correction_reason": "환급 예정"},
            idempotency_key="correction-1",
            correlation_id=correlation_id(),
        )
        event_types = [event.event_type for event in self.repository.list_events(self.user_ref)]
        self.assertIn(EVENT_JUDGMENT_COMPLETED, event_types)
        self.assertIn(EVENT_JUDGMENT_CORRECTED, event_types)
        current = self.service.get_transaction(
            self.user_ref, pending.data["transaction"]["transaction_id"]
        ).data["judgment"]
        self.assertNotEqual(current["original_label"], "")
        self.assertEqual(current["effective_label"], "justified")
        self.assertEqual(current["correction"]["correction_reason"], "환급 예정")

    def test_share_requires_roast_enabled(self) -> None:
        self.upsert_profile()
        pending = self.service.create_transaction(
            self.user_ref,
            {"amount_krw": 50000, "category": "shopping"},
            idempotency_key="tx-1",
            correlation_id=correlation_id(),
        )
        judged = self.service.add_reason(
            self.user_ref,
            pending.data["transaction"]["transaction_id"],
            {"reason": "업무상 필요해서 샀다"},
            idempotency_key="reason-1",
            correlation_id=correlation_id(),
        )
        with self.assertRaises(ServiceError) as caught:
            self.service.share_judgment(
                self.user_ref,
                judged.data["judgment"]["judgment_id"],
                idempotency_key="share-1",
                correlation_id=correlation_id(),
            )
        self.assertEqual(caught.exception.code, "roast_required")

    def test_deletion_purges_profile_projection(self) -> None:
        self.upsert_profile()
        self.service.delete_user_data(
            self.user_ref,
            idempotency_key="delete-1",
            correlation_id=correlation_id(),
        )
        self.assertIsNone(self.repository.get_profile(self.user_ref))


if __name__ == "__main__":
    unittest.main()
