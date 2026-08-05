import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";

const auth = vi.hoisted(() => ({
  signIn: vi.fn(),
  signUp: vi.fn(),
}));

vi.mock("../auth-context", () => ({
  useAuth: () => ({
    configured: true,
    error: null,
    signIn: auth.signIn,
    signUp: auth.signUp,
  }),
}));

describe("LoginPage", () => {
  afterEach(cleanup);

  beforeEach(() => {
    auth.signIn.mockReset();
    auth.signUp.mockReset();
    auth.signUp.mockResolvedValue(true);
  });

  it("logs in with an email and password instead of sending a magic link", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("이메일"), "user@example.com");
    await user.type(screen.getByLabelText("비밀번호"), "password123");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(auth.signIn).toHaveBeenCalledWith("user@example.com", "password123");
    expect(auth.signUp).not.toHaveBeenCalled();
    expect(screen.queryByText(/로그인 링크/)).not.toBeInTheDocument();
  });

  it("creates an account only after both password fields match", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.click(screen.getByRole("tab", { name: "회원가입" }));
    await user.type(screen.getByLabelText("이메일"), "new@example.com");
    await user.type(screen.getByLabelText("비밀번호", { selector: "#login-password" }), "password123");
    await user.type(screen.getByLabelText("비밀번호 확인"), "different123");
    await user.click(screen.getByRole("button", { name: "회원가입하고 시작" }));

    expect(screen.getByRole("alert")).toHaveTextContent("비밀번호가 서로 일치하지 않아요.");
    expect(auth.signUp).not.toHaveBeenCalled();
  });
});
