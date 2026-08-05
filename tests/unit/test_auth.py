from __future__ import annotations

import time
import unittest
from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from ledger.auth import (
    AuthConfigurationError,
    AuthenticationError,
    SupabaseJWTVerifier,
    parse_cors_origins,
)


class StaticSigningKeyClient:
    def __init__(self, key) -> None:
        self.key = key

    def get_signing_key_from_jwt(self, _token: str):
        return SimpleNamespace(key=self.key)


class SupabaseJWTVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.issuer = "https://project.supabase.co/auth/v1"
        self.verifier = SupabaseJWTVerifier(
            "https://project.supabase.co",
            "authenticated",
            signing_key_client=StaticSigningKeyClient(self.private_key.public_key()),
        )

    def token(self, **overrides) -> str:
        claims = {
            "aud": "authenticated",
            "exp": int(time.time()) + 300,
            "iss": self.issuer,
            "sub": "6f42d4bf-5d6a-44fc-ae8b-1f6f1bb63c50",
        }
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test"})

    def test_accepts_valid_asymmetric_access_token(self) -> None:
        self.assertEqual(
            self.verifier.verify_subject(self.token()),
            "6f42d4bf-5d6a-44fc-ae8b-1f6f1bb63c50",
        )

    def test_rejects_invalid_registered_claims(self) -> None:
        invalid_tokens = (
            self.token(iss="https://attacker.example/auth/v1"),
            self.token(aud="service_role"),
            self.token(exp=int(time.time()) - 1),
            self.token(sub=""),
        )
        for token in invalid_tokens:
            with self.subTest(token=token[-12:]), self.assertRaises(AuthenticationError):
                self.verifier.verify_subject(token)

    def test_rejects_shared_secret_algorithm(self) -> None:
        token = jwt.encode(
            {
                "aud": "authenticated",
                "exp": int(time.time()) + 300,
                "iss": self.issuer,
                "sub": "user-id",
            },
            "shared-secret-for-test-is-32-bytes-minimum",
            algorithm="HS256",
        )
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_subject(token)


class AuthConfigurationTests(unittest.TestCase):
    def test_production_cors_requires_exact_https_origins(self) -> None:
        self.assertEqual(
            parse_cors_origins(
                "https://jangbu-ai.vercel.app/, https://preview.example",
                production=True,
            ),
            frozenset({"https://jangbu-ai.vercel.app", "https://preview.example"}),
        )
        for value in ("", "*", "http://jangbu-ai.vercel.app", "https://example.com/path"):
            with self.subTest(value=value), self.assertRaises(AuthConfigurationError):
                parse_cors_origins(value, production=True)

    def test_supabase_url_must_be_an_https_origin(self) -> None:
        with self.assertRaises(AuthConfigurationError):
            SupabaseJWTVerifier("http://project.supabase.co", "authenticated")


if __name__ == "__main__":
    unittest.main()
