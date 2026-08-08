from __future__ import annotations

import unittest
import os
from unittest.mock import Mock, patch

import tasks
from ledger.application.service import ServiceResult
from ledger.domain.models import PendingQuestion
from tests.helpers import service_with_memory


class KakaoRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        tasks._runtime.cache_clear()

    def test_parses_korean_transaction_message(self) -> None:
        parsed = tasks._parse_transaction("커피 5,800원 마셨어")
        self.assertEqual(parsed["amount_krw"], 5800)

    def test_routes_grandma_mode_toggle_to_settings(self) -> None:
        service = Mock()
        reply = tasks._route_message(
            service,
            "usr_test",
            "욕쟁이 할머니 켜",
            idempotency_key="kakao:1",
            correlation_id="corr",
        )
        self.assertIn("욕쟁이 할머니 모드 켰다", reply)
        service.update_settings.assert_called_once()

    def test_routes_pending_question_answer_to_reason_flow(self) -> None:
        service, _repository, _privacy, _judge = service_with_memory()
        service.repository.save_pending_question(
            "usr_test",
            PendingQuestion(
                question_id="q-1",
                transaction_id="tx-1",
                question="왜 샀어?",
                asked_at="2026-08-01T00:00:00Z",
            ),
            idempotency_key="pending",
            correlation_id="corr",
        )
        service.add_reason = Mock(
            return_value=ServiceResult(201, {"judgment": {"message": "판단 완료"}})
        )
        reply = tasks._route_message(
            service,
            "usr_test",
            "필요해서",
            idempotency_key="kakao:2",
            correlation_id="corr",
        )
        self.assertEqual(reply, "판단 완료")

    def test_process_kakao_message_posts_mocked_callback(self) -> None:
        service, repository, privacy, _judge = service_with_memory()
        with patch.object(tasks, "_runtime", return_value=(service, privacy, repository)):
            with patch.object(tasks.requests, "post") as post:
                post.return_value.raise_for_status.return_value = None
                reply = tasks.process_kakao_message(
                    "kakao-user",
                    "커피 5,800원",
                    "https://callback.example/kakao",
                    idempotency_key="kakao:req-1",
                )
        self.assertIn("먼저 자산", reply)
        post.assert_called_once()

    def test_worker_rejects_memory_backed_rq_configuration(self) -> None:
        import worker

        with patch.dict(os.environ, {"LEDGER_STORE": "memory"}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "LEDGER_STORE=redis"):
                worker.main()


if __name__ == "__main__":
    unittest.main()
