"""Encrypted, short-lived review receipts; previews do not write to storage."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class InvalidPlanPreview(ValueError):
    pass


class PlanPreviewTokens:
    def __init__(self, encryption_key: bytes | None = None, *, ttl_seconds: int = 900) -> None:
        self._fernet = Fernet(encryption_key or Fernet.generate_key())
        self.ttl_seconds = ttl_seconds

    def issue(self, claims: dict[str, Any]) -> str:
        encoded = json.dumps(
            {**claims, "purpose": "ledger-plan-review-v1"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return self._fernet.encrypt(encoded).decode("ascii")

    def read(self, token: str, *, user_ref: str, operation: str) -> dict[str, Any]:
        try:
            if not isinstance(token, str) or len(token) > 200_000:
                raise InvalidPlanPreview("invalid review token")
            claims = json.loads(self._fernet.decrypt(token.encode("ascii"), ttl=self.ttl_seconds))
            if (
                not isinstance(claims, dict)
                or claims.get("purpose") != "ledger-plan-review-v1"
                or claims.get("user_ref") != user_ref
                or claims.get("operation") != operation
            ):
                raise InvalidPlanPreview("invalid review owner or operation")
            return claims
        except (InvalidToken, ValueError, UnicodeError, TypeError) as exc:
            raise InvalidPlanPreview("review expired or invalid") from exc
