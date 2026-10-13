import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { demoPlanState, demoProfile, demoSettings, demoSummary, demoTransactions } from "../demo";
import { ApiError } from "../api";
import { BrowserRouter } from "../router";
import type { SpendingPlanState } from "../types";
import { PlanPage } from "./PlanPage";


const mocks = vi.hoisted(() => ({ useAuth: vi.fn(), useLedger: vi.fn() }));

vi.mock("../ledger-context", () => ({ useLedger: mocks.useLedger }));
vi.mock("../auth-context", () => ({ useAuth: mocks.useAuth }));

describe("spending plan flow", () => {
  const activatePlan = vi.fn();
  const applyPlanRevision = vi.fn();
  const checkInPlan = vi.fn();
  const matchPlannedExpense = vi.fn();
  const previewPlan = vi.fn();
  const previewPlanRevision = vi.fn();

  beforeEach(() => {
    window.history.replaceState({}, "", "/plan?demo=1");
    vi.clearAllMocks();
    window.sessionStorage.clear();
    mocks.useAuth.mockReturnValue({ userKey: "plan-user" });
    activatePlan.mockResolvedValue(demoPlanState);
    applyPlanRevision.mockResolvedValue(demoPlanState);
    checkInPlan.mockResolvedValue(demoPlanState);
    matchPlannedExpense.mockResolvedValue(demoPlanState);
    previewPlan.mockResolvedValue({ ...demoPlanState, preview_token: "setup-token" });
    previewPlanRevision.mockResolvedValue({
      from_version: 1,
      to_version: 2,
      before: demoPlanState.original_plan,
      after: { ...demoPlanState.original_plan, version: 2 },
      before_progress: demoPlanState.progress,
      after_progress: { ...demoPlanState.progress, flexible_remaining_krw: 372_500 },
      budget_change_krw: 50_000,
      flexible_remaining_change_krw: 50_000,
      narrative: demoPlanState.narrative,
      preview_token: "revision-token",
    });
  });

  afterEach(cleanup);

  function value(plan: SpendingPlanState | null = demoPlanState) {
    return {
      activatePlan,
      applyPlanRevision,
      checkInPlan,
      demo: true,
      matchPlannedExpense,
      plan,
      previewPlan,
      previewPlanRevision,
      profile: demoProfile,
      settings: demoSettings,
      summary: demoSummary,
      transactions: demoTransactions,
    };
  }

  it("shows active progress, bounded narrative, check-in, and manual matching", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue(value());
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    expect(screen.getByText("계획상 남은 생활비")).toBeInTheDocument();
    expect(screen.getByText("현재 구간은 계획 안에서 움직이고 있어요.")).toBeInTheDocument();
    expect(screen.getByText(/금액은 최신 장부 기준이에요/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "이번 주 AI 브리핑" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /기준 관리|기준 만들기/ })).toHaveAttribute("href", "/settings?demo=1");

    await user.click(screen.getByRole("button", { name: "이대로 유지" }));
    expect(checkInPlan).toHaveBeenCalledWith("maintain");
    expect(await screen.findByRole("status")).toHaveTextContent("유지한다고 기록");

    matchPlannedExpense.mockRejectedValueOnce(new Error("ineligible"));
    await user.selectOptions(screen.getByRole("combobox", { name: "생일 선물과 연결할 거래" }), "tx-cafe");
    expect(matchPlannedExpense).toHaveBeenCalledWith("planned-gift", "tx-cafe");
    expect(await screen.findByRole("alert")).toHaveTextContent("실제 지출을 연결하지 못했어요");
  });

  it("treats a completed plan as history and starts the next period draft", async () => {
    const user = userEvent.setup();
    const completedPlan: SpendingPlanState = {
      ...demoPlanState,
      progress: {
        ...demoPlanState.progress,
        period_status: "completed",
        current_segment_id: null,
      },
    };
    mocks.useLedger.mockReturnValue(value(completedPlan));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    expect(screen.getByText(/완료된 계획 · v1/)).toBeInTheDocument();
    expect(screen.getByText("종료됨")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "이 기간 계획은 마무리됐어요" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "이대로 유지" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "다음 기간 계획 세우기" }));

    expect(screen.getByText("생활비 계획 1/3")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "다음 기간에 쓸 돈을 정해요" })).toBeInTheDocument();
    expect(screen.getByLabelText("시작일")).toHaveValue("2026-09-01");
    expect(screen.getByLabelText("종료일")).toHaveValue("2026-09-07");
    expect(screen.queryByRole("textbox", { name: "조정 이유" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.click(screen.getByRole("button", { name: "검토하기" }));

    await waitFor(() => expect(previewPlanRevision).toHaveBeenCalledWith(
      expect.objectContaining({ period_start: "2026-09-01", period_end: "2026-09-07" }),
      "다음 기간 계획 시작",
    ));
    expect(previewPlan).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { name: "다음 기간 계획을 시작할까요?" })).toBeInTheDocument();
    expect(screen.queryByText("변경 전 남은 생활비")).not.toBeInTheDocument();
    expect(screen.getByText("다음 기간 예상 생활비")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "다음 기간 계획 시작" }));
    expect(applyPlanRevision).toHaveBeenCalledWith(
      expect.objectContaining({ period_start: "2026-09-01", period_end: "2026-09-07" }),
      "다음 기간 계획 시작",
      "revision-token",
    );
    expect(activatePlan).not.toHaveBeenCalled();
  });

  it("creates a plan through period, priorities, review, and explicit confirmation", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue(value(null));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    expect(screen.getByText("생활비 계획 1/3")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.type(screen.getByRole("textbox", { name: /우선순위/ }), "친구와의 약속");
    await user.click(screen.getByRole("button", { name: "검토하기" }));

    await waitFor(() => expect(previewPlan).toHaveBeenCalled());
    expect(screen.getByRole("heading", { name: "이 계획으로 시작할까요?" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "확인하고 계획 시작" }));
    expect(activatePlan).toHaveBeenCalledWith(expect.objectContaining({ confirmed_budget_krw: expect.any(Number) }), "setup-token");
  });

  it.each(["next", "revise"] as const)("returns to the saved plan without discarding a %s draft", async (mode) => {
    const user = userEvent.setup();
    const completedPlan = { ...demoPlanState, progress: { ...demoPlanState.progress, period_status: "completed" as const, current_segment_id: null } };
    mocks.useLedger.mockReturnValue(value(completedPlan));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    await user.click(screen.getByRole("button", { name: mode === "next" ? "다음 기간 계획 세우기" : "계획 수정" }));
    fireEvent.change(screen.getByRole("textbox", { name: "확정 생활비 예산" }), { target: { value: "700000" } });
    await user.click(screen.getByRole("button", { name: /^다음$/ }));
    await user.clear(screen.getByRole("textbox", { name: /우선순위/ }));
    await user.type(screen.getByRole("textbox", { name: /우선순위/ }), "주말 약속 유지하기");
    if (mode === "revise") await user.type(screen.getByRole("textbox", { name: "조정 이유" }), "지출 범위 조정");

    await user.click(screen.getByRole("button", { name: "기존 계획 보기" }));
    expect(screen.getByText(/완료된 계획 · v1/)).toBeInTheDocument();
    expect(applyPlanRevision).not.toHaveBeenCalled();
    expect(activatePlan).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "작성 중인 계획 이어하기" }));
    expect(screen.getByText("생활비 계획 2/3")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /우선순위/ })).toHaveValue("주말 약속 유지하기");
    if (mode === "revise") expect(screen.getByRole("textbox", { name: "조정 이유" })).toHaveValue("지출 범위 조정");
    await user.click(screen.getByRole("button", { name: /^이전$/ }));
    expect(screen.getByRole("textbox", { name: "확정 생활비 예산" })).toHaveValue("700,000");
  });

  it("blocks returning to the saved plan while confirmation is being persisted", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue(value());
    applyPlanRevision.mockReturnValueOnce(new Promise(() => {}));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "계획 수정" }));
    await user.click(screen.getByRole("button", { name: /^다음$/ }));
    await user.type(screen.getByRole("textbox", { name: "조정 이유" }), "예산 조정");
    await user.click(screen.getByRole("button", { name: "검토하기" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "변경 내용 적용" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "변경 내용 적용" }));
    expect(screen.getByRole("button", { name: "기존 계획 보기" })).toBeDisabled();
  });

  it("rejects a plan period longer than the server's 366-day limit", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue(value(null));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    fireEvent.change(screen.getByLabelText("시작일"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("종료일"), { target: { value: "2027-01-03" } });
    await user.click(screen.getByRole("button", { name: "다음" }));

    expect(screen.getByRole("alert")).toHaveTextContent("366일 이내");
    expect(screen.getByText("생활비 계획 1/3")).toBeInTheDocument();
  });

  it("blocks confirmation when the latest preview request failed after edits", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue(value(null));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.type(screen.getByRole("textbox", { name: /우선순위/ }), "친구와의 약속");
    await user.click(screen.getByRole("button", { name: "검토하기" }));

    await waitFor(() => expect(previewPlan).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: "확인하고 계획 시작" })).toBeEnabled();

    previewPlan.mockRejectedValueOnce(new Error("preview unavailable"));
    await user.click(screen.getByRole("button", { name: "다시 수정" }));
    await user.type(screen.getByRole("textbox", { name: /우선순위/ }), "\n건강");
    await user.click(screen.getByRole("button", { name: "검토하기" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("계획 미리보기를 만들지 못했어요");
    expect(screen.getByRole("button", { name: "확인하고 계획 시작" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "확인하고 계획 시작" }));
    expect(activatePlan).not.toHaveBeenCalled();
  });

  it("validates period order and refuses to silently trim priorities", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue(value(null));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    await user.clear(screen.getByLabelText("시작일"));
    await user.type(screen.getByLabelText("시작일"), "2026-09-30");
    await user.clear(screen.getByLabelText("종료일"));
    await user.type(screen.getByLabelText("종료일"), "2026-09-01");
    await user.click(screen.getByRole("button", { name: "다음" }));
    expect(screen.getByRole("alert")).toHaveTextContent("종료일은 시작일 이후");

    await user.clear(screen.getByLabelText("종료일"));
    await user.type(screen.getByLabelText("종료일"), "2026-09-30");
    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.type(screen.getByRole("textbox", { name: /우선순위/ }), "하나\n둘\n셋\n넷");
    await user.click(screen.getByRole("button", { name: "검토하기" }));

    expect(screen.getByRole("alert")).toHaveTextContent("우선순위는 최대 3개");
    expect(previewPlan).not.toHaveBeenCalled();
  });

  it("requires a revision preview before applying the new version", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue(value());
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    await user.click(screen.getByRole("button", { name: "계획 수정" }));
    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.click(screen.getByRole("button", { name: "생일 선물 삭제" }));
    await user.type(screen.getByRole("textbox", { name: "이름" }), "병원비");
    await user.type(screen.getByRole("textbox", { name: "새 예정 지출 금액" }), "80000");
    await user.click(screen.getByRole("button", { name: "예정 지출 추가" }));
    await user.type(screen.getByRole("textbox", { name: "조정 이유" }), "  모임 반영  ");
    await user.click(screen.getByRole("button", { name: "검토하기" }));

    await waitFor(() => expect(previewPlanRevision).toHaveBeenCalled());
    expect(previewPlanRevision).toHaveBeenCalledWith(expect.anything(), "모임 반영");
    expect(previewPlanRevision.mock.calls[0][0].planned_expenses).toEqual([
      expect.objectContaining({ name: "병원비", amount_krw: 80_000 }),
    ]);
    expect(screen.getByRole("heading", { name: "변경 전후를 확인하세요" })).toBeInTheDocument();
    expect(screen.getByText("변경 전 남은 생활비")).toBeInTheDocument();
    expect(screen.getByText("변경 후 남은 생활비")).toBeInTheDocument();
    expect(screen.getByText("계획 코치 미리보기")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "변경 내용 적용" }));
    expect(applyPlanRevision).toHaveBeenCalledWith(
      expect.objectContaining({ planned_expenses: [expect.objectContaining({ name: "병원비" })] }),
      "모임 반영",
      "revision-token",
    );
  });

  it("keeps the draft and offers a new review when a preview token is no longer valid", async () => {
    const user = userEvent.setup();
    activatePlan.mockRejectedValueOnce(new ApiError("plan_preview_conflict", "changed", 409));
    mocks.useLedger.mockReturnValue(value(null));
    render(<BrowserRouter><PlanPage /></BrowserRouter>);

    await user.click(screen.getByRole("button", { name: "다음" }));
    await user.type(screen.getByRole("textbox", { name: /우선순위/ }), "배달 줄이기");
    await user.click(screen.getByRole("button", { name: "검토하기" }));
    await waitFor(() => expect(previewPlan).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "확인하고 계획 시작" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("다시 만들어야");
    expect(screen.getByText(/우선순위: 배달 줄이기/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "확인하고 계획 시작" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "다시 검토하기" }));
    await waitFor(() => expect(previewPlan).toHaveBeenCalledTimes(2));
  });
});
