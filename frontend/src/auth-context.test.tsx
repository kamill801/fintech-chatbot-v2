import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./auth-context";
import { manualDraftKey, onboardingDraftKey } from "./local-drafts";

const authApi = vi.hoisted(() => ({
  getSession: vi.fn(),
  getUser: vi.fn(),
  onAuthStateChange: vi.fn(),
  updateUser: vi.fn(),
  signInWithPassword: vi.fn(),
  signInWithIdToken: vi.fn(),
  signOut: vi.fn(),
  signUp: vi.fn(),
  unsubscribe: vi.fn(),
}));

const kakao = vi.hoisted(() => ({
  isKakaoCallback: vi.fn(() => false),
  startKakaoLogin: vi.fn(),
  finishKakaoLogin: vi.fn(),
}));

vi.mock("./kakao-login", () => kakao);

vi.mock("./auth-client", () => ({
  authConfigured: true,
  supabase: {
    auth: {
      getSession: authApi.getSession,
      getUser: authApi.getUser,
      onAuthStateChange: authApi.onAuthStateChange,
      updateUser: authApi.updateUser,
      signInWithPassword: authApi.signInWithPassword,
      signInWithIdToken: authApi.signInWithIdToken,
      signOut: authApi.signOut,
      signUp: authApi.signUp,
    },
  },
}));

