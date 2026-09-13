import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { ledgerApi, ApiError } from "./api";
import { useAuth } from "./auth-context";
import {
  demoJudgment,
  demoPlanState,
  demoPending,
  demoProfile,
  demoSettings,
  demoSignals,
  demoSummary,
  demoTransactions,
} from "./demo";
import { clearFinancialDrafts } from "./local-drafts";
import { createClientId } from "./utils";
import type {
  Correction,
  JudgmentLabel,
  Profile,
  Settings,
  Summary,
  Transaction,
  TransactionDetail,
  TransactionDraft,
  TransactionResult,
  SpendingReflection,
  PlanDraft,
  PlanImpact,
  PlanRevisionPreview,
  SpendingPlanState,
} from "./types";

interface LedgerContextValue {
  profile: Profile | null;
  settings: Settings;
  transactions: Transaction[];
  summary: Summary | null;
  plan: SpendingPlanState | null;
  latestPlanImpact: PlanImpact | null;
  loading: boolean;
  error: string | null;
  profileLoadError: string | null;
  demo: boolean;
  refresh(): Promise<void>;
  saveProfile(profile: Profile): Promise<void>;
  saveSettings(patch: Partial<Settings>): Promise<void>;
  createTransaction(draft: TransactionDraft, operationId?: string): Promise<TransactionResult>;
  updateTransaction(id: string, draft: Partial<TransactionDraft>): Promise<TransactionResult>;
  deleteTransaction(id: string): Promise<void>;
  answerReason(id: string, reason: string): Promise<TransactionResult>;
  reflectTransaction(id: string, reflection: SpendingReflection, note: string): Promise<Transaction>;
  getTransaction(id: string): Promise<TransactionDetail>;
  correctJudgment(
    id: string,
    label: JudgmentLabel,
    reason: string,
  ): Promise<Correction>;
  recordShareView(id: string): Promise<void>;
  recordShareSuccess(id: string): Promise<void>;
  deleteData(): Promise<void>;
  previewPlan(draft: PlanDraft): Promise<SpendingPlanState>;
  activatePlan(draft: PlanDraft): Promise<SpendingPlanState>;
  previewPlanRevision(draft: PlanDraft, reason: string): Promise<PlanRevisionPreview>;
  applyPlanRevision(draft: PlanDraft, reason: string): Promise<SpendingPlanState>;
  checkInPlan(decision: "maintain" | "adjust", note?: string): Promise<SpendingPlanState>;
  matchPlannedExpense(plannedExpenseId: string, transactionId: string): Promise<SpendingPlanState>;
}

const LedgerContext = createContext<LedgerContextValue | null>(null);

const initialSettings: Settings = {
  roast_enabled: false,
  locale: "ko-KR",
  timezone: "Asia/Seoul",
  spending_rules: [],
  accounts: [{ account_id: "cash", name: "현금", account_type: "cash", opening_balance_krw: 0, archived: false }],
  category_budgets_krw: {},
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "잠시 후 다시 시도해 주세요.";
}

function previewDemoPlan(draft: PlanDraft): SpendingPlanState {
  const reserved = draft.planned_expenses.reduce((sum, item) => sum + item.amount_krw, 0);
  return {
    ...demoPlanState,
    preview: true,
    plan: {
      ...demoPlanState.plan,
      period_start: draft.period_start,
      period_end: draft.period_end,
      confirmed_budget_krw: draft.confirmed_budget_krw,
      priorities: draft.priorities.map((item, index) => typeof item === "string" ? { priority_id: `priority-${index + 1}`, name: item, rank: index + 1 } : item),
      planned_expenses: draft.planned_expenses.map((item, index) => ({ ...item, planned_expense_id: item.planned_expense_id ?? `planned-${index + 1}`, matched_transaction_id: null, matched_at: null })),
    },
    progress: {
      ...demoPlanState.progress,
      period_start: draft.period_start,
      period_end: draft.period_end,
      confirmed_budget_krw: draft.confirmed_budget_krw,
      reserved_remaining_krw: reserved,
      total_remaining_krw: draft.confirmed_budget_krw,
      flexible_remaining_krw: draft.confirmed_budget_krw - reserved,
      shortfall_krw: Math.max(0, reserved - draft.confirmed_budget_krw),
    },
  };
}

