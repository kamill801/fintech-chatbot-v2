export type JudgmentLabel =
  | "justified"
  | "caution"
  | "overspending"
  | "insufficient_context";

export interface Goal {
  goal_id: string;
  name: string;
  target_amount_krw: number;
  current_amount_krw: number;
  target_date: string;
}

export interface Profile {
  user_ref?: string;
  monthly_income_krw: number;
  liquid_assets_krw: number;
  fixed_expenses_krw: number;
  monthly_debt_payment_krw: number;
  discretionary_budget_krw: number;
  goal: Goal;
  created_at?: string;
  updated_at?: string;
}

export interface Settings {
  roast_enabled: boolean;
  locale: string;
  timezone: string;
  spending_rules?: string[];
  accounts: LedgerAccount[];
  category_budgets_krw: Record<string, number>;
}

export type TransactionType = "expense" | "income" | "transfer";
export type AccountType = "cash" | "bank" | "card" | "savings" | "other";

export interface LedgerAccount {
  account_id: string;
  name: string;
  account_type: AccountType;
  opening_balance_krw: number;
  archived: boolean;
}

export type SpendingReflection = "well_spent" | "unsure" | "regretted";

export interface Transaction {
  transaction_id: string;
  amount_krw: number;
  merchant: string | null;
  category: string;
  description: string | null;
  occurred_at: string;
  source: "manual" | "synthetic" | "provider_readonly" | "legacy";
  source_reference: string | null;
  reason: string | null;
  status: "recorded" | "awaiting_reason" | "judged" | "corrected";
  created_at: string;
  reflection?: SpendingReflection | null;
  reflection_note?: string | null;
  reflected_at?: string | null;
  transaction_type: TransactionType;
  account_id: string;
  destination_account_id: string | null;
  exclude_from_budget: boolean;
  updated_at?: string | null;
}

export interface Signals {
  budget_usage_after: number;
  transaction_budget_share: number;
  goal_pressure: number;
  baseline_deviation: number;
  recurrence_30d: number;
  essentiality: number;
  risk_score: number;
  data_confidence: number;
  requires_reason: boolean;
  factors: string[];
}

export interface PendingQuestion {
  question_id: string;
  transaction_id: string;
  question: string;
  asked_at: string;
  answered_at: string | null;
  attempt_count: number;
}

export interface Correction {
  judgment_id: string;
  original_label: JudgmentLabel;
  corrected_label: JudgmentLabel;
  correction_reason: string | null;
  corrected_at: string;
}

export interface Judgment {
  judgment_id: string;
  transaction_id: string;
  mode: "normal" | "roast";
  label: JudgmentLabel;
  confidence: number;
  rationale: string;
  recommended_action: string;
  message: string;
  fallback_used: boolean;
  model: string;
  policy_version: string;
  original_label?: JudgmentLabel;
  effective_label?: JudgmentLabel;
  correction?: Correction | null;
}

export interface TransactionDetail {
  transaction: Transaction;
  judgment?: Judgment;
  pending_question?: PendingQuestion;
}

export interface TransactionResult extends TransactionDetail {
  signals?: Signals;
  plan_impact?: PlanImpact;
}

export interface PlanImpact {
  transaction_id: string;
  amount_krw: number;
  total_remaining_krw: number;
  reserved_remaining_krw: number;
  flexible_remaining_krw: number;
  shortfall_krw: number;
  message: string;
}

export interface PlanPriority {
  priority_id: string;
  name: string;
  rank: number;
}

export interface PlanAllocation {
  allocation_id: string;
  label: string;
  start_date: string;
  end_date: string;
  amount_krw: number;
}

export interface PlannedExpense {
  planned_expense_id: string;
  name: string;
  amount_krw: number;
  due_date: string;
  category: string;
  matched_transaction_id: string | null;
  matched_at: string | null;
}

export interface PlanRevision {
  revision_id: string;
  from_version: number;
  to_version: number;
  reason: string | null;
  applied_at: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
}

export interface PlanCheckIn {
  check_in_id: string;
  decision: "maintain" | "adjust";
  note: string | null;
  checked_in_at: string;
  plan_version: number;
}

export interface SpendingPlan {
  plan_id: string;
  period_start: string;
  period_end: string;
  confirmed_budget_krw: number;
  priorities: PlanPriority[];
  allocations: PlanAllocation[];
  planned_expenses: PlannedExpense[];
  status: "draft" | "active";
  version: number;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
  narrative?: PlanNarrative | null;
  revisions: PlanRevision[];
  check_ins: PlanCheckIn[];
}

