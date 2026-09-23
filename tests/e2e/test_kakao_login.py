from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from ledger.factory import create_app
from ledger.kakao_login import KakaoLoginError, exchange_code
from tests.e2e.test_flask_api import app_config


class KakaoLoginTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(app_config(
            KAKAO_REST_API_KEY="public-test-client",
            KAKAO_LOGIN_CLIENT_SECRET="test-secret",
        ))
        self.client = self.app.test_client()
        self.headers = {"Origin": "http://localhost:3015"}

    def test_start_requests_only_kakao_identity_without_email_scope(self) -> None:
        response = self.client.post(
            "/api/v1/auth/kakao/start",
            json={"state": "s" * 64, "nonce_hash": "a" * 64,
                  "code_challenge": "b" * 43},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        url = urlsplit(response.get_json()["data"]["authorization_url"])
        query = parse_qs(url.query)
        self.assertEqual(url.netloc, "kauth.kakao.com")
        self.assertEqual(query["redirect_uri"], ["http://localhost:3015/auth/kakao"])
        self.assertEqual(query["nonce"], ["a" * 64])
        self.assertEqual(query["code_challenge"], ["b" * 43])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertNotIn("scope", query)
        self.assertNotIn("test-secret", response.get_data(as_text=True))

    def test_exchange_uses_fixed_origin_and_hides_secret(self) -> None:
        with patch("ledger.api.exchange_code", return_value="id-token") as exchange:
            response = self.client.post(
                "/api/v1/auth/kakao/exchange",
                json={"code": "one-time-code", "code_verifier": "v" * 64},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["id_token"], "id-token")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        exchange.assert_called_once_with(
            "public-test-client", "test-secret", "http://localhost:3015", "one-time-code",
            "v" * 64,
        )
        self.assertNotIn("test-secret", response.get_data(as_text=True))

    def test_rejects_untrusted_origin_before_exchange(self) -> None:
        with patch("ledger.api.exchange_code") as exchange:
            response = self.client.post(
                "/api/v1/auth/kakao/exchange",
                json={"code": "one-time-code", "code_verifier": "v" * 64},
                headers={"Origin": "https://attacker.example"},
            )
        self.assertEqual(response.status_code, 403)
        exchange.assert_not_called()

    def test_missing_secret_fails_closed(self) -> None:
        app = create_app(app_config(KAKAO_REST_API_KEY="public-test-client"))
        response = app.test_client().post(
            "/api/v1/auth/kakao/start",
            json={"state": "s" * 64, "nonce_hash": "a" * 64,
                  "code_challenge": "b" * 43},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 503)

    def test_token_exchange_uses_server_secret_without_redirects(self) -> None:
        with patch("ledger.kakao_login.requests.post") as post:
            post.return_value.json.return_value = {"id_token": "signed-id-token"}
            token = exchange_code(
                "public-test-client", "test-secret", "https://jangbu-ai.vercel.app",
                "one-time-code", "v" * 64,
            )
        self.assertEqual(token, "signed-id-token")
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://kauth.kakao.com/oauth/token")
        self.assertEqual(kwargs["data"]["redirect_uri"], "https://jangbu-ai.vercel.app/auth/kakao")
        self.assertEqual(kwargs["data"]["client_secret"], "test-secret")
        self.assertEqual(kwargs["data"]["code_verifier"], "v" * 64)
        self.assertFalse(kwargs["allow_redirects"])

    def test_token_exchange_rejects_missing_id_token(self) -> None:
        with patch("ledger.kakao_login.requests.post") as post:
            post.return_value.json.return_value = {"access_token": "not-an-id-token"}
            with self.assertRaises(KakaoLoginError):
                exchange_code("public-test-client", "test-secret", "https://jangbu-ai.vercel.app",
                              "code", "v" * 64)


if __name__ == "__main__":
    unittest.main()
