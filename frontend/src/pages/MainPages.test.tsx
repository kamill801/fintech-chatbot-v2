import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "../router";
import { LedgerPage, ReportPage, SettingsPage } from "./MainPages";

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
    expect(screen.getByText("아직 기록한 지출이 없어요.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "검색" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "필터" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "2026년 8월" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "달력" })).not.toBeInTheDocument();
  });

  it("shows an honest empty report instead of fabricated category advice", () => {
    window.history.replaceState({}, "", "/report");
    render(<BrowserRouter><ReportPage /></BrowserRouter>);

    expect(screen.getByText("이번 달 지출을 기록해 보세요.")).toBeInTheDocument();
    expect(screen.getByText("지출을 기록하면 카테고리별 흐름을 보여드려요.")).toBeInTheDocument();
    expect(screen.queryByText(/카페 지출이 가장 컸어요/)).not.toBeInTheDocument();
  });
});
