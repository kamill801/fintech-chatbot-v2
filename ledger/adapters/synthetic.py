"""Read-only account adapters for tests and the disabled production boundary."""

from __future__ import annotations

from dataclasses import dataclass, field

from ledger.domain.models import Transaction, utc_now_iso
from ledger.domain.ports import (
    AccountBalance,
    AccountConnection,
    ReadOnlyAccountAdapter,
)


class ProviderUnavailableError(RuntimeError):
    code = "provider_unavailable"


@dataclass(frozen=True)
class SyntheticProviderTransaction:
    transaction_id: str
    connection_id: str
    amount_krw: int
    category: str
    occurred_at: str
    source_reference: str


@dataclass
class SyntheticReadOnlyAccountAdapter(ReadOnlyAccountAdapter):
    connections: list[AccountConnection] = field(default_factory=list)
    balances: list[AccountBalance] = field(default_factory=list)
    transactions: list[SyntheticProviderTransaction] = field(default_factory=list)

    def list_connections(self, user_ref: str) -> list[AccountConnection]:
        return list(self.connections)

    def fetch_balances(
        self, user_ref: str, connection_id: str
    ) -> list[AccountBalance]:
        return [
            balance
            for balance in self.balances
            if balance.connection_id == connection_id
        ]

    def fetch_transactions(
        self,
        user_ref: str,
        connection_id: str,
        *,
        since: str | None = None,
    ) -> list[Transaction]:
        rows = [
            transaction
            for transaction in self.transactions
            if transaction.connection_id == connection_id
            and (since is None or transaction.occurred_at >= since)
        ]
        return [
            Transaction(
                transaction_id=row.transaction_id,
                user_ref=user_ref,
                amount_krw=row.amount_krw,
                merchant=None,
                category=row.category,
                description=None,
                occurred_at=row.occurred_at,
                source="synthetic",
                source_reference=row.source_reference,
                reason=None,
                status="recorded",
                created_at=utc_now_iso(),
            )
            for row in rows
        ]

    def revoke_connection(self, user_ref: str, connection_id: str) -> None:
        for index, connection in enumerate(self.connections):
            if connection.connection_id == connection_id:
                self.connections[index] = AccountConnection(
                    connection_id=connection.connection_id,
                    provider=connection.provider,
                    display_name=connection.display_name,
                    status="revoked",
                )
                return
        raise ProviderUnavailableError("account connection was not found")

    @classmethod
    def sample(cls) -> "SyntheticReadOnlyAccountAdapter":
        now = utc_now_iso()
        connection = AccountConnection(
            connection_id="synthetic-connection",
            provider="synthetic",
            display_name="synthetic-checking",
            status="active",
        )
        return cls(
            connections=[connection],
            balances=[
                AccountBalance(
                    connection_id=connection.connection_id,
                    balance_krw=1_000_000,
                    as_of=now,
                )
            ],
            transactions=[
                SyntheticProviderTransaction(
                    transaction_id="synthetic-tx-1",
                    connection_id=connection.connection_id,
                    amount_krw=50_000,
                    category="shopping",
                    occurred_at=now,
                    source_reference="synthetic:tx:1",
                )
            ],
        )


class DisabledProductionAccountAdapter(ReadOnlyAccountAdapter):
    """Fail closed until a provider and compliance path are approved."""

    def _unavailable(self) -> None:
        raise ProviderUnavailableError(
            "production account linking is disabled until separately approved"
        )

    def list_connections(self, user_ref: str) -> list[AccountConnection]:
        self._unavailable()

    def fetch_balances(
        self, user_ref: str, connection_id: str
    ) -> list[AccountBalance]:
        self._unavailable()

    def fetch_transactions(
        self,
        user_ref: str,
        connection_id: str,
        *,
        since: str | None = None,
    ) -> list[Transaction]:
        self._unavailable()

    def revoke_connection(self, user_ref: str, connection_id: str) -> None:
        self._unavailable()
