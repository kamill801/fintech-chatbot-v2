import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { BrowserRouter } from "../router";
import { LedgerPage, ReportPage } from "./MainPages";

const mocks = vi.hoisted(() => ({
  useLedger: vi.fn(),
}));

vi.mock("../ledger-context", () => ({
  useLedger: mocks.useLedger,
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

  it("keeps a real zero balance instead of replacing it with demo spending", () => {
    render(<BrowserRouter><LedgerPage /></BrowserRouter>);

    expect(screen.getAllByText("0원").length).toBeGreaterThan(0);
    expect(screen.queryByText("377,500원")).not.toBeInTheDocument();
    expect(screen.getByText("아직 기록한 지출이 없어요.")).toBeInTheDocument();
  });

  it("shows an honest empty report instead of fabricated category advice", () => {
    window.history.replaceState({}, "", "/report");
    render(<BrowserRouter><ReportPage /></BrowserRouter>);

    expect(screen.getByText("이번 달 지출을 기록해 보세요.")).toBeInTheDocument();
    expect(screen.getByText("지출을 기록하면 카테고리별 흐름을 보여드려요.")).toBeInTheDocument();
    expect(screen.queryByText(/카페 지출이 가장 컸어요/)).not.toBeInTheDocument();
  });
});
