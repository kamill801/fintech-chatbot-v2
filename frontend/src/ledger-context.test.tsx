import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ledgerApi, ApiError } from "./api";
import { LedgerProvider, useLedger } from "./ledger-context";
import { demoPlanState, demoProfile, demoSettings, demoSummary, demoTransactions } from "./demo";

vi.mock("./auth-context", () => ({ useAuth: () => ({ userKey: "test-user" }) }));

const transaction = { ...demoTransactions[0], transaction_id: "persisted-one" };
const wrapper = ({ children }: { children: ReactNode }) => <LedgerProvider>{children}</LedgerProvider>;

describe("ledger mutation success boundary", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    vi.spyOn(ledgerApi, "profile").mockResolvedValue(demoProfile);
    vi.spyOn(ledgerApi, "settings").mockResolvedValue(demoSettings);
    vi.spyOn(ledgerApi, "transactions").mockResolvedValue([]);
    vi.spyOn(ledgerApi, "summary").mockResolvedValue(demoSummary);
    vi.spyOn(ledgerApi, "plan").mockResolvedValue(null);
    vi.spyOn(ledgerApi, "createTransaction").mockResolvedValue({ transaction });
  });
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it.each(["summary", "plan"] as const)("keeps a confirmed transaction when %s refresh fails", async (resource) => {
    const { result } = renderHook(useLedger, { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    vi.mocked(ledgerApi[resource]).mockRejectedValueOnce(new ApiError("request_failed", "synthetic refresh failure", 503));

    await act(async () => {
      await expect(result.current.createTransaction({ amount_krw: 9600, category: "food" }, "same-operation")).resolves.toMatchObject({ transaction: { transaction_id: "persisted-one" } });
    });
    expect(result.current.transactions.map((item) => item.transaction_id)).toEqual(["persisted-one"]);
    expect(result.current.syncWarning).toMatch(/저장됐지만/);
  });

  it("upserts the same transaction id when an idempotent result is returned again", async () => {
    const { result } = renderHook(useLedger, { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    await act(async () => {
      await result.current.createTransaction({ amount_krw: 9600, category: "food" }, "same-operation");
      await result.current.createTransaction({ amount_krw: 9600, category: "food" }, "same-operation");
    });
    expect(result.current.transactions.map((item) => item.transaction_id)).toEqual(["persisted-one"]);
    expect(ledgerApi.createTransaction).toHaveBeenCalledTimes(2);
  });

  it("does not label a secondary resource failure as a profile failure", async () => {
    vi.mocked(ledgerApi.summary).mockRejectedValueOnce(new ApiError("request_failed", "synthetic failure", 503));
    const { result } = renderHook(useLedger, { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.profile).toEqual(demoProfile);
    expect(result.current.profileLoadError).toBeNull();
    expect(result.current.error).toMatch(/일부/);
  });

  it("passes reviewed plan preview tokens through activation and revision apply", async () => {
    vi.mocked(ledgerApi.plan).mockResolvedValueOnce(demoPlanState);
    const previewPlan = vi.spyOn(ledgerApi, "previewPlan").mockResolvedValue({ ...demoPlanState, preview_token: "setup-token" });
    const activatePlan = vi.spyOn(ledgerApi, "activatePlan").mockResolvedValue(demoPlanState);
    const previewPlanRevision = vi.spyOn(ledgerApi, "previewPlanRevision").mockResolvedValue({
      revision_preview: {
        from_version: demoPlanState.plan.version,
        to_version: demoPlanState.plan.version + 1,
        before: demoPlanState.original_plan,
        after: { ...demoPlanState.plan, version: demoPlanState.plan.version + 1 },
        before_progress: demoPlanState.progress,
        after_progress: demoPlanState.progress,
        budget_change_krw: 0,
        flexible_remaining_change_krw: 0,
        narrative: demoPlanState.narrative,
      },
      plan: demoPlanState.plan,
      progress: demoPlanState.progress,
      preview_token: "revision-token",
    });
    const applyPlanRevision = vi.spyOn(ledgerApi, "applyPlanRevision").mockResolvedValue(demoPlanState);
    const draft = {
      period_start: demoPlanState.plan.period_start,
      period_end: demoPlanState.plan.period_end,
      confirmed_budget_krw: demoPlanState.plan.confirmed_budget_krw,
      priorities: demoPlanState.plan.priorities,
      planned_expenses: [],
    };

    const { result } = renderHook(useLedger, { wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.previewPlan(draft);
      await result.current.activatePlan(draft, "setup-token");
    });
    expect(previewPlan).toHaveBeenCalledWith(draft);
    expect(activatePlan).toHaveBeenCalledWith(draft, "setup-token");

    await act(async () => {
      const preview = await result.current.previewPlanRevision(draft, "변경 확인");
      expect(preview.preview_token).toBe("revision-token");
      await result.current.applyPlanRevision(draft, "변경 확인", preview.preview_token);
    });
    expect(previewPlanRevision).toHaveBeenCalledWith(draft, demoPlanState.plan.version, "변경 확인");
    expect(applyPlanRevision).toHaveBeenCalledWith(draft, demoPlanState.plan.version, "변경 확인", "revision-token");
  });
});
