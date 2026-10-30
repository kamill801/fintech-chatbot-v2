import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter, Route, Routes } from "../router";
import { demoPlanState, demoProfile, demoSettings, demoSummary, demoTransactions } from "../demo";
import { manualDraftKey } from "../local-drafts";
import { HomePage, ManualTransactionPage, ReasonPage } from "./HomeFlow";
import type { Transaction } from "../types";

const mocks = vi.hoisted(() => ({
  createTransaction: vi.fn(),
  useLedger: vi.fn(),
}));

vi.mock("../ledger-context", () => ({
  useLedger: mocks.useLedger,
}));

vi.mock("../auth-context", () => ({
  useAuth: () => ({ userKey: "user-a" }),
}));

describe("manual transaction drafts", () => {
  afterEach(cleanup);

  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/add");
    mocks.createTransaction.mockReset();
    mocks.useLedger.mockReturnValue({
      createTransaction: mocks.createTransaction,
      demo: false,
      settings: { roast_enabled: false, locale: "ko-KR", timezone: "Asia/Seoul" },
    });
  });

  it("keeps the same operation id when a saved transaction is retried", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(
      manualDraftKey("user-a"),
      JSON.stringify({
        draft: { amount_krw: 12000, category: "cafe", merchant: "카페" },
        operationId: "manual-op-1",
      }),
    );
    mocks.createTransaction
      .mockRejectedValueOnce(new Error("gateway"))
      .mockResolvedValueOnce({
        transaction: { transaction_id: "tx-1", occurred_at: "2026-08-19T03:00:00Z" },
        pending_question: { transaction_id: "tx-1" },
      });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "지출 저장하기" }));
    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "같은 요청으로 확인하기" }));

    await waitFor(() => expect(mocks.createTransaction).toHaveBeenCalledTimes(2));
    expect(mocks.createTransaction.mock.calls[0][1]).toBe("manual-op-1");
    expect(mocks.createTransaction.mock.calls[1][1]).toBe("manual-op-1");
    expect(mocks.createTransaction.mock.calls[1][0]).toEqual(mocks.createTransaction.mock.calls[0][0]);
    expect(window.localStorage.getItem(manualDraftKey("user-a"))).toBeNull();
  });

  it("submits a rapid double tap only once", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(manualDraftKey("user-a"), JSON.stringify({
      draft: { amount_krw: 9600, category: "food", merchant: "분식집" },
      operationId: "one-tap-op",
    }));
    mocks.createTransaction.mockImplementation(() => new Promise(() => undefined));

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    const saveButton = screen.getByRole("button", { name: "지출 저장하기" });
    await user.click(saveButton);
    await user.click(saveButton);

    expect(mocks.createTransaction).toHaveBeenCalledTimes(1);
  });

  it("supports each ledger transaction type and an accessible native date field", async () => {
    const user = userEvent.setup();
    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);

    const typeControl = screen.getByRole("group", { name: "거래 유형" });
    expect(within(typeControl).getByRole("button", { name: "지출" })).toHaveAttribute("aria-pressed", "true");
    expect(within(typeControl).getByRole("button", { name: "수입" })).toBeInTheDocument();
    expect(within(typeControl).getByRole("button", { name: "이체" })).toBeInTheDocument();
    await user.click(within(typeControl).getByRole("button", { name: "수입" }));
    expect(screen.getByRole("heading", { name: "수입 금액" })).toBeInTheDocument();
    expect(screen.queryByText("이번 달 예산에서 제외")).not.toBeInTheDocument();

    const dateInput = screen.getAllByLabelText("날짜").at(-1)!;
    expect(dateInput).toHaveAttribute("type", "date");
    expect((dateInput as HTMLInputElement).value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("records immediately in normal mode and returns to the ledger", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(
      manualDraftKey("user-a"),
      JSON.stringify({
        draft: { amount_krw: 12800, category: "shopping", merchant: "문구점" },
        operationId: "normal-op",
      }),
    );
    mocks.createTransaction.mockResolvedValue({
      transaction: { transaction_id: "tx-normal", occurred_at: "2026-08-19T03:00:00Z" },
      judgment: { judgment_id: "judgment-normal" },
    });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "지출 저장하기" }));

    await waitFor(() => expect(window.location.pathname).toBe("/ledger"));
    expect(window.location.search).toBe("?date=2026-08-19&view=calendar&saved=tx-normal");
    expect(screen.queryByText("정보가 부족하면 이유를 한 번 물어봐요")).not.toBeInTheDocument();
  });

  it("requires the reason flow only when grandma mode is enabled", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue({
      createTransaction: mocks.createTransaction,
      demo: false,
      settings: { roast_enabled: true, locale: "ko-KR", timezone: "Asia/Seoul" },
    });
    window.localStorage.setItem(
      manualDraftKey("user-a"),
      JSON.stringify({
        draft: { amount_krw: 12800, category: "shopping", merchant: "문구점" },
        operationId: "roast-op",
      }),
    );
    mocks.createTransaction.mockResolvedValue({
      transaction: { transaction_id: "tx-roast", occurred_at: "2026-08-19T03:00:00Z" },
      pending_question: { transaction_id: "tx-roast" },
    });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "저장하고 이유 답하기" }));

    await waitFor(() => expect(window.location.pathname).toBe("/transactions/tx-roast/reason"));
    expect(screen.getByText("저장 후 지출 이유를 한 번 물어요.")).toBeInTheDocument();
  });

  it("records income without opening the expense reason flow", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue({
      createTransaction: mocks.createTransaction,
      demo: false,
      settings: { roast_enabled: true, locale: "ko-KR", timezone: "Asia/Seoul" },
      transactions: [],
    });
    window.localStorage.setItem(
      manualDraftKey("user-a"),
      JSON.stringify({
        draft: { amount_krw: 3500000, category: "other", merchant: "회사" },
        operationId: "income-op",
      }),
    );
    mocks.createTransaction.mockResolvedValue({
      transaction: { transaction_id: "tx-income", transaction_type: "income", occurred_at: "2026-08-19T03:00:00Z" },
    });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "수입" }));
    await user.click(screen.getByRole("button", { name: "수입 저장하기" }));

    await waitFor(() => expect(window.location.pathname).toBe("/ledger"));
    expect(window.location.search).toBe("?date=2026-08-19&view=calendar&saved=tx-income");
    expect(mocks.createTransaction).toHaveBeenCalledWith(expect.objectContaining({
      amount_krw: 3500000,
      transaction_type: "income",
      category: "salary",
      account_id: "cash",
    }), "income-op");
  });

  it("prefills the date selected from the ledger calendar", () => {
    window.history.replaceState({}, "", "/add?date=2026-08-19");

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);

    expect(screen.getByLabelText("날짜")).toHaveValue("2026-08-19");
  });
});

