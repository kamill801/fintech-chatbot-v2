from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ledger.domain.events import EventEnvelope
from ledger.domain.models import (
    FinancialProfile,
    JudgmentCorrection,
    JudgmentResult,
    PendingQuestion,
    Transaction,
    UserSettings,
)


@dataclass(frozen=True)
class StoredResult:
    status: int
    body: dict[str, Any]


@dataclass(frozen=True)
class AccountConnection:
    connection_id: str
    provider: str
    display_name: str
    status: str


@dataclass(frozen=True)
class AccountBalance:
    connection_id: str
    balance_krw: int
    as_of: str


class LedgerRepository(ABC):
    """Storage boundary for event streams and encrypted projections."""

    @abstractmethod
    def get_profile(self, user_ref: str) -> FinancialProfile | None:
        raise NotImplementedError

    @abstractmethod
    def get_cached_result(
        self, user_ref: str, idempotency_key: str
    ) -> StoredResult | None:
        raise NotImplementedError

    @abstractmethod
    def cache_result(
        self, user_ref: str, idempotency_key: str, result: StoredResult
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def upsert_profile(
        self,
        profile: FinancialProfile,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def get_settings(self, user_ref: str) -> UserSettings:
        raise NotImplementedError

    @abstractmethod
    def update_settings(
        self,
        user_ref: str,
        settings: UserSettings,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def record_transaction(
        self,
        transaction: Transaction,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def get_transaction(self, user_ref: str, transaction_id: str) -> Transaction | None:
        raise NotImplementedError

    @abstractmethod
    def list_transactions(self, user_ref: str) -> Sequence[Transaction]:
        raise NotImplementedError

    @abstractmethod
    def update_transaction(
        self,
        transaction: Transaction,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def delete_transaction(
        self,
        user_ref: str,
        transaction_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def save_pending_question(
        self,
        user_ref: str,
        pending_question: PendingQuestion,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def get_pending_question(self, user_ref: str) -> PendingQuestion | None:
        raise NotImplementedError

    @abstractmethod
    def add_transaction_reason(
        self,
        user_ref: str,
        transaction_id: str,
        reason: str,
        *,
        answered_at: str,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def reflect_transaction(
        self,
        user_ref: str,
        transaction_id: str,
        reflection: str,
        *,
        reflection_note: str | None,
        reflected_at: str,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def save_judgment(
        self,
        user_ref: str,
        judgment: JudgmentResult,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def get_judgment(self, user_ref: str, judgment_id: str) -> JudgmentResult | None:
        raise NotImplementedError

    @abstractmethod
    def get_judgment_for_transaction(
        self, user_ref: str, transaction_id: str
    ) -> JudgmentResult | None:
        raise NotImplementedError

    @abstractmethod
    def get_judgment_correction(
        self, user_ref: str, judgment_id: str
    ) -> JudgmentCorrection | None:
        raise NotImplementedError

    @abstractmethod
    def correct_judgment(
        self,
        user_ref: str,
        judgment_id: str,
        corrected_label: str,
        *,
        correction_reason: str | None,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def record_share_view(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def record_share_click(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def record_share_success(
        self,
        user_ref: str,
        judgment_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def revoke_account(
        self,
        user_ref: str,
        connection_id: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def import_legacy_metadata(
        self,
        user_ref: str,
        metadata: Mapping[str, Any],
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def request_data_deletion(
        self,
        user_ref: str,
        *,
        idempotency_key: str,
        correlation_id: str,
        source: str = "api",
    ) -> StoredResult:
        raise NotImplementedError

    @abstractmethod
    def get_metrics(self, user_ref: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, user_ref: str) -> Sequence[EventEnvelope]:
        raise NotImplementedError


class ReadOnlyAccountAdapter(ABC):
    """Provider port. MVP permits read and revocation only."""

    @abstractmethod
    def list_connections(self, user_ref: str) -> Sequence[AccountConnection]:
        raise NotImplementedError

    @abstractmethod
    def fetch_balances(
        self, user_ref: str, connection_id: str
    ) -> Sequence[AccountBalance]:
        raise NotImplementedError

    @abstractmethod
    def fetch_transactions(
        self, user_ref: str, connection_id: str, *, since: str | None = None
    ) -> Sequence[Transaction]:
        raise NotImplementedError

    @abstractmethod
    def revoke_connection(self, user_ref: str, connection_id: str) -> None:
        raise NotImplementedError
