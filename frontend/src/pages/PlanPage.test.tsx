import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { demoPlanState, demoProfile, demoSettings, demoSummary, demoTransactions } from "../demo";
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
    previewPlan.mockResolvedValue(demoPlanState);
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
    expect(screen.getByText(/숫자는 장부 코드가 계산했어요/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "이번 주 AI 브리핑" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /기준 관리|기준 만들기/ })).toHaveAttribute("href", "/settings?demo=1");

    await user.click(screen.getByRole("button", { name: "이대로 유지" }));
    expect(checkInPlan).toHaveBeenCalledWith("maintain");

    matchPlannedExpense.mockRejectedValueOnce(new Error("ineligible"));
    await user.selectOptions(screen.getByRole("combobox", { name: "생일 선물과 연결할 거래" }), "tx-cafe");
    expect(matchPlannedExpense).toHaveBeenCalledWith("planned-gift", "tx-cafe");
    expect(await screen.findByRole("alert")).toHaveTextContent("실제 지출을 연결하지 못했어요");
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
    expect(activatePlan).toHaveBeenCalled();
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
    await user.type(screen.getByRole("textbox", { name: "조정 이유" }), "모임 반영");
    await user.click(screen.getByRole("button", { name: "검토하기" }));

    await waitFor(() => expect(previewPlanRevision).toHaveBeenCalled());
    expect(previewPlanRevision.mock.calls[0][0].planned_expenses).toEqual([
      expect.objectContaining({ name: "병원비", amount_krw: 80_000 }),
    ]);
    expect(screen.getByRole("heading", { name: "변경 전후를 확인하세요" })).toBeInTheDocument();
    expect(screen.getByText("변경 전 남은 생활비")).toBeInTheDocument();
    expect(screen.getByText("변경 후 남은 생활비")).toBeInTheDocument();
    expect(screen.getByText("계획 코치 미리보기")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "변경 내용 적용" }));
    expect(applyPlanRevision).toHaveBeenCalled();
  });
});
