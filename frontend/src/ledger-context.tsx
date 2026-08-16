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
} from "./types";

interface LedgerContextValue {
  profile: Profile | null;
  settings: Settings;
  transactions: Transaction[];
  summary: Summary | null;
  loading: boolean;
  error: string | null;
  profileLoadError: string | null;
  demo: boolean;
  refresh(): Promise<void>;
  saveProfile(profile: Profile): Promise<void>;
  saveSettings(patch: Partial<Settings>): Promise<void>;
  createTransaction(draft: TransactionDraft, operationId?: string): Promise<TransactionResult>;
  answerReason(id: string, reason: string): Promise<TransactionResult>;
  getTransaction(id: string): Promise<TransactionDetail>;
  correctJudgment(
    id: string,
    label: JudgmentLabel,
    reason: string,
  ): Promise<Correction>;
  recordShareView(id: string): Promise<void>;
  recordShareSuccess(id: string): Promise<void>;
  deleteData(): Promise<void>;
}

const LedgerContext = createContext<LedgerContextValue | null>(null);

const initialSettings: Settings = {
  roast_enabled: false,
  locale: "ko-KR",
  timezone: "Asia/Seoul",
};

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "잠시 후 다시 시도해 주세요.";
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
      const [nextSettings, nextTransactions, nextSummary] = await Promise.all([
        ledgerApi.settings(),
        ledgerApi.transactions(),
        ledgerApi.summary(),
      ]);
      setProfile(nextProfile);
      setSettings(nextSettings);
      setTransactions(nextTransactions);
      setSummary(nextSummary);
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
          const needsReason = settings.roast_enabled && !draft.reason;
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
            status: needsReason ? "awaiting_reason" : "judged",
            created_at: new Date().toISOString(),
          };
          setTransactions((items) => [transaction, ...items]);
          return needsReason
            ? { transaction, signals: demoSignals, pending_question: { ...demoPending, transaction_id: transaction.transaction_id } }
            : { transaction, signals: demoSignals, judgment: demoJudgment(settings.roast_enabled) };
        }
        const result = await ledgerApi.createTransaction(draft, operationId);
        setTransactions((items) => [result.transaction, ...items]);
        setSummary(await ledgerApi.summary());
        return result;
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
        setSettings(initialSettings);
        setProfileLoadError(null);
      },
    }),
    [demo, error, loading, profile, profileLoadError, refresh, settings, summary, transactions, userKey],
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
