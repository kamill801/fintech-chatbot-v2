// Diagnostic artifact for b46e3a4, NOT acceptance tests for the repaired app.
// Copy to frontend/src/UXAudit.repro.test.tsx, run Vitest, then remove the copy.
// All API responses are synthetic; no server or user account is contacted.
import { type ReactNode } from "react";
import { act, cleanup, render, renderHook, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ledgerApi, ApiError } from "./api";
import { LedgerProvider, useLedger } from "./ledger-context";
import { demoProfile, demoSettings, demoSummary, demoTransactions, demoPlanState } from "./demo";
import { BrowserRouter, Route, Routes } from "./router";
import { ManualTransactionPage } from "./pages/HomeFlow";
import { LedgerPage } from "./pages/MainPages";
import { PlanPage } from "./pages/PlanPage";

vi.mock("./auth-context", () => ({ useAuth: () => ({ userKey: "synthetic-ux-audit" }) }));

const transaction = { ...demoTransactions[0], transaction_id: "audit-tx", occurred_at: "2026-07-12T03:00:00.000Z" };
function Wrapper({ children }: { children: ReactNode }) { return <LedgerProvider>{children}</LedgerProvider>; }
function Gate({ children }: { children: ReactNode }) {
  const ledger = useLedger();
  return ledger.loading ? <p>audit-loading</p> : <><output data-testid="record-count">{ledger.transactions.length}</output>{children}</>;
}
function renderRoute(path: string) {
  window.history.replaceState({}, "", path);
  return render(<BrowserRouter><LedgerProvider><Gate><Routes>
    <Route path="/add" element={<ManualTransactionPage />} />
    <Route path="/ledger" element={<LedgerPage />} />
    <Route path="/plan" element={<PlanPage />} />
  </Routes></Gate></LedgerProvider></BrowserRouter>);
}

describe("AUDIT: reproduce existing defects, not desired behavior", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.history.replaceState({}, "", "/");
    vi.spyOn(ledgerApi, "profile").mockResolvedValue(demoProfile);
    vi.spyOn(ledgerApi, "settings").mockResolvedValue({ ...demoSettings, roast_enabled: false });
    vi.spyOn(ledgerApi, "transactions").mockResolvedValue([]);
    vi.spyOn(ledgerApi, "summary").mockResolvedValue(demoSummary);
    vi.spyOn(ledgerApi, "plan").mockResolvedValue(null);
    vi.spyOn(ledgerApi, "createTransaction").mockResolvedValue({ transaction });
  });
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it.each(["summary", "plan"] as const)("rejects an already successful create when %s refresh fails", async (endpoint) => {
    const { result } = renderHook(useLedger, { wrapper: Wrapper });
    await waitFor(() => expect(result.current.loading).toBe(false));
    vi.mocked(ledgerApi[endpoint]).mockRejectedValueOnce(new ApiError("request_failed", "synthetic refresh failed", 503));
    await act(async () => {
      await expect(result.current.createTransaction({ amount_krw: 9600, category: "food" }, "audit-op")).rejects.toThrow("synthetic refresh failed");
    });
    expect(result.current.transactions.map((item) => item.transaction_id)).toEqual(["audit-tx"]);
    expect(ledgerApi.createTransaction).toHaveBeenCalledTimes(1);
  });

  it("shows a save failure even after POST success if draft removal throws", async () => {
    const user = userEvent.setup();
    renderRoute("/add?date=2026-07-12");
    await screen.findByRole("textbox", { name: "금액" });
    await user.clear(screen.getByRole("textbox", { name: "금액" }));
    await user.type(screen.getByRole("textbox", { name: "금액" }), "9600");
    vi.spyOn(Storage.prototype, "removeItem").mockImplementationOnce(() => { throw new Error("synthetic storage failure"); });
    await user.click(screen.getByRole("button", { name: "거래 기록하기" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("거래를 저장하지 못했어요");
    expect(screen.getByTestId("record-count")).toHaveTextContent("1");
    expect(window.location.pathname).toBe("/add");
  });

  it("loses the entered month and date on successful calendar navigation", async () => {
    const user = userEvent.setup();
    renderRoute("/add?date=2026-07-12");
    await screen.findByRole("textbox", { name: "금액" });
    await user.clear(screen.getByRole("textbox", { name: "금액" }));
    await user.type(screen.getByRole("textbox", { name: "금액" }), "9600");
    await user.click(screen.getByRole("button", { name: "거래 기록하기" }));
    await waitFor(() => expect(window.location.pathname).toBe("/ledger"));
    expect(window.location.search).toBe("");
    expect(screen.queryByRole("heading", { name: "7월 12일 내역" })).not.toBeInTheDocument();
    expect(screen.getByTestId("record-count")).toHaveTextContent("1");
  });

  it("allows confirming a changed plan after its fresh preview failed", async () => {
    const user = userEvent.setup();
    vi.spyOn(ledgerApi, "previewPlan").mockResolvedValueOnce(demoPlanState).mockRejectedValueOnce(new Error("synthetic preview failed"));
    renderRoute("/plan");
    await screen.findByRole("button", { name: "다음" });
    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.click(screen.getByRole("button", { name: "검토하기" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "확인하고 계획 시작" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "다시 수정" }));
    await user.type(screen.getByRole("textbox", { name: /우선순위/ }), "changed priority");
    await user.click(screen.getByRole("button", { name: "검토하기" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("계획 미리보기를 만들지 못했어요");
    expect(screen.getByRole("button", { name: "확인하고 계획 시작" })).toBeEnabled();
  });
});
