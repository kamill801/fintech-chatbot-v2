"""Manual transaction source for first-class user-entered ledger records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from ledger.domain.models import Transaction


@dataclass(frozen=True)
class ManualTransactionDraft:
    user_ref: str
    amount_krw: int
    category: str
    occurred_at: str
    merchant: str | None = None
    description: str | None = None
    reason: str | None = None
    idempotency_key: str | None = None
    transaction_type: str = "expense"
    account_id: str = "cash"
    destination_account_id: str | None = None
    exclude_from_budget: bool = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ManualTransactionSource:
    """Builds normalized manual transaction records without provider access."""

    source = "manual"

    def create_record(self, draft: ManualTransactionDraft) -> Transaction:
        if draft.amount_krw <= 0:
            raise ValueError("amount_krw must be positive")
        if not draft.user_ref:
            raise ValueError("user_ref is required")
        if not draft.category:
            raise ValueError("category is required")
        return Transaction(
            transaction_id=str(uuid4()),
            user_ref=draft.user_ref,
            amount_krw=draft.amount_krw,
            merchant=draft.merchant,
            category=draft.category,
            description=draft.description,
            occurred_at=draft.occurred_at,
            source="manual",
            source_reference=None,
            reason=draft.reason,
            status="recorded",
            created_at=_utc_now(),
            transaction_type=draft.transaction_type,
            account_id=draft.account_id,
            destination_account_id=draft.destination_account_id,
            exclude_from_budget=draft.exclude_from_budget,
        )
