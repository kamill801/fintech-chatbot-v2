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
  updateTransaction: vi.fn(),
  deleteTransaction: vi.fn(),
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
    mocks.updateTransaction.mockReset().mockResolvedValue(undefined);
    mocks.deleteTransaction.mockReset().mockResolvedValue(undefined);
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
      updateTransaction: mocks.updateTransaction,
      deleteTransaction: mocks.deleteTransaction,
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

  it.each([
    ["judgment", "/judgments/tx-shopping", { fallback_used: true }, "AI 응답 대신 입력된 예산 기준으로 안내해요."],
    ["detail", "/transactions/tx-shopping", { fallback_used: true }, "AI 응답 대신 입력된 예산 기준으로 안내해요."],
    ["judgment", "/judgments/tx-shopping", { display_fallback_used: true }, "표현을 조정한 안내예요. 판단과 추천 행동은 그대로예요."],
    ["detail", "/transactions/tx-shopping", { display_fallback_used: true }, "표현을 조정한 안내예요. 판단과 추천 행동은 그대로예요."],
  ])("discloses substituted guidance on %s", async (page, path, provenance, message) => {
    const original = await mocks.getTransaction();
    mocks.getTransaction.mockResolvedValue({ ...original, judgment: { ...original.judgment, ...provenance } });
    window.history.replaceState({}, "", path);
    render(<BrowserRouter><Routes><Route path={page === "judgment" ? "/judgments/:transactionId" : "/transactions/:transactionId"} element={page === "judgment" ? <JudgmentPage /> : <TransactionDetailPage />} /></Routes></BrowserRouter>);

    expect(await screen.findByText(message)).toBeInTheDocument();
    if (page === "judgment") expect(screen.getByText("이번 주 쇼핑을 한 번 쉬어요.")).toBeInTheDocument();
    else expect(screen.getByText("생활비 예산 사용량이 높아요.")).toBeInTheDocument();
  });

  it("does not describe unchanged model output as a substitute", async () => {
    render(<BrowserRouter><Routes><Route path="/judgments/:transactionId" element={<JudgmentPage />} /></Routes></BrowserRouter>);
    await screen.findByRole("heading", { name: /장부 바닥이 보이는데/ });
    expect(screen.queryByText(/AI 응답 대신|표현을 조정한 안내/)).not.toBeInTheDocument();
    expect(screen.queryByText("☕")).not.toBeInTheDocument();
  });

  it.each([
    ["justified", "내 평가를 ‘납득 가능한 지출’로 바꿨어요."],
    ["caution", "내 평가를 ‘주의가 필요한 지출’로 바꿨어요."],
    ["overspending", "내 평가를 ‘과소비’로 바꿨어요."],
    ["insufficient_context", "내 평가를 ‘정보가 더 필요함’으로 바꿨어요."],
  ])("keeps corrected %s judgments in the selected normal voice", async (label, message) => {
    const original = await mocks.getTransaction();
    mocks.getTransaction.mockResolvedValue({
      ...original,
      judgment: {
        ...original.judgment,
        effective_label: label,
        correction: {
          judgment_id: "judgment-shopping",
          original_label: "overspending",
          corrected_label: label,
          correction_reason: "내 소비 기준으로 다시 판단했어요",
          corrected_at: "2026-08-14T03:00:00Z",
        },
      },
    });
    mocks.useLedger.mockReturnValue({
      demo: false,
      getTransaction: mocks.getTransaction,
      saveSettings: mocks.saveSettings,
      settings: { roast_enabled: false, locale: "ko-KR", timezone: "Asia/Seoul" },
    });

    render(<BrowserRouter><Routes><Route path="/judgments/:transactionId" element={<JudgmentPage />} /></Routes></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: message })).toBeInTheDocument();
    expect(screen.getByText(/기록 당시 AI 판단: 과소비/)).toBeInTheDocument();
    expect(screen.getByLabelText("욕쟁이 할머니 모드 꺼짐")).toBeInTheDocument();
    expect(screen.queryByText(/확인해라|남겨라/)).not.toBeInTheDocument();
    expect(screen.getByText("이번 주 쇼핑을 한 번 쉬어요.")).toBeInTheDocument();
  });

  it("keeps the grandma voice for a corrected judgment when explicitly enabled", async () => {
    const original = await mocks.getTransaction();
    mocks.getTransaction.mockResolvedValue({
      ...original,
      judgment: {
        ...original.judgment,
        effective_label: "justified",
        correction: {
          judgment_id: "judgment-shopping",
          original_label: "overspending",
          corrected_label: "justified",
          correction_reason: "회사 환급",
          corrected_at: "2026-08-14T03:00:00Z",
        },
      },
    });

    render(<BrowserRouter><Routes><Route path="/judgments/:transactionId" element={<JudgmentPage />} /></Routes></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: "그래, 네 평가는 ‘납득 가능한 지출’로 남겨두마. 기록 당시 판단도 장부에 그대로 있다." })).toBeInTheDocument();
    expect(screen.getByText("이번 주 쇼핑을 한 번 쉬어요.")).toBeInTheDocument();
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
    const original = await mocks.getTransaction();
    mocks.reflectTransaction.mockResolvedValue({
      ...original.transaction,
      reflection: "regretted",
      reflection_note: "충동적으로 샀어요",
      reflected_at: "2026-08-06T12:00:00Z",
    });
    await user.click(screen.getByRole("button", { name: /후회함/ }));
    await user.type(screen.getByRole("textbox", { name: /한 줄 메모/ }), "충동적으로 샀어요");
    await user.click(screen.getByRole("button", { name: "내 소비 기준에 반영" }));

    await waitFor(() => expect(mocks.reflectTransaction).toHaveBeenCalledWith("tx-shopping", "regretted", "충동적으로 샀어요"));
    expect(screen.getByText("내 소비 기준에 반영했어요.")).toBeInTheDocument();
  });

  it("opens transaction editing on the Korean ledger date and saves the edited transaction", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/transactions/tx-shopping");
    const original = await mocks.getTransaction();
    mocks.getTransaction.mockResolvedValue({
      ...original,
      transaction: {
        ...original.transaction,
        occurred_at: "2026-08-04T18:00:00Z",
        transaction_type: "expense",
        account_id: "cash",
        destination_account_id: null,
        exclude_from_budget: false,
      },
    });
    mocks.updateTransaction.mockResolvedValue({
      ...original,
      transaction: {
        ...original.transaction,
        amount_krw: 98000,
        category: "food",
        merchant: "김밥집",
        occurred_at: "2026-08-05T03:00:00Z",
        transaction_type: "expense",
        account_id: "cash",
        destination_account_id: null,
        exclude_from_budget: false,
      },
    });
    mocks.useLedger.mockReturnValue({
      demo: false,
      getTransaction: mocks.getTransaction,
      recordShareSuccess: mocks.recordShareSuccess,
      recordShareView: mocks.recordShareView,
      saveSettings: mocks.saveSettings,
      correctJudgment: mocks.correctJudgment,
      updateTransaction: mocks.updateTransaction,
      deleteTransaction: mocks.deleteTransaction,
      reflectTransaction: mocks.reflectTransaction,
      settings: {
        roast_enabled: true,
        locale: "ko-KR",
        timezone: "Asia/Seoul",
        accounts: [
          { account_id: "cash", name: "현금", account_type: "cash", opening_balance_krw: 0, archived: true },
          { account_id: "card", name: "카드", account_type: "card", opening_balance_krw: 0, archived: false },
        ],
      },
    });

    render(
      <BrowserRouter>
        <Routes><Route path="/transactions/:transactionId" element={<TransactionDetailPage />} /></Routes>
      </BrowserRouter>,
    );

    await waitFor(() => expect(screen.getByRole("heading", { name: "지금 생각하면 이 소비 어땠나요?" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "거래 내용 수정" }));
    expect(screen.getByLabelText("날짜")).toHaveValue("2026-08-05");
    expect(screen.getByLabelText("계좌")).toHaveValue("cash");
    expect(screen.getByRole("option", { name: "현금 (숨김)" })).toBeInTheDocument();
    await user.clear(screen.getByLabelText("금액"));
    await user.type(screen.getByLabelText("금액"), "98000");
    await user.selectOptions(screen.getByLabelText("분류"), "food");
    await user.clear(screen.getByLabelText("사용처"));
    await user.type(screen.getByLabelText("사용처"), "김밥집");
    await user.click(screen.getByRole("button", { name: "거래 저장" }));

    await waitFor(() => expect(mocks.updateTransaction).toHaveBeenCalledWith("tx-shopping", expect.objectContaining({
      amount_krw: 98000,
      category: "food",
      merchant: "김밥집",
      occurred_at: "2026-08-05T03:00:00.000Z",
      account_id: "cash",
    })));
    await waitFor(() => expect(screen.queryByRole("button", { name: "거래 저장" })).not.toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "-98,000원" })).toBeInTheDocument();
    expect(screen.getByText("김밥집")).toBeInTheDocument();
    expect(screen.getByText("식비")).toBeInTheDocument();
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

    await waitFor(() => expect(screen.getByText(/네 평가는 ‘납득 가능한 지출’로/)).toBeInTheDocument());
    expect(screen.queryByText(/장부 바닥이 보이는데/)).not.toBeInTheDocument();
    expect(screen.getByText(/내 평가 · 납득 가능한 지출/)).toBeInTheDocument();
  });
});
