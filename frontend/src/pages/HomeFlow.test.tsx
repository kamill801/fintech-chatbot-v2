import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "../router";
import { demoPlanState, demoProfile, demoSettings, demoSummary, demoTransactions } from "../demo";
import { manualDraftKey } from "../local-drafts";
import { HomePage, ManualTransactionPage, ReasonPage } from "./HomeFlow";

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
        transaction: { transaction_id: "tx-1" },
        pending_question: { transaction_id: "tx-1" },
      });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "거래 기록하기" }));
    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "거래 기록하기" }));

    await waitFor(() => expect(mocks.createTransaction).toHaveBeenCalledTimes(2));
    expect(mocks.createTransaction.mock.calls[0][1]).toBe("manual-op-1");
    expect(mocks.createTransaction.mock.calls[1][1]).toBe("manual-op-1");
    expect(window.localStorage.getItem(manualDraftKey("user-a"))).toBeNull();
  });

  it("supports each ledger transaction type and an accessible native date field", async () => {
    const user = userEvent.setup();
    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);

    const typeControl = screen.getByRole("group", { name: "거래 유형" });
    expect(within(typeControl).getByRole("button", { name: "지출" })).toHaveAttribute("aria-pressed", "true");
    expect(within(typeControl).getByRole("button", { name: "수입" })).toBeInTheDocument();
    expect(within(typeControl).getByRole("button", { name: "이체" })).toBeInTheDocument();
    await user.click(within(typeControl).getByRole("button", { name: "수입" }));
    expect(screen.getByRole("heading", { name: "얼마 들어왔어?" })).toBeInTheDocument();
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
      transaction: { transaction_id: "tx-normal" },
      judgment: { judgment_id: "judgment-normal" },
    });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "거래 기록하기" }));

    await waitFor(() => expect(window.location.pathname).toBe("/ledger"));
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
      transaction: { transaction_id: "tx-roast" },
      pending_question: { transaction_id: "tx-roast" },
    });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "기록하고 이유 답하기" }));

    await waitFor(() => expect(window.location.pathname).toBe("/transactions/tx-roast/reason"));
    expect(screen.getByText("욕쟁이 할머니가 지출 이유를 한 번 확인해요")).toBeInTheDocument();
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
      transaction: { transaction_id: "tx-income", transaction_type: "income" },
    });

    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "수입" }));
    await user.click(screen.getByRole("button", { name: "거래 기록하기" }));

    await waitFor(() => expect(window.location.pathname).toBe("/ledger"));
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
    expect(screen.getByText("목표까지 30%")).toBeInTheDocument();
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

    expect(await screen.findByText("생활비 예산 13% 사용")).toBeInTheDocument();
  });

  it("shows the same weekly recurrence count used by the demo judgment", async () => {
    window.history.replaceState({}, "", "/transactions/tx-cafe/reason?demo=1");
    render(<BrowserRouter><ReasonPage /></BrowserRouter>);

    expect(await screen.findByText("생활비 예산 47% 사용")).toBeInTheDocument();
    expect(screen.getByText("이번 주 같은 분류 3번째")).toBeInTheDocument();
  });
});
