import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "../router";
import { AgentPage, LedgerPage, ReportPage, SettingsPage } from "./MainPages";

const mocks = vi.hoisted(() => ({
  useLedger: vi.fn(),
}));

vi.mock("../ledger-context", () => ({
  useLedger: mocks.useLedger,
}));

vi.mock("../auth-context", () => ({
  useAuth: () => ({ signOut: vi.fn() }),
}));

describe("live ledger summaries", () => {
  afterEach(cleanup);

  beforeEach(() => {
    window.history.replaceState({}, "", "/ledger");
    mocks.useLedger.mockReturnValue({
      demo: false,
      profile: null,
      settings: { roast_enabled: false, locale: "ko-KR", timezone: "Asia/Seoul" },
      summary: {
        month: "2026-08",
        total_spent_krw: 0,
        by_category_krw: {},
        transaction_count: 0,
        discretionary_budget_krw: 0,
        weekly_briefing: {
          period_start: "2026-08-10",
          period_end: "2026-08-16",
          total_spent_krw: 0,
          transaction_count: 0,
          top_category: null,
          top_category_spent_krw: 0,
          judged_count: 0,
          justified_count: 0,
          caution_count: 0,
          overspending_count: 0,
          insufficient_context_count: 0,
          headline: "이번 주 첫 지출을 기록해 보세요.",
          summary: "거래를 기록하면 이번 주 흐름을 자동으로 묶어 드려요.",
          improvement: "지출 한 건을 기록하면 다음 행동을 구체적으로 제안해 드려요.",
          concern: null,
        },
      },
      transactions: [],
    });
  });

  it("uses the Korean grandma mode name and previews both voices", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/settings");
    mocks.useLedger.mockReturnValue({
      deleteData: vi.fn(),
      demo: true,
      profile: null,
      saveSettings: vi.fn(),
      settings: { roast_enabled: false, locale: "ko-KR", timezone: "Asia/Seoul" },
    });

    render(<BrowserRouter><SettingsPage /></BrowserRouter>);
    expect(screen.getByRole("heading", { name: "욕쟁이 할머니 모드" })).toBeInTheDocument();
    expect(screen.queryByText("Roast 모드")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /말투 미리보기/ }));
    expect(screen.getByText("기본 말투")).toBeInTheDocument();
    expect(screen.getByText("욕쟁이 할머니 말투")).toBeInTheDocument();
    expect(screen.getByText(/이번 주 카페가 벌써 세 번째/)).toBeInTheDocument();
  });

  it("keeps a real zero balance instead of replacing it with demo spending", () => {
    render(<BrowserRouter><LedgerPage /></BrowserRouter>);

    expect(screen.getAllByText("0원").length).toBeGreaterThan(0);
    expect(screen.queryByText("377,500원")).not.toBeInTheDocument();
    expect(screen.getByText("이 날짜에 기록한 거래가 없어요.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "검색" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "필터" })).not.toBeInTheDocument();
    expect(screen.getByRole("grid", { name: "2026년 8월 거래 달력" })).toBeInTheDocument();
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual(["일", "월", "화", "수", "목", "금", "토"]);
  });

  it("uses the calendar as the default ledger and opens entry with the selected date", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue({
      demo: false,
      profile: { monthly_income_krw: 3500000 },
      settings: { roast_enabled: false, locale: "ko-KR", timezone: "Asia/Seoul" },
      summary: {
        month: "2026-08",
        total_spent_krw: 20000,
        by_category_krw: { other: 20000 },
        transaction_count: 1,
        discretionary_budget_krw: 800000,
      },
      transactions: [{
        transaction_id: "tx-calendar",
        amount_krw: 20000,
        merchant: "문구점",
        category: "other",
        description: null,
        occurred_at: "2026-08-16T03:00:00Z",
        source: "manual",
        source_reference: null,
        reason: null,
        status: "judged",
        created_at: "2026-08-16T03:00:00Z",
      }],
    });

    render(<BrowserRouter><LedgerPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: /8월 16일.*20,000원/ }));

    expect(screen.getByRole("heading", { name: "8월 16일 내역" })).toBeInTheDocument();
    expect(screen.getByText("문구점")).toBeInTheDocument();
    const addLink = screen.getByRole("link", { name: "8월 16일에 거래 추가" });
    expect(addLink).toHaveAttribute("href", "/add?date=2026-08-16");
  });

  it("searches the list and narrows records by type, category, and account", async () => {
    const user = userEvent.setup();
    mocks.useLedger.mockReturnValue({
      demo: false,
      settings: {
        roast_enabled: false,
        locale: "ko-KR",
        timezone: "Asia/Seoul",
        accounts: [
          { account_id: "cash", name: "현금", account_type: "cash", opening_balance_krw: 0, archived: false },
          { account_id: "salary", name: "급여 통장", account_type: "bank", opening_balance_krw: 0, archived: false },
        ],
      },
      summary: { month: "2026-08", total_spent_krw: 12000, total_income_krw: 3500000, by_category_krw: { cafe: 12000 }, transaction_count: 2 },
      transactions: [
        { transaction_id: "tx-cafe", amount_krw: 12000, merchant: "카페 온도", category: "cafe", description: "친구 약속", occurred_at: "2026-08-16T03:00:00Z", source: "manual", source_reference: null, reason: null, status: "judged", created_at: "2026-08-16T03:00:00Z", transaction_type: "expense", account_id: "cash", destination_account_id: null, exclude_from_budget: false },
        { transaction_id: "tx-salary", amount_krw: 3500000, merchant: "회사", category: "salary", description: "8월 급여", occurred_at: "2026-08-15T03:00:00Z", source: "manual", source_reference: null, reason: null, status: "recorded", created_at: "2026-08-15T03:00:00Z", transaction_type: "income", account_id: "salary", destination_account_id: null, exclude_from_budget: false },
      ],
    });

    render(<BrowserRouter><LedgerPage /></BrowserRouter>);
    await user.click(screen.getByRole("button", { name: "목록" }));
    expect(screen.getByText("카페 온도")).toBeInTheDocument();
    expect(screen.getByText("회사")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "거래 유형 필터" }), "income");
    expect(screen.queryByText("카페 온도")).not.toBeInTheDocument();
    expect(screen.getByText("회사")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "거래 유형 필터" }), "all");
    await user.selectOptions(screen.getByRole("combobox", { name: "분류 필터" }), "cafe");
    expect(screen.getByText("카페 온도")).toBeInTheDocument();
    expect(screen.queryByText("회사")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "분류 필터" }), "all");
    await user.selectOptions(screen.getByRole("combobox", { name: "계좌 필터" }), "salary");
    expect(screen.queryByText("카페 온도")).not.toBeInTheDocument();
    expect(screen.getByText("회사")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "계좌 필터" }), "all");
    await user.type(screen.getByRole("textbox", { name: "거래 검색" }), "친구");
    expect(screen.getByText("카페 온도")).toBeInTheDocument();
    expect(screen.queryByText("회사")).not.toBeInTheDocument();
  });

  it("shows a judgment-backed weekly AI briefing in normal mode", () => {
    window.history.replaceState({}, "", "/agent");
    mocks.useLedger.mockReturnValue({
      demo: false,
      profile: { discretionary_budget_krw: 800000 },
      settings: { roast_enabled: false, locale: "ko-KR", timezone: "Asia/Seoul" },
      summary: {
        month: "2026-08",
        total_spent_krw: 120000,
        by_category_krw: { cafe: 72000 },
        transaction_count: 5,
        discretionary_budget_krw: 800000,
        weekly_briefing: {
          period_start: "2026-08-10",
          period_end: "2026-08-16",
          total_spent_krw: 72000,
          transaction_count: 3,
          top_category: "cafe",
          top_category_spent_krw: 72000,
          judged_count: 3,
          justified_count: 1,
          caution_count: 2,
          overspending_count: 0,
          insufficient_context_count: 0,
          headline: "주의가 필요한 지출 2건이 보여요.",
          summary: "이번 주 3건에 72,000원을 썼어요.",
          improvement: "다음 카페 약속은 산책으로 바꿔요.",
          concern: {
            transaction_id: "tx-cafe",
            label: "caution",
            category: "cafe",
            merchant: "카페 온도",
            amount_krw: 32000,
            rationale: "카페 지출이 반복됐어요.",
          },
        },
      },
      transactions: [],
    });

    render(<BrowserRouter><AgentPage /></BrowserRouter>);

    expect(screen.getByRole("heading", { name: "이번 주 AI 브리핑" })).toBeInTheDocument();
    expect(screen.getByText("주의가 필요한 지출 2건이 보여요.")).toBeInTheDocument();
    expect(screen.getByText("카페 온도 · 32,000원")).toBeInTheDocument();
    expect(screen.getByText("다음 카페 약속은 산책으로 바꿔요.")).toBeInTheDocument();
    expect(screen.queryByText(/답변 대기/)).not.toBeInTheDocument();
  });

  it("prioritizes learned regret patterns and one concrete next action", () => {
    window.history.replaceState({}, "", "/agent");
    mocks.useLedger.mockReturnValue({
      demo: false,
      profile: { discretionary_budget_krw: 800000 },
      settings: { roast_enabled: false, locale: "ko-KR", timezone: "Asia/Seoul", spending_rules: ["배달은 주 2회까지"] },
      summary: {
        month: "2026-08",
        total_spent_krw: 40000,
        by_category_krw: { food_delivery: 40000 },
        transaction_count: 2,
        reflection_summary: { reflected_count: 2, well_spent_count: 0, unsure_count: 0, regretted_count: 2, regretted_spent_krw: 40000, regret_rate: 1, strongest_regret_category: "food_delivery", goal_delay_days: 3 },
        weekly_briefing: {
          period_start: "2026-08-10", period_end: "2026-08-16", total_spent_krw: 40000, transaction_count: 2,
          top_category: "food_delivery", top_category_spent_krw: 40000, judged_count: 2, justified_count: 0,
          caution_count: 2, overspending_count: 0, insufficient_context_count: 0,
          headline: "이번 주 배달에서 후회한 소비 2건이 보여요.", summary: "이번 주 2건에 40,000원을 썼어요.",
          improvement: "이번 주 배달 지출을 1회 줄이고, 절약한 금액을 비상금에 남겨둬요.", concern: null,
          evidence_state: "learned", regret_pattern: { category: "food_delivery", category_name: "배달", count: 2, spent_krw: 40000 }, goal_impact_days: 3,
        },
        goal: { goal_id: "goal", name: "비상금", target_amount_krw: 10000000, current_amount_krw: 3000000, target_date: "2027-08-03" },
      },
      transactions: [],
    });

    render(<BrowserRouter><AgentPage /></BrowserRouter>);
    expect(screen.getByText("배달 2건 · 40,000원")).toBeInTheDocument();
    expect(screen.getByText(/비상금 예상일에 약 3일/)).toBeInTheDocument();
    expect(screen.getByText("배달은 주 2회까지")).toBeInTheDocument();
    expect(screen.getByText(/이번 주 배달 지출을 1회 줄이고/)).toBeInTheDocument();
  });

  it("shows an honest empty report instead of fabricated category advice", () => {
    window.history.replaceState({}, "", "/report");
    render(<BrowserRouter><ReportPage /></BrowserRouter>);

    expect(screen.getByText("이번 달 지출을 기록해 보세요.")).toBeInTheDocument();
    expect(screen.getByText("지출을 기록하면 카테고리별 흐름을 보여드려요.")).toBeInTheDocument();
    expect(screen.queryByText(/카페 지출이 가장 컸어요/)).not.toBeInTheDocument();
  });
});
