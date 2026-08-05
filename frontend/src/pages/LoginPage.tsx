import { LockKey } from "@phosphor-icons/react";
import { type FormEvent, useState } from "react";
import { useAuth } from "../auth-context";
import { BookkeeperMark, Highlight, PrimaryButton, Surface } from "../components";

type AuthMode = "login" | "signup";

export function LoginPage() {
  const { configured, error, signIn, signUp } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [confirmationRequired, setConfirmationRequired] = useState(false);

  function changeMode(nextMode: AuthMode) {
    setMode(nextMode);
    setPassword("");
    setPasswordConfirm("");
    setFormError(null);
    setConfirmationRequired(false);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!configured || !email.trim() || !password) return;
    if (mode === "signup" && password !== passwordConfirm) {
      setFormError("비밀번호가 서로 일치하지 않아요.");
      return;
    }

    setFormError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await signIn(email.trim(), password);
        return;
      }
      const signedIn = await signUp(email.trim(), password);
      setConfirmationRequired(!signedIn);
    } catch {
      setConfirmationRequired(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-hero">
        <div>
          <span className="auth-kicker">AI 가계부 에이전트</span>
          <h1>내 돈을 맡기는 게 아니라,<br /><Highlight>판단</Highlight>을 같이 하는 거야.</h1>
          <p>로그인하면 내 장부와 목표를 기기 사이에서 안전하게 이어서 관리해요.</p>
        </div>
        <BookkeeperMark />
      </section>

      <Surface className="auth-card">
        <span className="auth-icon"><LockKey size={28} /></span>
        <div>
          <h2>{mode === "login" ? "로그인" : "회원가입"}</h2>
          <p>{mode === "login" ? "이메일과 비밀번호로 바로 시작해요." : "내 장부를 안전하게 보관할 계정을 만들어요."}</p>
        </div>
        <div className="auth-mode-switch" role="tablist" aria-label="인증 방식">
          <button type="button" role="tab" aria-selected={mode === "login"} onClick={() => changeMode("login")}>로그인</button>
          <button type="button" role="tab" aria-selected={mode === "signup"} onClick={() => changeMode("signup")}>회원가입</button>
        </div>
        <form onSubmit={(event) => void submit(event)}>
          <label htmlFor="login-email">이메일</label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            inputMode="email"
            placeholder="name@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="login-password">비밀번호</label>
          <input
            id="login-password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={8}
            placeholder="8자 이상 입력"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {mode === "signup" && (
            <>
              <label htmlFor="login-password-confirm">비밀번호 확인</label>
              <input
                id="login-password-confirm"
                type="password"
                autoComplete="new-password"
                minLength={8}
                placeholder="비밀번호 다시 입력"
                value={passwordConfirm}
                onChange={(event) => setPasswordConfirm(event.target.value)}
                required
              />
            </>
          )}
          <PrimaryButton type="submit" disabled={submitting || !configured}>
            {submitting ? "확인 중" : mode === "login" ? "로그인" : "회원가입하고 시작"}
          </PrimaryButton>
        </form>
        {!configured && <p className="form-error" role="alert">인증 서비스 연결이 아직 완료되지 않았어요.</p>}
        {formError && <p className="form-error" role="alert">{formError}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        {confirmationRequired && (
          <p className="form-notice" role="status">계정은 생성됐지만 이메일 확인 설정이 켜져 있어요. 메일 확인 후 로그인해 주세요.</p>
        )}
      </Surface>

      <p className="auth-privacy"><LockKey size={17} /> 로그인 토큰은 장부 서버에서 검증하며 이메일은 금융 기록에 저장하지 않아요.</p>
      <a className="auth-demo-link" href="/?demo=1">계정 없이 데모 보기</a>
    </main>
  );
}
