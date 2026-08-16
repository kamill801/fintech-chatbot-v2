import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "../router";
import { demoProfile, demoSettings, demoSummary, demoTransactions } from "../demo";
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
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/add");
    mocks.createTransaction.mockReset();
    mocks.useLedger.mockReturnValue({
      createTransaction: mocks.createTransaction,
      demo: false,
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
    await user.click(screen.getByRole("button", { name: "기록하고 판단받기" }));
    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "기록하고 판단받기" }));

    await waitFor(() => expect(mocks.createTransaction).toHaveBeenCalledTimes(2));
    expect(mocks.createTransaction.mock.calls[0][1]).toBe("manual-op-1");
    expect(mocks.createTransaction.mock.calls[1][1]).toBe("manual-op-1");
    expect(window.localStorage.getItem(manualDraftKey("user-a"))).toBeNull();
  });

  it("shows a fixed expense type and an accessible native date field", () => {
    render(<BrowserRouter><ManualTransactionPage /></BrowserRouter>);

    const typeSummary = screen.getAllByLabelText("거래 유형: 지출").at(-1);
    expect(typeSummary).toBeInTheDocument();
    expect(within(typeSummary!).getByText("거래 유형")).toBeInTheDocument();
    expect(within(typeSummary!).getByText("지출")).toBeInTheDocument();
    expect(within(typeSummary!).queryByRole("button")).not.toBeInTheDocument();

    const dateInput = screen.getAllByLabelText("날짜").at(-1)!;
    expect(dateInput).toHaveAttribute("type", "date");
    expect((dateInput as HTMLInputElement).value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe("demo financial consistency", () => {
  beforeEach(() => {
    window.localStorage.clear();
    mocks.useLedger.mockReturnValue({
      answerReason: vi.fn(),
      demo: true,
      getTransaction: vi.fn().mockResolvedValue({ transaction: demoTransactions[0] }),
      profile: demoProfile,
      settings: demoSettings,
      summary: demoSummary,
      transactions: demoTransactions,
    });
  });

  it("derives the Home budget and goal values from the shared demo records", () => {
    window.history.replaceState({}, "", "/?demo=1");
    render(<BrowserRouter><HomePage /></BrowserRouter>);

    expect(screen.getByText("422,500원")).toBeInTheDocument();
    expect(screen.getByText("예산의 53% 남음")).toBeInTheDocument();
    expect(screen.getByText("목표까지 30%")).toBeInTheDocument();
    expect(screen.queryByText("623,000원")).not.toBeInTheDocument();
  });

  it("shows the same weekly recurrence count used by the demo judgment", async () => {
    window.history.replaceState({}, "", "/transactions/tx-cafe/reason?demo=1");
    render(<BrowserRouter><ReasonPage /></BrowserRouter>);

    expect(await screen.findByText("생활비 예산 47% 사용")).toBeInTheDocument();
    expect(screen.getByText("이번 주 같은 분류 3번째")).toBeInTheDocument();
  });
});
