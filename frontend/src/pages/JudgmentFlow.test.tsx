import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter, Route, Routes } from "../router";
import { JudgmentPage, SharePage, TransactionDetailPage } from "./JudgmentFlow";

const mocks = vi.hoisted(() => ({
  getTransaction: vi.fn(),
  recordShareSuccess: vi.fn(),
  recordShareView: vi.fn(),
  saveSettings: vi.fn(),
  correctJudgment: vi.fn(),
  reflectTransaction: vi.fn(),
  useLedger: vi.fn(),
}));

vi.mock("../ledger-context", () => ({
  useLedger: mocks.useLedger,
}));

describe("judgment voice", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    window.history.replaceState({}, "", "/judgments/tx-shopping");
    mocks.recordShareSuccess.mockReset().mockResolvedValue(undefined);
    mocks.recordShareView.mockReset().mockResolvedValue(undefined);
    mocks.saveSettings.mockReset().mockResolvedValue(undefined);
    mocks.correctJudgment.mockReset().mockResolvedValue(undefined);
    mocks.reflectTransaction.mockReset().mockResolvedValue(undefined);
    mocks.getTransaction.mockResolvedValue({
      transaction: {
        transaction_id: "tx-shopping",
        amount_krw: 120_000,
        category: "shopping",
        description: null,
        merchant: "온라인 쇼핑",
        occurred_at: "2026-08-05T12:00:00Z",
        source: "manual",
        source_reference: null,
        reason: null,
        status: "judged",
        created_at: "2026-08-05T12:00:00Z",
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
      recordShareSuccess: mocks.recordShareSuccess,
      recordShareView: mocks.recordShareView,
      saveSettings: mocks.saveSettings,
      correctJudgment: mocks.correctJudgment,
      reflectTransaction: mocks.reflectTransaction,
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

  it("saves the user's post-purchase reflection from transaction detail", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/transactions/tx-shopping");
    render(
      <BrowserRouter>
        <Routes><Route path="/transactions/:transactionId" element={<TransactionDetailPage />} /></Routes>
      </BrowserRouter>,
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "지금 생각하면 이 소비 어땠나요?" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: /후회함/ }));
    await user.type(screen.getByPlaceholderText(/왜 그렇게 느꼈는지/), "충동적으로 샀어요");
    await user.click(screen.getByRole("button", { name: "내 소비 기준에 반영" }));

    await waitFor(() => expect(mocks.reflectTransaction).toHaveBeenCalledWith("tx-shopping", "regretted", "충동적으로 샀어요"));
    expect(screen.getByText("내 소비 기준에 반영했어요.")).toBeInTheDocument();
  });

  it("derives share preview from the loaded judgment and records success after download", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/share/tx-shopping");
    mocks.recordShareView.mockResolvedValue(undefined);
    mocks.recordShareSuccess.mockResolvedValue(null);
    const context = {
      beginPath: vi.fn(),
      fill: vi.fn(),
      fillRect: vi.fn(),
      fillText: vi.fn(),
      lineTo: vi.fn(),
      measureText: vi.fn(() => ({ width: 100 })),
      moveTo: vi.fn(),
      roundRect: vi.fn(),
      stroke: vi.fn(),
    };
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(context as unknown as CanvasRenderingContext2D);
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation((callback) => {
      callback(new Blob(["png"], { type: "image/png" }));
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:jangbu"),
      revokeObjectURL: vi.fn(),
    });

    render(
      <BrowserRouter>
        <Routes><Route path="/share/:transactionId" element={<SharePage />} /></Routes>
      </BrowserRouter>,
    );

    await waitFor(() => expect(screen.getByText(/장부 바닥이 보이는데/)).toBeInTheDocument());
    await waitFor(() => expect(mocks.recordShareView).toHaveBeenCalledWith("judgment-shopping"));
    expect(mocks.recordShareSuccess).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /이미지 저장/ }));

    await waitFor(() => expect(mocks.recordShareSuccess).toHaveBeenCalledWith("judgment-shopping"));
    expect(screen.queryByText(/카페에 네 이름/)).not.toBeInTheDocument();
  });

  it("uses correction-aware copy instead of sharing the superseded judgment", async () => {
    window.history.replaceState({}, "", "/share/tx-shopping");
    const original = await mocks.getTransaction();
    mocks.getTransaction.mockResolvedValue({
      ...original,
      judgment: {
        ...original.judgment,
        correction: {
          judgment_id: "judgment-shopping",
          original_label: "overspending",
          corrected_label: "justified",
          correction_reason: "회사 환급",
          corrected_at: "2026-08-14T03:00:00Z",
        },
        effective_label: "justified",
      },
    });

    render(
      <BrowserRouter>
        <Routes><Route path="/share/:transactionId" element={<SharePage />} /></Routes>
      </BrowserRouter>,
    );

    await waitFor(() => expect(screen.getByText(/납득할 만한 지출/)).toBeInTheDocument());
    expect(screen.queryByText(/장부 바닥이 보이는데/)).not.toBeInTheDocument();
    expect(screen.getByText(/판단 · 납득 가능한 지출/)).toBeInTheDocument();
  });
});