describe("demo financial consistency", () => {
  afterEach(cleanup);

  beforeEach(() => {
    window.localStorage.clear();
    mocks.useLedger.mockReturnValue({
      answerReason: vi.fn(),
      demo: true,
      getTransaction: vi.fn().mockResolvedValue({ transaction: demoTransactions[0] }),
      profile: demoProfile,
      plan: demoPlanState,
      settings: demoSettings,
      summary: demoSummary,
      transactions: demoTransactions,
    });
  });

  it("leads with plan-period flexible living money and input freshness", () => {
    window.history.replaceState({}, "", "/?demo=1");
    render(<BrowserRouter><HomePage /></BrowserRouter>);

    expect(screen.getByText("322,500원")).toBeInTheDocument();
    expect(screen.getByText(/직접 입력된 거래 기준/)).toBeInTheDocument();
    expect(screen.getByText("이번 주 배정")).toBeInTheDocument();
    expect(screen.getByText("이번 주 남음")).toBeInTheDocument();
    expect(screen.getByText("30% 달성")).toBeInTheDocument();
    expect(screen.queryByText("623,000원")).not.toBeInTheDocument();
  });

  it("uses budget spending rather than total expense for the reason signal", async () => {
    mocks.useLedger.mockReturnValue({
      answerReason: vi.fn(),
      demo: true,
      getTransaction: vi.fn().mockResolvedValue({ transaction: demoTransactions[0] }),
      profile: demoProfile,
      plan: demoPlanState,
      settings: demoSettings,
      summary: { ...demoSummary, total_spent_krw: 500_000, budget_spent_krw: 100_000 },
      transactions: demoTransactions,
    });
    window.history.replaceState({}, "", "/transactions/tx-cafe/reason?demo=1");
    render(<BrowserRouter><ReasonPage /></BrowserRouter>);

    expect(await screen.findByText("8월 생활비 예산 13% 사용 · 현재 입력 기준")).toBeInTheDocument();
  });

  it("labels the demo recurrence as seven days instead of a calendar week", async () => {
    window.history.replaceState({}, "", "/transactions/tx-cafe/reason?demo=1");
    render(<BrowserRouter><ReasonPage /></BrowserRouter>);

    expect(await screen.findByText("8월 생활비 예산 47% 사용 · 현재 입력 기준")).toBeInTheDocument();
    expect(screen.getByText("지출일 기준 최근 7일 · 같은 분류 3건")).toBeInTheDocument();
  });

  it("returns from an unanswered reason to that transaction's calendar date", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/transactions/tx-cafe/reason?demo=1");
    render(<BrowserRouter><ReasonPage /></BrowserRouter>);

    await screen.findByText("8월 생활비 예산 47% 사용 · 현재 입력 기준");
    await user.click(screen.getByRole("button", { name: "나중에 답하기 · 장부로" }));
    expect(window.location.pathname).toBe("/ledger");
    expect(window.location.search).toBe("?date=2026-08-03&view=calendar&saved=tx-cafe&demo=1");
  });
});

