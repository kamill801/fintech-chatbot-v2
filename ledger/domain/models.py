from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any, ClassVar, Mapping


SCHEMA_VERSION = 1

ALLOWED_TRANSACTION_SOURCES = frozenset(
    {"manual", "synthetic", "provider_readonly", "legacy"}
)
ALLOWED_TRANSACTION_STATUSES = frozenset(
    {"recorded", "awaiting_reason", "judged", "corrected"}
)
ALLOWED_TRANSACTION_TYPES = frozenset({"expense", "income", "transfer"})
ALLOWED_ACCOUNT_TYPES = frozenset({"cash", "bank", "card", "savings", "other"})
ALLOWED_JUDGMENT_LABELS = frozenset(
    {"justified", "caution", "overspending", "insufficient_context"}
)
ALLOWED_SPENDING_REFLECTIONS = frozenset({"well_spent", "unsure", "regretted"})


class DomainValidationError(ValueError):
    """Raised when a domain object violates the TECHSPEC contract."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc_datetime(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise DomainValidationError(f"{field_name} must be a UTC timestamp string")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DomainValidationError(f"{field_name} must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise DomainValidationError(f"{field_name} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def parse_date(value: str, field_name: str) -> date:
    if not isinstance(value, str) or not value:
        raise DomainValidationError(f"{field_name} must be a date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DomainValidationError(f"{field_name} must be ISO 8601 date") from exc


def require_non_negative_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise DomainValidationError(f"{field_name} must be a non-negative integer")


def require_positive_int(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DomainValidationError(f"{field_name} must be a positive integer")


def require_ratio(value: float | int, field_name: str) -> None:
    if not isinstance(value, (float, int)) or isinstance(value, bool):
        raise DomainValidationError(f"{field_name} must be a number")
    if not 0 <= float(value) <= 1:
        raise DomainValidationError(f"{field_name} must be between 0 and 1")


@dataclass(frozen=True)
class FinancialGoal:
    goal_id: str
    name: str
    target_amount_krw: int
    current_amount_krw: int
    target_date: str

    def __post_init__(self) -> None:
        if not self.goal_id:
            raise DomainValidationError("goal_id is required")
        if not self.name:
            raise DomainValidationError("goal.name is required")
        require_non_negative_int(self.target_amount_krw, "goal.target_amount_krw")
        require_non_negative_int(self.current_amount_krw, "goal.current_amount_krw")
        if self.target_amount_krw < self.current_amount_krw:
            raise DomainValidationError(
                "goal.target_amount_krw must exceed or equal current_amount_krw"
            )
        parse_date(self.target_date, "goal.target_date")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FinancialGoal:
        return cls(
            goal_id=str(payload["goal_id"]),
            name=str(payload["name"]),
            target_amount_krw=int(payload["target_amount_krw"]),
            current_amount_krw=int(payload["current_amount_krw"]),
            target_date=str(payload["target_date"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinancialProfile:
    user_ref: str
    monthly_income_krw: int
    liquid_assets_krw: int
    fixed_expenses_krw: int
    monthly_debt_payment_krw: int
    discretionary_budget_krw: int
    goal: FinancialGoal
    created_at: str
    updated_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.user_ref:
            raise DomainValidationError("user_ref is required")
        require_non_negative_int(self.monthly_income_krw, "monthly_income_krw")
        require_non_negative_int(self.liquid_assets_krw, "liquid_assets_krw")
        require_non_negative_int(self.fixed_expenses_krw, "fixed_expenses_krw")
        require_non_negative_int(
            self.monthly_debt_payment_krw, "monthly_debt_payment_krw"
        )
        require_positive_int(self.discretionary_budget_krw, "discretionary_budget_krw")
        parse_utc_datetime(self.created_at, "created_at")
        parse_utc_datetime(self.updated_at, "updated_at")
        if self.schema_version != SCHEMA_VERSION:
            raise DomainValidationError("unsupported profile schema_version")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FinancialProfile:
        return cls(
            user_ref=str(payload["user_ref"]),
            monthly_income_krw=int(payload["monthly_income_krw"]),
            liquid_assets_krw=int(payload["liquid_assets_krw"]),
            fixed_expenses_krw=int(payload["fixed_expenses_krw"]),
            monthly_debt_payment_krw=int(payload["monthly_debt_payment_krw"]),
            discretionary_budget_krw=int(payload["discretionary_budget_krw"]),
            goal=FinancialGoal.from_dict(payload["goal"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["goal"] = self.goal.to_dict()
        return payload


@dataclass(frozen=True)
class LedgerAccount:
    account_id: str
    name: str
    account_type: str
    opening_balance_krw: int = 0
    archived: bool = False

    def __post_init__(self) -> None:
        if not self.account_id or len(self.account_id) > 64:
            raise DomainValidationError("account_id must be 1 to 64 characters")
        if not self.name or len(self.name) > 40:
            raise DomainValidationError("account name must be 1 to 40 characters")
        if self.account_type not in ALLOWED_ACCOUNT_TYPES:
            raise DomainValidationError("unsupported account_type")
        require_non_negative_int(self.opening_balance_krw, "opening_balance_krw")
        if not isinstance(self.archived, bool):
            raise DomainValidationError("archived must be boolean")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LedgerAccount:
        return cls(
            account_id=str(payload["account_id"]),
            name=str(payload["name"]),
            account_type=str(payload.get("account_type", "other")),
            opening_balance_krw=int(payload.get("opening_balance_krw", 0)),
            archived=payload.get("archived", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_ledger_accounts() -> list[LedgerAccount]:
    return [LedgerAccount(account_id="cash", name="현금", account_type="cash")]


@dataclass(frozen=True)
class UserSettings:
    roast_enabled: bool = False
    locale: str = "ko-KR"
    timezone: str = "Asia/Seoul"
    spending_rules: list[str] = field(default_factory=list)
    accounts: list[LedgerAccount] = field(default_factory=default_ledger_accounts)
    category_budgets_krw: dict[str, int] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.roast_enabled, bool):
            raise DomainValidationError("roast_enabled must be boolean")
        if not self.locale:
            raise DomainValidationError("locale is required")
        if not self.timezone:
            raise DomainValidationError("timezone is required")
        if not isinstance(self.spending_rules, list) or len(self.spending_rules) > 8:
            raise DomainValidationError("spending_rules must contain at most 8 items")
        if any(not rule or len(rule) > 120 for rule in self.spending_rules):
            raise DomainValidationError("each spending rule must be 1 to 120 characters")
        if not isinstance(self.accounts, list) or not 1 <= len(self.accounts) <= 20:
            raise DomainValidationError("accounts must contain 1 to 20 items")
        account_ids = [account.account_id for account in self.accounts]
        if len(account_ids) != len(set(account_ids)):
            raise DomainValidationError("account_id values must be unique")
        if not isinstance(self.category_budgets_krw, dict):
            raise DomainValidationError("category_budgets_krw must be an object")
        for category, budget in self.category_budgets_krw.items():
            if not category or len(category) > 40:
                raise DomainValidationError("budget category must be 1 to 40 characters")
            require_positive_int(budget, f"category_budgets_krw.{category}")
        if self.schema_version != SCHEMA_VERSION:
            raise DomainValidationError("unsupported settings schema_version")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> UserSettings:
        raw_accounts = payload.get("accounts")
        accounts = (
            default_ledger_accounts()
            if raw_accounts is None
            else [LedgerAccount.from_dict(item) for item in raw_accounts]
        )
        return cls(
            roast_enabled=payload.get("roast_enabled", False),
            locale=str(payload.get("locale", "ko-KR")),
            timezone=str(payload.get("timezone", "Asia/Seoul")),
            spending_rules=[str(rule) for rule in payload.get("spending_rules", [])],
            accounts=accounts,
            category_budgets_krw={
                str(category): int(budget)
                for category, budget in dict(payload.get("category_budgets_krw", {})).items()
            },
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    user_ref: str
    amount_krw: int
    merchant: str | None
    category: str
    description: str | None
    occurred_at: str
    source: str
    source_reference: str | None
    reason: str | None
    status: str
    created_at: str
    reflection: str | None = None
    reflection_note: str | None = None
    reflected_at: str | None = None
    transaction_type: str = "expense"
    account_id: str = "cash"
    destination_account_id: str | None = None
    exclude_from_budget: bool = False
    updated_at: str | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.transaction_id:
            raise DomainValidationError("transaction_id is required")
        if not self.user_ref:
            raise DomainValidationError("user_ref is required")
        require_non_negative_int(self.amount_krw, "amount_krw")
        if not self.category:
            raise DomainValidationError("category is required")
        parse_utc_datetime(self.occurred_at, "occurred_at")
        parse_utc_datetime(self.created_at, "created_at")
        if self.source not in ALLOWED_TRANSACTION_SOURCES:
            raise DomainValidationError("unsupported transaction source")
        if self.status not in ALLOWED_TRANSACTION_STATUSES:
            raise DomainValidationError("unsupported transaction status")
        if self.transaction_type not in ALLOWED_TRANSACTION_TYPES:
            raise DomainValidationError("unsupported transaction_type")
        if not self.account_id:
            raise DomainValidationError("account_id is required")
        if self.transaction_type == "transfer":
            if not self.destination_account_id:
                raise DomainValidationError("destination_account_id is required for transfer")
            if self.destination_account_id == self.account_id:
                raise DomainValidationError("transfer accounts must be different")
        elif self.destination_account_id is not None:
            raise DomainValidationError("destination_account_id is only valid for transfer")
        if not isinstance(self.exclude_from_budget, bool):
            raise DomainValidationError("exclude_from_budget must be boolean")
        if self.transaction_type != "expense" and self.exclude_from_budget:
            raise DomainValidationError("only expenses can be excluded from budget")
        if self.transaction_type != "expense" and self.reflection is not None:
            raise DomainValidationError("only expenses can have a spending reflection")
        if self.reflection is not None and self.reflection not in ALLOWED_SPENDING_REFLECTIONS:
            raise DomainValidationError("unsupported spending reflection")
        if self.reflected_at is not None:
            parse_utc_datetime(self.reflected_at, "reflected_at")
        if self.updated_at is not None:
            parse_utc_datetime(self.updated_at, "updated_at")
        if self.schema_version != SCHEMA_VERSION:
            raise DomainValidationError("unsupported transaction schema_version")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Transaction:
        return cls(
            transaction_id=str(payload["transaction_id"]),
            user_ref=str(payload["user_ref"]),
            amount_krw=int(payload["amount_krw"]),
            merchant=payload.get("merchant"),
            category=str(payload["category"]),
            description=payload.get("description"),
            occurred_at=str(payload["occurred_at"]),
            source=str(payload["source"]),
            source_reference=payload.get("source_reference"),
            reason=payload.get("reason"),
            status=str(payload["status"]),
            created_at=str(payload["created_at"]),
            reflection=payload.get("reflection"),
            reflection_note=payload.get("reflection_note"),
            reflected_at=payload.get("reflected_at"),
            transaction_type=str(payload.get("transaction_type", "expense")),
            account_id=str(payload.get("account_id", "cash")),
            destination_account_id=payload.get("destination_account_id"),
            exclude_from_budget=payload.get("exclude_from_budget", False),
            updated_at=payload.get("updated_at"),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DeterministicSignalSet:
    budget_usage_after: float
    transaction_budget_share: float
    goal_pressure: float
    baseline_deviation: float
    recurrence_30d: int
    essentiality: float
    risk_score: float
    data_confidence: float
    requires_reason: bool
    factors: list[str] = field(default_factory=list)

    RATIO_FIELDS: ClassVar[tuple[str, ...]] = (
        "budget_usage_after",
        "transaction_budget_share",
        "goal_pressure",
        "essentiality",
        "risk_score",
        "data_confidence",
    )

    def __post_init__(self) -> None:
        for field_name in self.RATIO_FIELDS:
            require_ratio(getattr(self, field_name), field_name)
        if not isinstance(self.baseline_deviation, (float, int)):
            raise DomainValidationError("baseline_deviation must be a number")
        require_non_negative_int(self.recurrence_30d, "recurrence_30d")
        if not isinstance(self.requires_reason, bool):
            raise DomainValidationError("requires_reason must be boolean")
        if not all(isinstance(factor, str) and factor for factor in self.factors):
            raise DomainValidationError("factors must be non-empty strings")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> DeterministicSignalSet:
        return cls(
            budget_usage_after=float(payload["budget_usage_after"]),
            transaction_budget_share=float(payload["transaction_budget_share"]),
            goal_pressure=float(payload["goal_pressure"]),
            baseline_deviation=float(payload["baseline_deviation"]),
            recurrence_30d=int(payload["recurrence_30d"]),
            essentiality=float(payload["essentiality"]),
            risk_score=float(payload["risk_score"]),
            data_confidence=float(payload["data_confidence"]),
            requires_reason=bool(payload["requires_reason"]),
            factors=list(payload.get("factors", [])),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JudgmentResult:
    judgment_id: str
    transaction_id: str
    label: str
    confidence: float
    rationale: str
    recommended_action: str
    decision_factors: list[str]
    normal_message: str
    roast_message: str
    fallback_used: bool
    model: str
    policy_version: str
    created_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.judgment_id:
            raise DomainValidationError("judgment_id is required")
        if not self.transaction_id:
            raise DomainValidationError("transaction_id is required")
        if self.label not in ALLOWED_JUDGMENT_LABELS:
            raise DomainValidationError("unsupported judgment label")
        require_ratio(self.confidence, "confidence")
        if not self.rationale:
            raise DomainValidationError("rationale is required")
        if not self.recommended_action:
            raise DomainValidationError("recommended_action is required")
        if not self.normal_message:
            raise DomainValidationError("normal_message is required")
        if not self.roast_message:
            raise DomainValidationError("roast_message is required")
        if not isinstance(self.fallback_used, bool):
            raise DomainValidationError("fallback_used must be boolean")
        if not self.model:
            raise DomainValidationError("model is required")
        if not self.policy_version:
            raise DomainValidationError("policy_version is required")
        if not all(isinstance(factor, str) and factor for factor in self.decision_factors):
            raise DomainValidationError("decision_factors must be non-empty strings")
        parse_utc_datetime(self.created_at, "created_at")
        if self.schema_version != SCHEMA_VERSION:
            raise DomainValidationError("unsupported judgment schema_version")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> JudgmentResult:
        return cls(
            judgment_id=str(payload["judgment_id"]),
            transaction_id=str(payload["transaction_id"]),
            label=str(payload["label"]),
            confidence=float(payload["confidence"]),
            rationale=str(payload["rationale"]),
            recommended_action=str(payload["recommended_action"]),
            decision_factors=list(payload["decision_factors"]),
            normal_message=str(payload["normal_message"]),
            roast_message=str(payload["roast_message"]),
            fallback_used=bool(payload["fallback_used"]),
            model=str(payload["model"]),
            policy_version=str(payload["policy_version"]),
            created_at=str(payload["created_at"]),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JudgmentCorrection:
    judgment_id: str
    original_label: str
    corrected_label: str
    correction_reason: str | None
    corrected_at: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.judgment_id:
            raise DomainValidationError("judgment_id is required")
        if self.original_label not in ALLOWED_JUDGMENT_LABELS:
            raise DomainValidationError("unsupported original_label")
        if self.corrected_label not in ALLOWED_JUDGMENT_LABELS:
            raise DomainValidationError("unsupported corrected_label")
        parse_utc_datetime(self.corrected_at, "corrected_at")
        if self.schema_version != SCHEMA_VERSION:
            raise DomainValidationError("unsupported correction schema_version")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> JudgmentCorrection:
        return cls(
            judgment_id=str(payload["judgment_id"]),
            original_label=str(payload["original_label"]),
            corrected_label=str(payload["corrected_label"]),
            correction_reason=payload.get("correction_reason"),
            corrected_at=str(payload["corrected_at"]),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PendingQuestion:
    question_id: str
    transaction_id: str
    question: str
    asked_at: str
    answered_at: str | None = None
    attempt_count: int = 0

    def __post_init__(self) -> None:
        if not self.question_id:
            raise DomainValidationError("question_id is required")
        if not self.transaction_id:
            raise DomainValidationError("transaction_id is required")
        if not self.question:
            raise DomainValidationError("question is required")
        parse_utc_datetime(self.asked_at, "asked_at")
        if self.answered_at is not None:
            parse_utc_datetime(self.answered_at, "answered_at")
        require_non_negative_int(self.attempt_count, "attempt_count")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> PendingQuestion:
        return cls(
            question_id=str(payload["question_id"]),
            transaction_id=str(payload["transaction_id"]),
            question=str(payload["question"]),
            asked_at=str(payload["asked_at"]),
            answered_at=payload.get("answered_at"),
            attempt_count=int(payload.get("attempt_count", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
