from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from ledger.domain.models import (
    SCHEMA_VERSION,
    DomainValidationError,
    Transaction,
    parse_date,
    parse_utc_datetime,
    require_non_negative_int,
    require_positive_int,
)


ALLOWED_PLAN_STATUSES = frozenset({"draft", "active"})
ALLOWED_CHECK_IN_DECISIONS = frozenset({"maintain", "adjust"})


@dataclass(frozen=True)
class PlanPriority:
    priority_id: str
    name: str
    rank: int

    def __post_init__(self) -> None:
        if not self.priority_id:
            raise DomainValidationError("priority_id is required")
        if not self.name or len(self.name) > 60:
            raise DomainValidationError("priority name must be 1 to 60 characters")
        if self.rank not in {1, 2, 3}:
            raise DomainValidationError("priority rank must be between 1 and 3")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanPriority:
        return cls(str(payload["priority_id"]), str(payload["name"]), int(payload["rank"]))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanAllocation:
    allocation_id: str
    label: str
    start_date: str
    end_date: str
    amount_krw: int

    def __post_init__(self) -> None:
        if not self.allocation_id:
            raise DomainValidationError("allocation_id is required")
        if not self.label or len(self.label) > 60:
            raise DomainValidationError("allocation label must be 1 to 60 characters")
        start = parse_date(self.start_date, "allocation.start_date")
        end = parse_date(self.end_date, "allocation.end_date")
        if end < start:
            raise DomainValidationError("allocation end_date must be on or after start_date")
        require_non_negative_int(self.amount_krw, "allocation.amount_krw")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanAllocation:
        return cls(
            allocation_id=str(payload["allocation_id"]),
            label=str(payload["label"]),
            start_date=str(payload["start_date"]),
            end_date=str(payload["end_date"]),
            amount_krw=int(payload["amount_krw"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlannedExpense:
    planned_expense_id: str
    name: str
    amount_krw: int
    due_date: str
    category: str
    matched_transaction_id: str | None = None
    matched_at: str | None = None

    def __post_init__(self) -> None:
        if not self.planned_expense_id:
            raise DomainValidationError("planned_expense_id is required")
        if not self.name or len(self.name) > 80:
            raise DomainValidationError("planned expense name must be 1 to 80 characters")
        require_positive_int(self.amount_krw, "planned_expense.amount_krw")
        parse_date(self.due_date, "planned_expense.due_date")
        if not self.category or len(self.category) > 40:
            raise DomainValidationError("planned expense category must be 1 to 40 characters")
        if bool(self.matched_transaction_id) != bool(self.matched_at):
            raise DomainValidationError("planned expense match id and timestamp must be set together")
        if self.matched_at:
            parse_utc_datetime(self.matched_at, "planned_expense.matched_at")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlannedExpense:
        return cls(
            planned_expense_id=str(payload["planned_expense_id"]),
            name=str(payload["name"]),
            amount_krw=int(payload["amount_krw"]),
            due_date=str(payload["due_date"]),
            category=str(payload.get("category", "other")),
            matched_transaction_id=payload.get("matched_transaction_id"),
            matched_at=payload.get("matched_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanRevision:
    revision_id: str
    from_version: int
    to_version: int
    reason: str | None
    applied_at: str
    before: dict[str, Any]
    after: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.revision_id:
            raise DomainValidationError("revision_id is required")
        if self.from_version < 1 or self.to_version != self.from_version + 1:
            raise DomainValidationError("revision versions must be consecutive")
        if self.reason is not None and len(self.reason) > 200:
            raise DomainValidationError("revision reason must be at most 200 characters")
        parse_utc_datetime(self.applied_at, "revision.applied_at")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanRevision:
        return cls(
            revision_id=str(payload["revision_id"]),
            from_version=int(payload["from_version"]),
            to_version=int(payload["to_version"]),
            reason=payload.get("reason"),
            applied_at=str(payload["applied_at"]),
            before=dict(payload["before"]),
            after=dict(payload["after"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanCheckIn:
    check_in_id: str
    decision: str
    note: str | None
    checked_in_at: str
    plan_version: int

    def __post_init__(self) -> None:
        if not self.check_in_id:
            raise DomainValidationError("check_in_id is required")
        if self.decision not in ALLOWED_CHECK_IN_DECISIONS:
            raise DomainValidationError("check-in decision must be maintain or adjust")
        if self.note is not None and len(self.note) > 200:
            raise DomainValidationError("check-in note must be at most 200 characters")
        if self.plan_version < 1:
            raise DomainValidationError("check-in plan_version must be positive")
        parse_utc_datetime(self.checked_in_at, "check_in.checked_in_at")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PlanCheckIn:
        return cls(
            check_in_id=str(payload["check_in_id"]),
            decision=str(payload["decision"]),
            note=payload.get("note"),
            checked_in_at=str(payload["checked_in_at"]),
            plan_version=int(payload["plan_version"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpendingPlan:
    plan_id: str
    user_ref: str
    period_start: str
    period_end: str
    confirmed_budget_krw: int
    priorities: list[PlanPriority]
    allocations: list[PlanAllocation]
    planned_expenses: list[PlannedExpense]
    status: str
    version: int
    confirmed_at: str | None
    created_at: str
    updated_at: str
    narrative: dict[str, Any] | None = None
    revisions: list[PlanRevision] = field(default_factory=list)
    check_ins: list[PlanCheckIn] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.plan_id or not self.user_ref:
            raise DomainValidationError("plan_id and user_ref are required")
        start = parse_date(self.period_start, "plan.period_start")
        end = parse_date(self.period_end, "plan.period_end")
        if end < start:
            raise DomainValidationError("plan period_end must be on or after period_start")
        if (end - start).days > 366:
            raise DomainValidationError("plan period cannot exceed 366 days")
        require_positive_int(self.confirmed_budget_krw, "confirmed_budget_krw")
        if self.status not in ALLOWED_PLAN_STATUSES:
            raise DomainValidationError("unsupported plan status")
        if self.version < 1:
            raise DomainValidationError("plan version must be positive")
        if self.status == "active" and self.confirmed_at is None:
            raise DomainValidationError("active plan requires confirmed_at")
        if self.confirmed_at:
            parse_utc_datetime(self.confirmed_at, "confirmed_at")
        parse_utc_datetime(self.created_at, "created_at")
        parse_utc_datetime(self.updated_at, "updated_at")
        if self.narrative is not None and not isinstance(self.narrative, dict):
            raise DomainValidationError("plan narrative must be an object")
        if not isinstance(self.priorities, list) or len(self.priorities) > 3:
            raise DomainValidationError("priorities must contain at most 3 items")
        ranks = [item.rank for item in self.priorities]
        if len(ranks) != len(set(ranks)):
            raise DomainValidationError("priority ranks must be unique")
        allocation_total = sum(item.amount_krw for item in self.allocations)
        if allocation_total != self.confirmed_budget_krw:
            raise DomainValidationError("allocation amounts must equal confirmed_budget_krw")
        if not self.allocations:
            raise DomainValidationError("plan requires at least one allocation")
        previous_end: date | None = None
        ordered_allocations = sorted(self.allocations, key=lambda item: item.start_date)
        for index, allocation in enumerate(ordered_allocations):
            allocation_start = parse_date(allocation.start_date, "allocation.start_date")
            allocation_end = parse_date(allocation.end_date, "allocation.end_date")
            if allocation_start < start or allocation_end > end:
                raise DomainValidationError("allocations must stay inside the plan period")
            expected_start = start if index == 0 else previous_end + timedelta(days=1)
            if allocation_start != expected_start:
                raise DomainValidationError("allocations must cover the full plan period without gaps")
            previous_end = allocation_end
        if previous_end != end:
            raise DomainValidationError("allocations must cover the full plan period without gaps")
        expense_ids = [item.planned_expense_id for item in self.planned_expenses]
        if len(expense_ids) != len(set(expense_ids)):
            raise DomainValidationError("planned expense ids must be unique")
        for expense in self.planned_expenses:
            due = parse_date(expense.due_date, "planned_expense.due_date")
            if not start <= due <= end:
                raise DomainValidationError("planned expense due_date must be inside the plan period")
        if self.schema_version != SCHEMA_VERSION:
            raise DomainValidationError("unsupported plan schema_version")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> SpendingPlan:
        return cls(
            plan_id=str(payload["plan_id"]),
            user_ref=str(payload["user_ref"]),
            period_start=str(payload["period_start"]),
            period_end=str(payload["period_end"]),
            confirmed_budget_krw=int(payload["confirmed_budget_krw"]),
            priorities=[PlanPriority.from_dict(item) for item in payload.get("priorities", [])],
            allocations=[PlanAllocation.from_dict(item) for item in payload.get("allocations", [])],
            planned_expenses=[PlannedExpense.from_dict(item) for item in payload.get("planned_expenses", [])],
            status=str(payload.get("status", "active")),
            version=int(payload.get("version", 1)),
            confirmed_at=payload.get("confirmed_at"),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            narrative=(
                dict(payload["narrative"])
                if isinstance(payload.get("narrative"), Mapping)
                else None
            ),
            revisions=[PlanRevision.from_dict(item) for item in payload.get("revisions", [])],
            check_ins=[PlanCheckIn.from_dict(item) for item in payload.get("check_ins", [])],
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["priorities"] = [item.to_dict() for item in self.priorities]
        payload["allocations"] = [item.to_dict() for item in self.allocations]
        payload["planned_expenses"] = [item.to_dict() for item in self.planned_expenses]
        payload["revisions"] = [item.to_dict() for item in self.revisions]
        payload["check_ins"] = [item.to_dict() for item in self.check_ins]
        return payload

    def snapshot(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("revisions", None)
        payload.pop("check_ins", None)
        return payload


def default_allocations(period_start: str, period_end: str, budget_krw: int) -> list[PlanAllocation]:
    start = parse_date(period_start, "period_start")
    end = parse_date(period_end, "period_end")
    require_positive_int(budget_krw, "confirmed_budget_krw")
    ranges: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        segment_end = min(end, cursor + timedelta(days=6 - cursor.weekday()))
        ranges.append((cursor, segment_end))
        cursor = segment_end + timedelta(days=1)
    base, remainder = divmod(budget_krw, len(ranges))
    return [
        PlanAllocation(
            allocation_id=f"segment-{index + 1}",
            label=f"{index + 1}주차",
            start_date=segment_start.isoformat(),
            end_date=segment_end.isoformat(),
            amount_krw=base + (1 if index < remainder else 0),
        )
        for index, (segment_start, segment_end) in enumerate(ranges)
    ]


def compute_plan_progress(
    plan: SpendingPlan,
    transactions: Sequence[Transaction],
    *,
    timezone_name: str,
    as_of: date,
) -> dict[str, Any]:
    try:
        local_timezone = ZoneInfo(timezone_name)
    except Exception as exc:
        raise DomainValidationError("unsupported timezone") from exc
    period_start = parse_date(plan.period_start, "plan.period_start")
    period_end = parse_date(plan.period_end, "plan.period_end")
    eligible: list[tuple[Transaction, date]] = []
    for transaction in transactions:
        if transaction.transaction_type != "expense" or transaction.exclude_from_budget:
            continue
        local_date = parse_utc_datetime(transaction.occurred_at, "occurred_at").astimezone(local_timezone).date()
        if period_start <= local_date <= period_end:
            eligible.append((transaction, local_date))
    actual_spent = sum(item.amount_krw for item, _ in eligible)
    reserved_remaining = sum(
        item.amount_krw for item in plan.planned_expenses if item.matched_transaction_id is None
    )
    total_remaining = plan.confirmed_budget_krw - actual_spent
    flexible_remaining = total_remaining - reserved_remaining
    segments = []
    current_segment_id: str | None = None
    for allocation in plan.allocations:
        segment_start = parse_date(allocation.start_date, "allocation.start_date")
        segment_end = parse_date(allocation.end_date, "allocation.end_date")
        spent = sum(item.amount_krw for item, local_date in eligible if segment_start <= local_date <= segment_end)
        reserved = sum(
            item.amount_krw
            for item in plan.planned_expenses
            if item.matched_transaction_id is None and segment_start <= parse_date(item.due_date, "due_date") <= segment_end
        )
        if segment_start <= as_of <= segment_end:
            current_segment_id = allocation.allocation_id
        segments.append(
            {
                **allocation.to_dict(),
                "actual_spent_krw": spent,
                "reserved_remaining_krw": reserved,
                "total_remaining_krw": allocation.amount_krw - spent,
                "flexible_remaining_krw": allocation.amount_krw - spent - reserved,
            }
        )
    latest_input_at = max((item.occurred_at for item, _ in eligible), default=None)
    return {
        "period_start": plan.period_start,
        "period_end": plan.period_end,
        "confirmed_budget_krw": plan.confirmed_budget_krw,
        "actual_spent_krw": actual_spent,
        "reserved_remaining_krw": reserved_remaining,
        "total_remaining_krw": total_remaining,
        "flexible_remaining_krw": flexible_remaining,
        "shortfall_krw": abs(min(0, flexible_remaining)),
        "segments": segments,
        "current_segment_id": current_segment_id,
        "latest_input_at": latest_input_at,
    }
