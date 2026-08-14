import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { BrowserRouter } from "./router";

const mocks = vi.hoisted(() => ({
  refresh: vi.fn(),
  useLedger: vi.fn(),
}));

vi.mock("./auth-context", () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useAuth: () => ({ loading: false, session: { user: { id: "user-a" } } }),
}));

vi.mock("./ledger-context", () => ({
  LedgerProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useLedger: mocks.useLedger,
}));

describe("App profile loading", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    mocks.refresh.mockReset();
    mocks.useLedger.mockReturnValue({
      demo: false,
      loading: false,
      profile: null,
      profileLoadError: "서버 응답을 읽지 못했어요.",
      refresh: mocks.refresh,
    });
  });

  it("shows a retry state instead of onboarding when profile loading fails", async () => {
    const user = userEvent.setup();
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(screen.getByRole("heading", { name: "장부를 불러오지 못했어요" })).toBeInTheDocument();
    expect(screen.queryByText("수기로 시작하기")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(mocks.refresh).toHaveBeenCalled();
  });
});