describe("reason evidence boundaries", () => {
  afterEach(cleanup);

  const transaction: Transaction = {
    ...demoTransactions[0],
    transaction_id: "tx-reason",
    occurred_at: "2026-08-02T15:30:00Z", // Monday, August 3 at 00:30 in Korea.
    status: "awaiting_reason",
  };

  function renderReason(transactions: Transaction[], summary = demoSummary, demo = false) {
    mocks.useLedger.mockReturnValue({
      answerReason: vi.fn(),
      demo,
      getTransaction: vi.fn().mockResolvedValue({ transaction }),
      profile: demoProfile,
      summary,
      transactions,
    });
    window.history.replaceState({}, "", `/transactions/tx-reason/reason${demo ? "?demo=1" : ""}`);
    return render(<BrowserRouter><Routes><Route path="/transactions/:transactionId/reason" element={<ReasonPage />} /></Routes></BrowserRouter>);
  }

  it.each([false, true])("counts only same-category expenses in seven Korean dates through this purchase (demo=%s)", async (demo) => {
    const record = (id: string, occurredAt: string, patch: Partial<Transaction> = {}): Transaction => ({
      ...transaction,
      transaction_id: id,
      occurred_at: occurredAt,
      ...patch,
    });
    renderReason([
      transaction,
      record("first-in-range", "2026-07-27T15:00:00Z"),
      record("before-this-purchase", "2026-08-02T15:20:00Z"),
      record("too-old", "2026-07-27T14:59:59Z"),
      record("later-same-day", "2026-08-02T15:31:00Z"),
      record("future", "2030-08-03T00:00:00Z"),
      record("income", "2026-08-02T15:10:00Z", { transaction_type: "income" }),
      record("transfer", "2026-08-02T15:10:00Z", { transaction_type: "transfer" }),
      record("other-category", "2026-08-02T15:10:00Z", { category: "food" }),
    ], demoSummary, demo);

    expect(await screen.findByText("지출일 기준 최근 7일 · 같은 분류 3건")).toBeInTheDocument();
    expect(screen.queryByText(/이번 주 같은 분류/)).not.toBeInTheDocument();
  });

  it("includes the loaded purchase once when the transaction list has not caught up", async () => {
    renderReason([]);

    expect(await screen.findByText("지출일 기준 최근 7일 · 같은 분류 1건")).toBeInTheDocument();
  });

  it("does not present a different month's budget as historical evidence", async () => {
    renderReason([transaction], { ...demoSummary, month: "2026-10" });

    expect(await screen.findByText("당시 예산 사용률은 확인할 수 없어요")).toBeInTheDocument();
    expect(screen.queryByText(/47% 사용/)).not.toBeInTheDocument();
  });

  it("matches the summary month using the transaction's Korean date", async () => {
    const boundaryTransaction = { ...transaction, occurred_at: "2026-07-31T15:05:00Z" };
    renderReason([boundaryTransaction]);

    expect(await screen.findByText("8월 생활비 예산 47% 사용 · 현재 입력 기준")).toBeInTheDocument();
  });
});
