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
}

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
}

export interface Summary {
  month: string;
  total_spent_krw: number;
  by_category_krw: Record<string, number>;
  transaction_count: number;
  discretionary_budget_krw?: number;
  budget_usage?: number;
  goal?: Goal;
  weekly_briefing?: WeeklyBriefing;
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
}
