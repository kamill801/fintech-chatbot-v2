from __future__ import annotations

from typing import Any, Mapping, Protocol
from urllib.parse import urlsplit

import jwt
from jwt import PyJWKClient


ALLOWED_JWT_ALGORITHMS = ("RS256", "ES256")


class AuthConfigurationError(ValueError):
    pass


class AuthenticationError(ValueError):
    pass


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class SupabaseJWTVerifier:
    def __init__(
        self,
        supabase_url: str,
        audience: str,
        *,
        signing_key_client: SigningKeyClient | None = None,
    ) -> None:
        base_url = _validated_https_base_url(supabase_url, "SUPABASE_URL")
        if not audience.strip():
            raise AuthConfigurationError("SUPABASE_JWT_AUDIENCE is required")
        self.issuer = f"{base_url}/auth/v1"
        self.audience = audience.strip()
        self._signing_keys = signing_key_client or PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json",
            cache_keys=False,
            cache_jwk_set=True,
            lifespan=300,
            timeout=5,
        )

    def verify_subject(self, token: str) -> str:
        if not token:
            raise AuthenticationError("bearer token is required")
        try:
            signing_key = self._signing_keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=list(ALLOWED_JWT_ALGORITHMS),
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["aud", "exp", "iss", "sub"]},
            )
        except Exception as exc:
            if isinstance(exc, AuthenticationError):
                raise
            raise AuthenticationError("invalid access token") from exc
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip() or len(subject) > 255:
            raise AuthenticationError("invalid access token subject")
        return subject.strip()


def create_production_verifier(
    values: Mapping[str, str],
) -> SupabaseJWTVerifier:
    return SupabaseJWTVerifier(
        values.get("SUPABASE_URL", ""),
        values.get("SUPABASE_JWT_AUDIENCE", ""),
    )


def parse_cors_origins(raw_value: str, *, production: bool) -> frozenset[str]:
    origins: set[str] = set()
    for candidate in raw_value.split(","):
        origin = candidate.strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            raise AuthConfigurationError("wildcard CORS origins are forbidden")
        parts = urlsplit(origin)
        allowed_schemes = {"https"} if production else {"http", "https"}
        if (
            parts.scheme not in allowed_schemes
            or not parts.netloc
            or parts.username
            or parts.password
            or parts.path
            or parts.query
            or parts.fragment
        ):
            raise AuthConfigurationError(f"invalid CORS origin: {origin}")
        origins.add(origin)
    if production and not origins:
        raise AuthConfigurationError("CORS_ALLOWED_ORIGINS is required in production")
    return frozenset(origins)


def _validated_https_base_url(value: str, name: str) -> str:
    base_url = value.strip().rstrip("/")
    parts = urlsplit(base_url)
    if (
        parts.scheme != "https"
        or not parts.netloc
        or parts.username
        or parts.password
        or parts.path
        or parts.query
        or parts.fragment
    ):
        raise AuthConfigurationError(f"{name} must be an HTTPS origin")
    return base_url
