import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./auth-context";
import { manualDraftKey, onboardingDraftKey } from "./local-drafts";

const authApi = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signInWithPassword: vi.fn(),
  signOut: vi.fn(),
  signUp: vi.fn(),
  unsubscribe: vi.fn(),
}));

vi.mock("./auth-client", () => ({
  authConfigured: true,
  supabase: {
    auth: {
      getSession: authApi.getSession,
      onAuthStateChange: authApi.onAuthStateChange,
      signInWithPassword: authApi.signInWithPassword,
      signOut: authApi.signOut,
      signUp: authApi.signUp,
    },
  },
}));

function AuthActions() {
  const { loading, signIn, signOut, signUp } = useAuth();
  if (loading) return <span>loading</span>;
  return (
    <>
      <button type="button" onClick={() => void signIn("user@example.com", "password123")}>login</button>
      <button type="button" onClick={() => void signUp("new@example.com", "password123")}>signup</button>
      <button type="button" onClick={() => void signOut()}>logout</button>
    </>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    authApi.getSession.mockReset().mockResolvedValue({ data: { session: null }, error: null });
    authApi.onAuthStateChange.mockReset().mockReturnValue({ data: { subscription: { unsubscribe: authApi.unsubscribe } } });
    authApi.signInWithPassword.mockReset().mockResolvedValue({ error: null });
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
    expect(authApi.signUp).toHaveBeenCalledWith({
      email: "new@example.com",
      password: "password123",
    });
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