export function LedgerProvider({ children }: { children: ReactNode }) {
  const { userKey } = useAuth();
  const initialQuery = new URLSearchParams(window.location.search);
  const demo =
    initialQuery.get("demo") === "1" ||
    import.meta.env.VITE_DEMO_DEFAULT === "1";
  const demoRoast = initialQuery.get("roast") === "1";
  const [profile, setProfile] = useState<Profile | null>(demo ? demoProfile : null);
  const [settings, setSettings] = useState<Settings>(demo ? { ...demoSettings, roast_enabled: demoRoast } : initialSettings);
  const [transactions, setTransactions] = useState<Transaction[]>(demo ? demoTransactions : []);
  const [summary, setSummary] = useState<Summary | null>(demo ? demoSummary : null);
  const [plan, setPlan] = useState<SpendingPlanState | null>(demo ? demoPlanState : null);
  const [latestPlanImpact, setLatestPlanImpact] = useState<PlanImpact | null>(null);
  const [loading, setLoading] = useState(!demo);
  const [error, setError] = useState<string | null>(null);
  const [profileLoadError, setProfileLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (demo) return;
    setLoading(true);
    setError(null);
    setProfileLoadError(null);
    try {
      let nextProfile: Profile | null;
      try {
        nextProfile = await ledgerApi.profile();
      } catch (nextError) {
        const message = errorMessage(nextError);
        setProfileLoadError(message);
        setError(message);
        return;
      }
      const [nextSettings, nextTransactions, nextSummary, nextPlan] = await Promise.all([
        ledgerApi.settings(),
        ledgerApi.transactions(),
        ledgerApi.summary(),
        ledgerApi.plan(),
      ]);
      setProfile(nextProfile);
      setSettings(nextSettings);
      setTransactions(nextTransactions);
      setSummary(nextSummary);
      setPlan(nextPlan);
    } catch (nextError) {
      const message = errorMessage(nextError);
      setProfileLoadError(message);
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [demo]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<LedgerContextValue>(
    () => ({
      profile,
      settings,
      transactions,
      summary,
      plan,
      latestPlanImpact,
      loading,
      error,
      profileLoadError,
      demo,
      refresh,
      async saveProfile(nextProfile) {
        setProfile(demo ? nextProfile : await ledgerApi.saveProfile(nextProfile));
        setProfileLoadError(null);
        if (!demo) setSummary(await ledgerApi.summary());
      },
      async saveSettings(patch) {
        const next = demo
          ? { ...settings, ...patch }
          : await ledgerApi.saveSettings(patch);
        setSettings(next);
      },
      async createTransaction(draft, operationId) {
        if (demo) {
          const transactionType = draft.transaction_type ?? "expense";
          const needsReason = transactionType === "expense" && settings.roast_enabled && !draft.reason;
          const transaction: Transaction = {
            transaction_id: `tx-${createClientId()}`,
            amount_krw: draft.amount_krw,
            merchant: draft.merchant ?? null,
            category: draft.category,
            description: draft.description ?? null,
            occurred_at: draft.occurred_at ?? new Date().toISOString(),
            source: "manual",
            source_reference: null,
            reason: draft.reason ?? null,
            status: needsReason ? "awaiting_reason" : transactionType === "expense" ? "judged" : "recorded",
            created_at: new Date().toISOString(),
            transaction_type: transactionType,
            account_id: draft.account_id ?? settings.accounts[0]?.account_id ?? "cash",
            destination_account_id: draft.destination_account_id ?? null,
            exclude_from_budget: draft.exclude_from_budget ?? false,
          };
          setTransactions((items) => [transaction, ...items]);
          if (transactionType === "expense" && plan && !transaction.exclude_from_budget) {
            const totalRemaining = plan.progress.total_remaining_krw - transaction.amount_krw;
            const flexibleRemaining = plan.progress.flexible_remaining_krw - transaction.amount_krw;
            const impact = {
              transaction_id: transaction.transaction_id,
              amount_krw: transaction.amount_krw,
              total_remaining_krw: totalRemaining,
              reserved_remaining_krw: plan.progress.reserved_remaining_krw,
              flexible_remaining_krw: flexibleRemaining,
              shortfall_krw: Math.max(0, -flexibleRemaining),
              message: flexibleRemaining < 0 ? `계획상 생활비가 ${Math.abs(flexibleRemaining).toLocaleString("ko-KR")}원 부족해졌어요.` : `계획상 쓸 수 있는 생활비가 ${flexibleRemaining.toLocaleString("ko-KR")}원 남았어요.`,
            };
            setLatestPlanImpact(impact);
            setPlan({ ...plan, progress: { ...plan.progress, actual_spent_krw: plan.progress.actual_spent_krw + transaction.amount_krw, total_remaining_krw: totalRemaining, flexible_remaining_krw: flexibleRemaining, shortfall_krw: impact.shortfall_krw } });
          }
          if (transactionType !== "expense") return { transaction };
          return needsReason
            ? { transaction, signals: demoSignals, pending_question: { ...demoPending, transaction_id: transaction.transaction_id } }
            : { transaction, signals: demoSignals, judgment: demoJudgment(settings.roast_enabled) };
        }
        const result = await ledgerApi.createTransaction(draft, operationId);
        setTransactions((items) => [result.transaction, ...items]);
        setLatestPlanImpact(result.plan_impact ?? null);
        setSummary(await ledgerApi.summary());
        setPlan(await ledgerApi.plan());
        return result;
      },
      async updateTransaction(id, draft) {
        if (demo) {
          const current = transactions.find((item) => item.transaction_id === id) ?? demoTransactions[0];
          const updated: Transaction = {
            ...current,
            ...draft,
            merchant: draft.merchant ?? current.merchant,
            description: draft.description ?? current.description,
            destination_account_id:
              draft.destination_account_id === undefined
                ? current.destination_account_id
                : draft.destination_account_id,
            updated_at: new Date().toISOString(),
          };
          setTransactions((items) => items.map((item) => (item.transaction_id === id ? updated : item)));
          return { transaction: updated, judgment: updated.transaction_type === "expense" ? demoJudgment(settings.roast_enabled) : undefined };
        }
        const result = await ledgerApi.updateTransaction(id, draft);
        setTransactions((items) => items.map((item) => (item.transaction_id === id ? result.transaction : item)));
        setSummary(await ledgerApi.summary());
        return result;
      },
      async deleteTransaction(id) {
        if (!demo) await ledgerApi.deleteTransaction(id);
        setTransactions((items) => items.filter((item) => item.transaction_id !== id));
        if (!demo) setSummary(await ledgerApi.summary());
      },
      async answerReason(id, reason) {
        if (demo) {
          const transaction = transactions.find((item) => item.transaction_id === id) ?? demoTransactions[0];
          const updated = { ...transaction, reason, status: "judged" as const };
          setTransactions((items) => items.map((item) => (item.transaction_id === id ? updated : item)));
          return { transaction: updated, signals: demoSignals, judgment: demoJudgment(settings.roast_enabled) };
        }
        const result = await ledgerApi.answerReason(id, reason);
        setTransactions((items) => items.map((item) => (item.transaction_id === id ? result.transaction : item)));
        return result;
      },
      async reflectTransaction(id, reflection, note) {
        if (demo) {
          const reflected_at = new Date().toISOString();
          const current = transactions.find((item) => item.transaction_id === id) ?? demoTransactions[0];
          const updated = {
            ...current,
            reflection,
            reflection_note: note.trim() || null,
            reflected_at,
          };
          setTransactions((items) => items.map((item) => (item.transaction_id === id ? updated : item)));
          return updated;
        }
        const updated = await ledgerApi.reflectTransaction(id, reflection, note);
        setTransactions((items) => items.map((item) => (item.transaction_id === id ? updated : item)));
        setSummary(await ledgerApi.summary());
        return updated;
      },
      async getTransaction(id) {
        if (demo) {
          const transaction = transactions.find((item) => item.transaction_id === id) ?? demoTransactions[0];
          return {
            transaction,
            judgment: transaction.status === "judged" ? demoJudgment(settings.roast_enabled) : undefined,
            pending_question: transaction.status === "awaiting_reason" ? { ...demoPending, transaction_id: transaction.transaction_id } : undefined,
          };
        }
        return ledgerApi.transaction(id);
      },
      async correctJudgment(id, label, reason) {
        if (demo) {
          return {
            judgment_id: id,
            original_label: "caution",
            corrected_label: label,
            correction_reason: reason,
            corrected_at: new Date().toISOString(),
          };
        }
        return ledgerApi.correctJudgment(id, label, reason);
      },
      async recordShareView(id) {
        if (!demo) await ledgerApi.shareView(id);
      },
      async recordShareSuccess(id) {
        if (!demo) await ledgerApi.shareSuccess(id);
      },
      async deleteData() {
        if (!demo) await ledgerApi.deleteData();
        clearFinancialDrafts(userKey);
        setProfile(null);
        setTransactions([]);
        setSummary(null);
        setPlan(null);
        setLatestPlanImpact(null);
        setSettings(initialSettings);
        setProfileLoadError(null);
      },
      async previewPlan(draft) {
        return demo ? previewDemoPlan(draft) : ledgerApi.previewPlan(draft);
      },
      async activatePlan(draft) {
        const next = demo ? { ...previewDemoPlan(draft), preview: false } : await ledgerApi.activatePlan(draft);
        setPlan(next);
        return next;
      },
      async previewPlanRevision(draft, reason) {
        if (!plan) throw new Error("plan required");
        if (!demo) return (await ledgerApi.previewPlanRevision(draft, plan.plan.version, reason)).revision_preview;
        const preview = previewDemoPlan(draft);
        return {
          from_version: plan.plan.version,
          to_version: plan.plan.version + 1,
          before: plan.plan,
          after: { ...preview.plan, version: plan.plan.version + 1 },
          before_progress: plan.progress,
          after_progress: preview.progress,
          budget_change_krw: draft.confirmed_budget_krw - plan.plan.confirmed_budget_krw,
          flexible_remaining_change_krw: preview.progress.flexible_remaining_krw - plan.progress.flexible_remaining_krw,
          narrative: preview.narrative,
        };
      },
      async applyPlanRevision(draft, reason) {
        if (!plan) throw new Error("plan required");
        const next = demo
          ? { ...previewDemoPlan(draft), preview: false, plan: { ...previewDemoPlan(draft).plan, version: plan.plan.version + 1 } }
          : await ledgerApi.applyPlanRevision(draft, plan.plan.version, reason);
        setPlan(next);
        return next;
      },
      async checkInPlan(decision, note = "") {
        if (!plan) throw new Error("plan required");
        const next = demo
          ? { ...plan, plan: { ...plan.plan, check_ins: [...plan.plan.check_ins, { check_in_id: createClientId(), decision, note: note || null, checked_in_at: new Date().toISOString(), plan_version: plan.plan.version }] } }
          : await ledgerApi.checkInPlan(decision, note);
        setPlan(next);
        return next;
      },
      async matchPlannedExpense(plannedExpenseId, transactionId) {
        if (!plan) throw new Error("plan required");
        const expense = plan.plan.planned_expenses.find((item) => item.planned_expense_id === plannedExpenseId);
        const nextFlexibleRemaining = expense
          ? plan.progress.flexible_remaining_krw + expense.amount_krw
          : plan.progress.flexible_remaining_krw;
        const next = demo && expense
          ? {
              ...plan,
              plan: { ...plan.plan, planned_expenses: plan.plan.planned_expenses.map((item) => item.planned_expense_id === plannedExpenseId ? { ...item, matched_transaction_id: transactionId, matched_at: new Date().toISOString() } : item) },
              progress: { ...plan.progress, reserved_remaining_krw: plan.progress.reserved_remaining_krw - expense.amount_krw, flexible_remaining_krw: nextFlexibleRemaining, shortfall_krw: Math.max(0, -nextFlexibleRemaining) },
            }
          : await ledgerApi.matchPlannedExpense(plannedExpenseId, transactionId);
        setPlan(next);
        return next;
      },
    }),
    [demo, error, latestPlanImpact, loading, plan, profile, profileLoadError, refresh, settings, summary, transactions, userKey],
  );

  return <LedgerContext.Provider value={value}>{children}</LedgerContext.Provider>;
}

// The provider and hook intentionally share this module to keep the state contract private.
// eslint-disable-next-line react-refresh/only-export-components
export function useLedger(): LedgerContextValue {
  const context = useContext(LedgerContext);
  if (!context) throw new Error("useLedger must be used inside LedgerProvider");
  return context;
}