export type SpendingPlanSnapshot = Omit<SpendingPlan, "revisions" | "check_ins">;

export interface PlanSegmentProgress extends PlanAllocation {
  actual_spent_krw: number;
  reserved_remaining_krw: number;
  total_remaining_krw: number;
  flexible_remaining_krw: number;
}

export interface PlanProgress {
  period_start: string;
  period_end: string;
  confirmed_budget_krw: number;
  actual_spent_krw: number;
  reserved_remaining_krw: number;
  total_remaining_krw: number;
  flexible_remaining_krw: number;
  shortfall_krw: number;
  segments: PlanSegmentProgress[];
  current_segment_id: string | null;
  latest_input_at: string | null;
}

export interface PlanNarrative {
  headline: string;
  explanation: string;
  segment_focuses: Array<{ allocation_id: string; focus: string }>;
  next_action: string;
  assumptions: string[];
  confidence: "low" | "medium" | "high";
  fallback_used: boolean;
}

export interface SpendingPlanState {
  plan: SpendingPlan;
  original_plan: SpendingPlanSnapshot;
  progress: PlanProgress;
  next_action: string;
  narrative: PlanNarrative;
  preview?: boolean;
}

export interface PlanDraft {
  period_start: string;
  period_end: string;
  confirmed_budget_krw: number;
  priorities: Array<string | PlanPriority>;
  planned_expenses: Array<{
    planned_expense_id?: string;
    name: string;
    amount_krw: number;
    due_date: string;
    category: string;
  }>;
}

export interface PlanRevisionPreview {
  from_version: number;
  to_version: number;
  before: SpendingPlanSnapshot;
  after: SpendingPlanSnapshot;
  before_progress: PlanProgress;
  after_progress: PlanProgress;
  budget_change_krw: number;
  flexible_remaining_change_krw: number;
  narrative: PlanNarrative;
}

export interface WeeklyConcern {
  transaction_id: string;
  label: JudgmentLabel;
  category: string;
  merchant: string | null;
  amount_krw: number;
  rationale: string;
}

export interface WeeklyBriefing {
  period_start: string;
  period_end: string;
  total_spent_krw: number;
  transaction_count: number;
  top_category: string | null;
  top_category_spent_krw: number;
  judged_count: number;
  justified_count: number;
  caution_count: number;
  overspending_count: number;
  insufficient_context_count: number;
  headline: string;
  summary: string;
  improvement: string;
  concern: WeeklyConcern | null;
  evidence_state?: "learned" | "feedback_sparse" | "judgment_only" | "empty";
  regret_pattern?: {
    category: string;
    category_name: string;
    count: number;
    spent_krw: number;
  } | null;
  goal_impact_days?: number;
}

export interface ReflectionSummary {
  reflected_count: number;
  well_spent_count: number;
  unsure_count: number;
  regretted_count: number;
  regretted_spent_krw: number;
  regret_rate: number;
  strongest_regret_category: string | null;
  goal_delay_days: number;
}

export interface Summary {
  month: string;
  total_spent_krw: number;
  by_category_krw: Record<string, number>;
  transaction_count: number;
  budget_spent_krw?: number;
  total_income_krw?: number;
  net_cashflow_krw?: number;
  transfer_total_krw?: number;
  expense_count?: number;
  income_count?: number;
  transfer_count?: number;
  previous_month?: {
    month: string;
    total_spent_krw: number;
    change_krw: number;
    change_rate: number | null;
  };
  category_budgets?: Record<string, {
    budget_krw: number;
    spent_krw: number;
    remaining_krw: number;
    usage: number;
    daily_allowance_krw: number;
  }>;
  account_balances?: Array<LedgerAccount & { balance_krw: number }>;
  discretionary_budget_krw?: number;
  budget_usage?: number;
  goal?: Goal;
  weekly_briefing?: WeeklyBriefing;
  reflection_summary?: ReflectionSummary;
}

export interface SharePayload {
  label: JudgmentLabel;
  roast_message: string;
  category: string;
  recommended_action: string;
}

export interface TransactionDraft {
  amount_krw: number;
  category: string;
  merchant?: string;
  description?: string;
  occurred_at?: string;
  reason?: string;
  transaction_type?: TransactionType;
  account_id?: string;
  destination_account_id?: string | null;
  exclude_from_budget?: boolean;
}
