"""Reason-question state machine for ledger transaction judgment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from ledger.domain.models import DeterministicSignalSet, PendingQuestion


class StateTransitionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LedgerState:
    transaction_id: str
    status: str = "recorded"
    reason_question: PendingQuestion | None = None
    reason: str | None = None
    judgment_id: str | None = None
    correction_count: int = 0


@dataclass(frozen=True)
class StateTransition:
    state: LedgerState
    event_type: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LedgerStateMachine:
    """Enforces one reason question and the TECHSPEC transition order."""

    def record_transaction(self, transaction_id: str, *, profile_exists: bool) -> StateTransition:
        if not profile_exists:
            raise StateTransitionError(
                "profile_required",
                "A financial profile is required before recording transactions.",
            )
        return StateTransition(
            state=LedgerState(transaction_id=transaction_id, status="recorded"),
            event_type="transaction.recorded",
        )

    def after_signals(
        self,
        state: LedgerState,
        signals: DeterministicSignalSet,
    ) -> StateTransition:
        if state.status != "recorded":
            raise StateTransitionError("invalid_state", "Signals apply only to recorded transactions.")
        if signals.requires_reason:
            return self.request_reason(state)
        return StateTransition(state=LedgerState(transaction_id=state.transaction_id, status="judged"), event_type="judgment.ready")

    def request_reason(self, state: LedgerState) -> StateTransition:
        if state.status != "recorded":
            raise StateTransitionError("invalid_state", "Reason questions can only follow recorded transactions.")
        if state.reason_question is not None:
            raise StateTransitionError("reason_question_exists", "Exactly one reason question is permitted.")
        question = PendingQuestion(
            question_id=str(uuid4()),
            transaction_id=state.transaction_id,
            question="이 지출이 꼭 필요했던 이유가 뭐야?",
            asked_at=_utc_now(),
        )
        return StateTransition(
            state=LedgerState(
                transaction_id=state.transaction_id,
                status="awaiting_reason",
                reason_question=question,
            ),
            event_type="judgment.reason_requested",
        )

    def add_reason(self, state: LedgerState, reason: str) -> StateTransition:
        if state.status == "judged" and state.reason:
            return StateTransition(state=state, event_type="transaction.reason_added")
        if state.status != "awaiting_reason" or state.reason_question is None:
            raise StateTransitionError("invalid_state", "Reason can be added only to an awaiting transaction.")
        if state.reason:
            return StateTransition(state=state, event_type="transaction.reason_added")
        answered = PendingQuestion(
            question_id=state.reason_question.question_id,
            transaction_id=state.reason_question.transaction_id,
            question=state.reason_question.question,
            asked_at=state.reason_question.asked_at,
            answered_at=_utc_now(),
            attempt_count=state.reason_question.attempt_count + 1,
        )
        return StateTransition(
            state=LedgerState(
                transaction_id=state.transaction_id,
                status="judged",
                reason_question=answered,
                reason=reason,
            ),
            event_type="transaction.reason_added",
        )

    def complete_judgment(self, state: LedgerState, judgment_id: str) -> StateTransition:
        if state.status not in {"recorded", "judged"}:
            raise StateTransitionError("invalid_state", "Judgment completion requires recorded or reasoned state.")
        return StateTransition(
            state=LedgerState(
                transaction_id=state.transaction_id,
                status="judged",
                reason_question=state.reason_question,
                reason=state.reason,
                judgment_id=judgment_id,
                correction_count=state.correction_count,
            ),
            event_type="judgment.completed",
        )

    def correct_judgment(self, state: LedgerState) -> StateTransition:
        if state.status != "judged" or not state.judgment_id:
            raise StateTransitionError("invalid_state", "Only completed judgments can be corrected.")
        return StateTransition(
            state=LedgerState(
                transaction_id=state.transaction_id,
                status="corrected",
                reason_question=state.reason_question,
                reason=state.reason,
                judgment_id=state.judgment_id,
                correction_count=state.correction_count + 1,
            ),
            event_type="judgment.corrected",
        )
