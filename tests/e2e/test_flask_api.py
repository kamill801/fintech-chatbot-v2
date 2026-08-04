from __future__ import annotations

import importlib
import json
import os
import unittest
from unittest.mock import patch

from ledger.auth import AuthConfigurationError, AuthenticationError
from tests.helpers import FERNET_KEY, USER_REF_SECRET, profile_payload


def app_config(**overrides):
    config = {
        "APP_ENV": "test",
        "ALLOW_DEV_AUTH": "1",
        "LEDGER_STORE": "memory",
        "LEDGER_ENCRYPTION_KEY": FERNET_KEY.decode("ascii"),
        "LEDGER_USER_REF_SECRET": USER_REF_SECRET.decode("utf-8"),
        "TESTING": True,
    }
    config.update(overrides)
    return config


class FlaskLedgerE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        from ledger.factory import create_app

        self.app = create_app(app_config())
        self.client = self.app.test_client()
        self.headers = {"X-User-Id": "e2e-user"}

    def mutate_headers(self, key: str) -> dict[str, str]:
        return {**self.headers, "Idempotency-Key": key}

    def put_profile(self) -> None:
        response = self.client.put(
            "/api/v1/me/profile",
            json=profile_payload(),
            headers=self.mutate_headers("profile-1"),
        )
        self.assertEqual(response.status_code, 200)

    def create_reason_judgment(self) -> tuple[str, str]:
        self.put_profile()
        tx = self.client.post(
            "/api/v1/me/transactions",
            json={"amount_krw": 50000, "category": "shopping"},
            headers=self.mutate_headers("tx-1"),
        )
        self.assertEqual(tx.status_code, 202)
        transaction_id = tx.get_json()["data"]["transaction"]["transaction_id"]
        judged = self.client.post(
            f"/api/v1/me/transactions/{transaction_id}/reason",
            json={"reason": "업무상 필요"},
            headers=self.mutate_headers("reason-1"),
        )
        self.assertEqual(judged.status_code, 201)
        judgment_id = judged.get_json()["data"]["judgment"]["judgment_id"]
        return transaction_id, judgment_id

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.get_json()["data"]["status"], "ok")

    def test_ready_returns_ready(self) -> None:
        response = self.client.get("/ready")
        self.assertEqual(response.get_json()["data"]["status"], "ready")

    def test_get_profile_returns_null_before_onboarding(self) -> None:
        response = self.client.get("/api/v1/me/profile", headers=self.headers)
        self.assertIsNone(response.get_json()["data"]["profile"])

    def test_transaction_before_profile_returns_profile_required(self) -> None:
        response = self.client.post(
            "/api/v1/me/transactions",
            json={"amount_krw": 50000, "category": "shopping"},
            headers=self.mutate_headers("tx-before-profile"),
        )
        self.assertEqual(response.get_json()["error"]["code"], "profile_required")

    def test_transaction_reason_flow_returns_judgment(self) -> None:
        _transaction_id, judgment_id = self.create_reason_judgment()
        self.assertTrue(judgment_id)

    def test_mutating_request_requires_idempotency_key(self) -> None:
        response = self.client.put(
            "/api/v1/me/profile",
            json=profile_payload(),
            headers=self.headers,
        )
        self.assertEqual(response.get_json()["error"]["code"], "idempotency_key_required")

    def test_transaction_post_is_idempotent(self) -> None:
        self.put_profile()
        first = self.client.post(
            "/api/v1/me/transactions",
            json={"amount_krw": 50000, "category": "shopping"},
            headers=self.mutate_headers("tx-idem"),
        )
        second = self.client.post(
            "/api/v1/me/transactions",
            json={"amount_krw": 50000, "category": "shopping"},
            headers=self.mutate_headers("tx-idem"),
        )
        self.assertEqual(
            first.get_json()["data"]["transaction"]["transaction_id"],
            second.get_json()["data"]["transaction"]["transaction_id"],
        )

    def test_settings_toggle_changes_share_eligibility(self) -> None:
        _transaction_id, judgment_id = self.create_reason_judgment()
        self.client.put(
            "/api/v1/me/settings",
            json={"roast_enabled": True},
            headers=self.mutate_headers("settings-1"),
        )
        response = self.client.post(
            f"/api/v1/me/judgments/{judgment_id}/share",
            headers=self.mutate_headers("share-1"),
        )
        self.assertIn("share", response.get_json()["data"])

    def test_correction_endpoint_appends_correction(self) -> None:
        transaction_id, judgment_id = self.create_reason_judgment()
        response = self.client.post(
            f"/api/v1/me/judgments/{judgment_id}/corrections",
            json={"corrected_label": "justified", "correction_reason": "환급 예정"},
            headers=self.mutate_headers("correction-1"),
        )
        self.assertEqual(response.get_json()["data"]["correction"]["corrected_label"], "justified")
        current = self.client.get(
            f"/api/v1/me/transactions/{transaction_id}", headers=self.headers
        ).get_json()["data"]["judgment"]
        self.assertEqual(current["original_label"], response.get_json()["data"]["correction"]["original_label"])
        self.assertEqual(current["effective_label"], "justified")
        self.assertEqual(current["correction"]["correction_reason"], "환급 예정")

    def test_summary_endpoint_returns_monthly_summary(self) -> None:
        self.create_reason_judgment()
        response = self.client.get("/api/v1/me/summary", headers=self.headers)
        self.assertIn("summary", response.get_json()["data"])

    def test_metrics_endpoint_reports_share_rate(self) -> None:
        _transaction_id, judgment_id = self.create_reason_judgment()
        self.client.put(
            "/api/v1/me/settings",
            json={"roast_enabled": True},
            headers=self.mutate_headers("settings-1"),
        )
        self.client.post(
            f"/api/v1/me/judgments/{judgment_id}/share-view",
            headers=self.mutate_headers("share-view-1"),
        )
        self.client.post(
            f"/api/v1/me/judgments/{judgment_id}/share",
            headers=self.mutate_headers("share-1"),
        )
        response = self.client.get("/api/v1/me/metrics", headers=self.headers)
        self.assertEqual(response.get_json()["data"]["metrics"]["roast_share_rate"], 1.0)

    def test_delete_data_returns_204(self) -> None:
        self.put_profile()
        response = self.client.delete(
            "/api/v1/me/data",
            headers=self.mutate_headers("delete-1"),
        )
        self.assertEqual(response.status_code, 204)

    def test_revoke_account_returns_provider_unavailable(self) -> None:
        response = self.client.post(
            "/api/v1/me/accounts/conn-1/revoke",
            headers=self.mutate_headers("revoke-1"),
        )
        self.assertEqual(response.get_json()["error"]["code"], "provider_unavailable")

    def test_production_rejects_x_user_id(self) -> None:
        from ledger.factory import create_app

        app = create_app(self.production_config(AUTH_VERIFIER=lambda _token: "prod-user"))
        response = app.test_client().get(
            "/api/v1/me/profile", headers={"X-User-Id": "prod-user"}
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"]["code"], "unauthorized")

    def test_production_requires_trusted_auth_and_tls_redis_config(self) -> None:
        from ledger.factory import create_app

        with self.assertRaises(AuthConfigurationError):
            create_app(
                app_config(
                    APP_ENV="production",
                    LEDGER_STORE="redis",
                    REDIS_URL="rediss://example/0",
                    SUPABASE_URL="",
                    SUPABASE_JWT_AUDIENCE="",
                    CORS_ALLOWED_ORIGINS="https://jangbu-ai.vercel.app",
                )
            )
        with self.assertRaises(ValueError):
            create_app(
                self.production_config(
                    REDIS_URL="redis://example/0",
                    AUTH_VERIFIER=lambda _token: "prod-user",
                )
            )

    def test_production_bearer_subject_crosses_only_pseudonym_boundary(self) -> None:
        from ledger.factory import create_app

        app = create_app(self.production_config(AUTH_VERIFIER=lambda token: f"subject-{token}"))
        service = app.extensions["ledger_service"]
        expected = app.extensions["ledger_privacy"].user_ref("subject-valid-token")
        with patch.object(service, "get_profile", wraps=service.get_profile) as get_profile:
            service.repository.get_profile = lambda _user_ref: None
            response = app.test_client().get(
                "/api/v1/me/profile",
                headers={"Authorization": "Bearer valid-token"},
            )
        self.assertEqual(response.status_code, 200)
        get_profile.assert_called_once_with(expected)

    def test_production_rejects_missing_and_invalid_bearer_tokens(self) -> None:
        from ledger.factory import create_app

        def reject(_token: str) -> str:
            raise AuthenticationError("invalid")

        app = create_app(self.production_config(AUTH_VERIFIER=reject))
        client = app.test_client()
        missing = client.get("/api/v1/me/profile")
        malformed = client.get(
            "/api/v1/me/profile", headers={"Authorization": "Basic token"}
        )
        invalid = client.get(
            "/api/v1/me/profile", headers={"Authorization": "Bearer invalid"}
        )
        self.assertEqual([missing.status_code, malformed.status_code, invalid.status_code], [401, 401, 401])

    def test_cors_allows_only_configured_origin(self) -> None:
        from ledger.factory import create_app

        cors_app = create_app(
            app_config(CORS_ALLOWED_ORIGINS="https://jangbu-ai.vercel.app")
        )
        client = cors_app.test_client()
        allowed = client.options(
            "/api/v1/me/profile",
            headers={
                "Origin": "https://jangbu-ai.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        blocked = client.options(
            "/api/v1/me/profile",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(allowed.status_code, 204)
        self.assertEqual(
            allowed.headers["Access-Control-Allow-Origin"],
            "https://jangbu-ai.vercel.app",
        )
        self.assertNotIn("Access-Control-Allow-Credentials", allowed.headers)
        self.assertEqual(blocked.status_code, 403)
        self.assertNotIn("Access-Control-Allow-Origin", blocked.headers)

    @staticmethod
    def production_config(**overrides):
        config = app_config(
            APP_ENV="production",
            LEDGER_STORE="redis",
            REDIS_URL="rediss://example/0",
            CORS_ALLOWED_ORIGINS="https://jangbu-ai.vercel.app",
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_JWT_AUDIENCE="authenticated",
        )
        config.update(overrides)
        return config


class FixtureTests(unittest.TestCase):
    def test_judgment_scenarios_fixture_contains_required_cases(self) -> None:
        with open("tests/fixtures/judgment_scenarios_v1.json", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(len(payload["cases"]), 10)


class KakaoEndpointE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        modules = ["app"]
        for module_name in modules:
            if module_name in list(importlib.sys.modules):
                del importlib.sys.modules[module_name]

    def test_question_endpoint_uses_mocked_callback_in_testing_mode(self) -> None:
        env = app_config()
        env["TESTING"] = "1"
        with patch.dict(os.environ, env, clear=False):
            import app as app_module

            app_module.app.config["TESTING"] = True
            with patch("tasks.requests.post") as post:
                post.return_value.raise_for_status.return_value = None
                response = app_module.app.test_client().post(
                    "/question",
                    json={
                        "userRequest": {
                            "user": {"id": "kakao-user"},
                            "utterance": "커피 5,800원",
                            "callbackUrl": "https://callback.example/kakao",
                            "requestId": "req-1",
                        }
                    },
                )
        self.assertTrue(response.get_json()["useCallback"])
        post.assert_called_once()

    def test_question_endpoint_does_not_queue_with_memory_store(self) -> None:
        with patch.dict(
            os.environ,
            self._environment_config(REDIS_URL="redis://localhost:6379/0"),
            clear=False,
        ):
            import app as app_module

            self.assertIsNone(app_module._queue())

    def test_production_question_fails_closed_without_transport_config(self) -> None:
        with patch.dict(os.environ, self._environment_config(), clear=False):
            import app as app_module

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "KAKAO_WEBHOOK_SECRET": "",
                "KAKAO_CALLBACK_HOSTS": "",
            },
            clear=False,
        ):
            response = app_module.app.test_client().post(
                "/question", json=self._payload(request_id="req-prod-1")
            )
        self.assertEqual(response.status_code, 503)

    def test_production_question_rejects_wrong_secret(self) -> None:
        with patch.dict(os.environ, self._environment_config(), clear=False):
            import app as app_module

        with patch.dict(os.environ, self._production_transport_env(), clear=False):
            response = app_module.app.test_client().post(
                "/question",
                json=self._payload(request_id="req-prod-2"),
                headers={"X-Kakao-Webhook-Secret": "wrong"},
            )
        self.assertEqual(response.status_code, 401)

    def test_production_question_rejects_untrusted_callback_host(self) -> None:
        with patch.dict(os.environ, self._environment_config(), clear=False):
            import app as app_module

        with patch.dict(os.environ, self._production_transport_env(), clear=False):
            response = app_module.app.test_client().post(
                "/question",
                json=self._payload(
                    callback_url="https://attacker.example/kakao",
                    request_id="req-prod-3",
                ),
                headers={"X-Kakao-Webhook-Secret": "transport-secret"},
            )
        self.assertEqual(response.status_code, 400)

    def test_production_question_requires_verified_request_id(self) -> None:
        with patch.dict(os.environ, self._environment_config(), clear=False):
            import app as app_module

        with patch.dict(os.environ, self._production_transport_env(), clear=False):
            response = app_module.app.test_client().post(
                "/question",
                json=self._payload(),
                headers={"X-Kakao-Webhook-Secret": "transport-secret"},
            )
        self.assertEqual(response.status_code, 400)

    @staticmethod
    def _production_transport_env() -> dict[str, str]:
        return {
            "APP_ENV": "production",
            "KAKAO_WEBHOOK_SECRET": "transport-secret",
            "KAKAO_CALLBACK_HOSTS": "callback.example",
        }

    @staticmethod
    def _environment_config(**overrides) -> dict[str, str]:
        return {key: str(value) for key, value in app_config(**overrides).items()}

    @staticmethod
    def _payload(
        *,
        callback_url: str = "https://callback.example/kakao",
        request_id: str | None = None,
    ) -> dict:
        user_request = {
            "user": {"id": "kakao-user"},
            "utterance": "커피 5,800원",
            "callbackUrl": callback_url,
        }
        if request_id:
            user_request["requestId"] = request_id
        return {"userRequest": user_request}


if __name__ == "__main__":
    unittest.main()