function AuthActions() {
  const { avatarUrl, displayName, error, introSeen, loading, markIntroSeen, provider, signIn, signInWithKakao, signOut, signUp, userKey } = useAuth();
  if (loading) return <span>loading</span>;
  return (
    <>
      <button type="button" onClick={() => void signIn("user@example.com", "password123")}>login</button>
      <button type="button" onClick={() => void signInWithKakao().catch(() => undefined)}>kakao</button>
      <button type="button" onClick={() => void signUp("new@example.com", "password123")}>signup</button>
      <button type="button" onClick={() => void signOut()}>logout</button>
      <button type="button" onClick={() => void markIntroSeen().catch(() => undefined)}>mark intro</button>
      <output aria-label="intro state">{introSeen ? "seen" : "new"}</output>
      <output aria-label="auth identity">{JSON.stringify({ avatarUrl, displayName, provider, userKey })}</output>
      {error && <p role="alert">{error}</p>}
    </>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    authApi.getSession.mockReset().mockResolvedValue({ data: { session: null }, error: null });
    authApi.getUser.mockReset().mockResolvedValue({ data: { user: null }, error: null });
    authApi.updateUser.mockReset();
    authApi.onAuthStateChange.mockReset().mockReturnValue({ data: { subscription: { unsubscribe: authApi.unsubscribe } } });
    authApi.signInWithPassword.mockReset().mockResolvedValue({ error: null });
    kakao.startKakaoLogin.mockReset().mockResolvedValue(undefined);
    kakao.finishKakaoLogin.mockReset();
    kakao.isKakaoCallback.mockReturnValue(false);
    authApi.signUp.mockReset().mockResolvedValue({ data: { session: { access_token: "token" } }, error: null });
    authApi.signOut.mockReset().mockResolvedValue({ error: null });
    authApi.unsubscribe.mockReset();
  });

  afterEach(cleanup);

  it("uses password authentication for login and signup", async () => {
    const user = userEvent.setup();
    render(<AuthProvider><AuthActions /></AuthProvider>);

    await waitFor(() => expect(screen.queryByText("loading")).not.toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "login" }));
    await user.click(screen.getByRole("button", { name: "signup" }));

    expect(authApi.signInWithPassword).toHaveBeenCalledWith({
      email: "user@example.com",
      password: "password123",
    });
    await user.click(screen.getByRole("button", { name: "kakao" }));
    expect(kakao.startKakaoLogin).toHaveBeenCalledTimes(1);
    expect(authApi.signUp).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "password123",
    });
  });

  it("surfaces a Kakao startup failure without affecting the email path", async () => {
    const user = userEvent.setup();
    kakao.startKakaoLogin.mockRejectedValue(new Error("provider disabled"));
    render(<AuthProvider><AuthActions /></AuthProvider>);

    await waitFor(() => expect(screen.queryByText("loading")).not.toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "kakao" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("카카오 로그인을 시작하지 못했어요.");
  });

  it("waits for the Kakao callback before showing the signed-in app", async () => {
    kakao.isKakaoCallback.mockReturnValue(true);
    const session = { user: { id: "kakao-supabase-user" } };
    kakao.finishKakaoLogin.mockResolvedValue(session);
    render(<AuthProvider><AuthActions /></AuthProvider>);

    await waitFor(() => expect(screen.queryByText("loading")).not.toBeInTheDocument());
    expect(kakao.finishKakaoLogin).toHaveBeenCalledTimes(1);
    expect(authApi.getSession).not.toHaveBeenCalled();
    expect(screen.getByLabelText("auth identity")).toHaveTextContent("kakao-supabase-user");
  });

  it("keeps ledger ownership on the Supabase user ID while exposing Kakao metadata for display", async () => {
    authApi.getSession.mockResolvedValueOnce({
      data: {
        session: {
          user: {
            id: "supabase-user-id",
            email: "mutable@example.com",
            app_metadata: { provider: "kakao" },
            user_metadata: {
              full_name: "변경 가능한 닉네임",
              avatar_url: "https://example.com/profile.png",
            },
          },
        },
      },
      error: null,
    });
    render(<AuthProvider><AuthActions /></AuthProvider>);

    await waitFor(() => expect(screen.queryByText("loading")).not.toBeInTheDocument());

    expect(screen.getByLabelText("auth identity")).toHaveTextContent(JSON.stringify({
      avatarUrl: "https://example.com/profile.png",
      displayName: "변경 가능한 닉네임",
      provider: "kakao",
      userKey: "supabase-user-id",
    }));
  });

  it("loads the account's latest introduction state and saves it without financial data", async () => {
    const user = userEvent.setup();
    const account = { id: "user-a", user_metadata: { jangbu_intro_seen: false } };
    authApi.getSession.mockResolvedValueOnce({ data: { session: { user: account } }, error: null });
    authApi.getUser.mockResolvedValueOnce({ data: { user: account }, error: null });
    authApi.updateUser.mockResolvedValueOnce({
      data: { user: { ...account, user_metadata: { jangbu_intro_seen: true } } },
      error: null,
    });

    render(<AuthProvider><AuthActions /></AuthProvider>);
    expect(await screen.findByLabelText("intro state")).toHaveTextContent("new");
    await user.click(screen.getByRole("button", { name: "mark intro" }));

    expect(authApi.updateUser).toHaveBeenCalledWith({ data: { jangbu_intro_seen: true } });
    expect(screen.getByLabelText("intro state")).toHaveTextContent("seen");
  });

  it("uses refreshed account metadata rather than an older cached session", async () => {
    authApi.getSession.mockResolvedValueOnce({
      data: { session: { user: { id: "user-a", user_metadata: {} } } }, error: null,
    });
    authApi.getUser.mockResolvedValueOnce({
      data: { user: { id: "user-a", user_metadata: { jangbu_intro_seen: true } } }, error: null,
    });

    render(<AuthProvider><AuthActions /></AuthProvider>);
    expect(await screen.findByLabelText("intro state")).toHaveTextContent("seen");
  });

  it("clears user-scoped financial drafts after sign-out succeeds", async () => {
    const user = userEvent.setup();
    authApi.getSession.mockResolvedValueOnce({
      data: { session: { user: { id: "user-a", email: "a@example.com" } } },
      error: null,
    });
    window.localStorage.setItem(manualDraftKey("user-a"), "{}");
    window.sessionStorage.setItem(onboardingDraftKey("user-a"), "{}");
    window.localStorage.setItem(manualDraftKey("user-b"), "{}");

    render(<AuthProvider><AuthActions /></AuthProvider>);
    await waitFor(() => expect(screen.queryByText("loading")).not.toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "logout" }));

    expect(authApi.signOut).toHaveBeenCalled();
    expect(window.localStorage.getItem(manualDraftKey("user-a"))).toBeNull();
    expect(window.sessionStorage.getItem(onboardingDraftKey("user-a"))).toBeNull();
    expect(window.localStorage.getItem(manualDraftKey("user-b"))).toBe("{}");
  });
});
