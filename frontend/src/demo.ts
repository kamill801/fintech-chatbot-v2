import type {
  Judgment,
  PendingQuestion,
  Profile,
  Settings,
  Signals,
  Summary,
  Transaction,
} from "./types";

export const demoProfile: Profile = {
  monthly_income_krw: 3_500_000,
  liquid_assets_krw: 10_000_000,
  fixed_expenses_krw: 1_400_000,
  monthly_debt_payment_krw: 300_000,
  discretionary_budget_krw: 800_000,
  goal: {
    goal_id: "goal-demo",
    name: "비상금",
    target_amount_krw: 10_000_000,
    current_amount_krw: 3_000_000,
    target_date: "2027-08-03",
  },
};

export const demoSettings: Settings = {
  roast_enabled: false,
  locale: "ko-KR",
  timezone: "Asia/Seoul",
};

export const demoTransactions: Transaction[] = [
  {
    transaction_id: "tx-cafe",
    amount_krw: 12_000,
    merchant: "카페 온도",
    category: "cafe",
    description: null,
    occurred_at: "2026-08-03T02:45:00Z",
    source: "manual",
    source_reference: null,
    reason: "친구와 오랜만에 만나서 이야기할 곳이 필요했어.",
    status: "judged",
    created_at: "2026-08-03T02:45:00Z",
  },
  {
    transaction_id: "tx-lunch",
    amount_krw: 9_000,
    merchant: "점심",
    category: "food",
    description: null,
    occurred_at: "2026-08-03T03:34:00Z",
    source: "manual",
    source_reference: null,
    reason: null,
    status: "judged",
    created_at: "2026-08-03T03:34:00Z",
  },
  {
    transaction_id: "tx-transit",
    amount_krw: 1_500,
    merchant: "교통카드",
    category: "transport",
    description: null,
    occurred_at: "2026-08-03T00:22:00Z",
    source: "manual",
    source_reference: null,
    reason: null,
    status: "judged",
    created_at: "2026-08-03T00:22:00Z",
  },
  {
    transaction_id: "tx-grocery",
    amount_krw: 64_000,
    merchant: "마켓컬리",
    category: "food",
    description: "주간 장보기",
    occurred_at: "2026-08-02T09:20:00Z",
    source: "manual",
    source_reference: null,
    reason: "일주일 식재료",
    status: "judged",
    created_at: "2026-08-02T09:20:00Z",
  },
  {
    transaction_id: "tx-store",
    amount_krw: 18_500,
    merchant: "편의점",
    category: "shopping",
    description: null,
    occurred_at: "2026-08-01T12:10:00Z",
    source: "manual",
    source_reference: null,
    reason: null,
    status: "judged",
    created_at: "2026-08-01T12:10:00Z",
  },
];

export const demoSignals: Signals = {
  budget_usage_after: 0.62,
  transaction_budget_share: 0.015,
  goal_pressure: 0.7,
  baseline_deviation: 1.4,
  recurrence_30d: 3,
  essentiality: 0.2,
  risk_score: 0.66,
  data_confidence: 0.81,
  requires_reason: true,
  factors: ["budget_usage", "recurrence", "user_reason"],
};

export const demoPending: PendingQuestion = {
  question_id: "question-cafe",
  transaction_id: "tx-cafe",
  question: "이 지출이 꼭 필요했던 이유가 뭐야?",
  asked_at: "2026-08-03T02:45:00Z",
  answered_at: null,
  attempt_count: 0,
};

export function demoJudgment(roast: boolean): Judgment {
  return {
    judgment_id: "judgment-cafe",
    transaction_id: "tx-cafe",
    mode: roast ? "roast" : "normal",
    label: "caution",
    confidence: 0.81,
    rationale: "필요한 만남이었지만 이번 주 카페 지출이 세 번째예요.",
    recommended_action: "이번 주 카페는 여기까지. 다음 만남은 산책으로 바꿔요.",
    message: roast
      ? "아이고 이 화상아, 친구 만난 건 좋다만 이번 주 카페가 벌써 세 번째다. 이번 주 카페는 여기까지 하고, 다음 약속은 산책으로 돌려서 지갑도 숨 좀 쉬자."
      : "필요했지만, 이번 주는 여기까지.",
    fallback_used: false,
    model: "demo-artifact",
    policy_version: "overspending-v1",
    original_label: "caution",
    effective_label: "caution",
    correction: null,
  };
}

export const demoSummary: Summary = {
  month: "2026-08",
  total_spent_krw: 377_500,
  by_category_krw: {
    food: 160_000,
    shopping: 95_000,
    cafe: 72_000,
    transport: 50_500,
  },
  transaction_count: 14,
  discretionary_budget_krw: 800_000,
  budget_usage: 0.4719,
  goal: demoProfile.goal,
};
