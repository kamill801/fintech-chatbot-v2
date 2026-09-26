import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { onboardingDraftKey, onboardingStageKey } from "./local-drafts";
import { BrowserRouter } from "./router";

const mocks = vi.hoisted(() => ({
  refresh: vi.fn(),
  useAuth: vi.fn(),
  useLedger: vi.fn(),
}));

vi.mock("./auth-context", () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useAuth: mocks.useAuth,
}));

vi.mock("./pages/HomeFlow", () => ({
  HomePage: () => <h1>홈 화면</h1>,
  ManualTransactionPage: () => null,
  ReasonPage: () => null,
}));

vi.mock("./ledger-context", () => ({
  LedgerProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useLedger: mocks.useLedger,
}));

describe("App profile loading", () => {
  afterEach(cleanup);
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    window.sessionStorage.clear();
    mocks.refresh.mockReset();
    mocks.useAuth.mockReturnValue({
      loading: false,
      session: { user: { id: "user-a" } },
      userKey: "user-a",
      introSeen: false,
      markIntroSeen: vi.fn(),
      signOut: vi.fn(),
    });
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

  it("shows the service introduction to a new account", async () => {
    mocks.useLedger.mockReturnValue({ demo: false, loading: false, profile: null, profileLoadError: null });
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: "장부 AI" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "시작하기" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/onboarding/trust");
  });

  it("returns an account that saw the introduction to financial setup", async () => {
    mocks.useAuth.mockReturnValue({
      ...mocks.useAuth(),
      introSeen: true,
    });
    mocks.useLedger.mockReturnValue({ demo: false, loading: false, profile: null, profileLoadError: null });
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: /내 예산 기준/ })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/onboarding/baseline");
    expect(screen.queryByRole("heading", { name: "장부 AI" })).not.toBeInTheDocument();
  });

  it("advances from the budget baseline through the goal step without bouncing back", async () => {
    const user = userEvent.setup();
    mocks.useAuth.mockReturnValue({ ...mocks.useAuth(), introSeen: true });
    mocks.useLedger.mockReturnValue({ demo: false, loading: false, profile: null, profileLoadError: null });
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: /내 예산 기준/ })).toBeInTheDocument();
    const assets = screen.getByRole("textbox", { name: "보유 현금·예금 금액" });
    await user.clear(assets);
    await user.type(assets, "40000000");
    await user.click(screen.getByRole("button", { name: "다음: 목표 설정" }));
    expect(await screen.findByRole("heading", { name: /저축 목표/ })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/onboarding/goal");
    expect(JSON.parse(window.sessionStorage.getItem(onboardingDraftKey("user-a")) ?? "{}").liquid_assets_krw).toBe(40_000_000);
    expect(window.sessionStorage.getItem(onboardingStageKey("user-a"))).toBe("goal");

    await user.click(screen.getByRole("button", { name: "다음: 기록 방식" }));
    expect(await screen.findByRole("heading", { name: /장부 기록/ })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/onboarding/source");
    expect(window.sessionStorage.getItem(onboardingStageKey("user-a"))).toBe("source");
  });

  it("shows an actionable error instead of silently staying on the budget step when draft storage fails", async () => {
    const user = userEvent.setup();
    mocks.useAuth.mockReturnValue({ ...mocks.useAuth(), introSeen: true });
    mocks.useLedger.mockReturnValue({ demo: false, loading: false, profile: null, profileLoadError: null });
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: /내 예산 기준/ })).toBeInTheDocument();
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("storage unavailable"); });
    try {
      await user.click(screen.getByRole("button", { name: "다음: 목표 설정" }));
      expect(screen.getByRole("alert")).toHaveTextContent("입력 내용을 임시 저장하지 못했어요");
      expect(window.location.pathname).toBe("/onboarding/baseline");
    } finally {
      setItem.mockRestore();
    }
  });

  it("takes a returning account with a profile straight to Home", async () => {
    window.history.replaceState({}, "", "/onboarding/trust");
    mocks.useLedger.mockReturnValue({ demo: false, loading: false, profile: {}, profileLoadError: null });
    render(<BrowserRouter><App /></BrowserRouter>);

    expect(await screen.findByRole("heading", { name: "홈 화면" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
  });
});
