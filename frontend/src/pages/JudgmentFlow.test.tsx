import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter, Route, Routes } from "../router";
import { JudgmentPage } from "./JudgmentFlow";

const mocks = vi.hoisted(() => ({
  getTransaction: vi.fn(),
  saveSettings: vi.fn(),
  useLedger: vi.fn(),
}));

vi.mock("../ledger-context", () => ({
  useLedger: mocks.useLedger,
}));

describe("judgment voice", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/judgments/tx-shopping");
    mocks.getTransaction.mockResolvedValue({
      transaction: {
        transaction_id: "tx-shopping",
        amount_krw: 120_000,
        category: "shopping",
        merchant: "온라인 쇼핑",
        occurred_at: "2026-08-05T12:00:00Z",
        source: "manual",
        status: "judged",
      },
      signals: { risk_score: 0.81, factors: ["budget_usage"] },
      judgment: {
        judgment_id: "judgment-shopping",
        transaction_id: "tx-shopping",
        mode: "roast",
        label: "overspending",
        confidence: 0.86,
        rationale: "생활비 예산 사용량이 높아요.",
        recommended_action: "이번 주 쇼핑을 한 번 쉬어요.",
        message: "이 녀석아, 장부 바닥이 보이는데 또 장바구니를 채웠냐. 이번 주 쇼핑은 한 번 쉬어.",
        fallback_used: false,
        model: "test-model",
        policy_version: "overspending-v1",
        original_label: "overspending",
        effective_label: "overspending",
        correction: null,
      },
    });
    mocks.useLedger.mockReturnValue({
      demo: false,
      getTransaction: mocks.getTransaction,
      saveSettings: mocks.saveSettings,
      settings: { roast_enabled: true, locale: "ko-KR", timezone: "Asia/Seoul" },
    });
  });

  it("uses the server judgment as the headline instead of a fixed cafe joke", async () => {
    render(
      <BrowserRouter>
        <Routes><Route path="/judgments/:transactionId" element={<JudgmentPage />} /></Routes>
      </BrowserRouter>,
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: /장부 바닥이 보이는데/ })).toBeInTheDocument());
    expect(screen.queryByText(/카페에 네 이름/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("욕쟁이 할머니 모드 켜짐")).toBeInTheDocument();
  });
});
