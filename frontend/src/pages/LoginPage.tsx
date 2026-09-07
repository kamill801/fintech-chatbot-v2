import { ChatCircleDots, LockKey } from "@phosphor-icons/react";
import { type FormEvent, useState } from "react";
import { useAuth } from "../auth-context";
import { BookkeeperMark, Highlight, PrimaryButton, Surface } from "../components";

type AuthMode = "login" | "signup";

export function LoginPage() {
  const { configured, error, signIn, signInWithKakao, signUp } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [kakaoSubmitting, setKakaoSubmitting] = useState(false);
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

  async function startKakaoLogin() {
    if (!configured || kakaoSubmitting) return;
    setFormError(null);
    setConfirmationRequired(false);
    setKakaoSubmitting(true);
    try {
      await signInWithKakao();
    } catch {
      // The shared auth error remains visible and email login stays available.
    } finally {
      setKakaoSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-hero">
        <div>
          <span className="auth-kicker">AI 가계부 에이전트</span>
          <h1>쓴 돈은 기록하고,<br /><Highlight>후회할 소비</Highlight>는 줄이게.</h1>
          <p>예산과 목표, 내가 남긴 소비 평가를 함께 보고 다음 주에 바꿀 행동 하나를 알려드려요.</p>
        </div>
        <BookkeeperMark />
      </section>

      <Surface className="auth-card">
        <span className="auth-icon"><LockKey size={28} /></span>
        <div>
          <h2>내 장부 시작하기</h2>
          <p>카카오로 빠르게 시작하거나 이메일 계정을 사용할 수 있어요.</p>
        </div>
        <button
          className="kakao-login-button"
          type="button"
          disabled={!configured || kakaoSubmitting || submitting}
          onClick={() => void startKakaoLogin()}
        >
          <ChatCircleDots aria-hidden="true" size={23} weight="fill" />
          <span>{kakaoSubmitting ? "카카오 연결 중" : "카카오로 시작하기"}</span>
        </button>
        <div className="auth-divider"><span>또는 이메일로 계속</span></div>
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

      <p className="auth-privacy"><LockKey size={17} /> 로그인 정보와 금융 기록은 분리하고, 장부 소유권은 인증된 사용자 ID로만 확인해요.</p>
      <a className="auth-demo-link" href="/?demo=1">계정 없이 데모 보기</a>
    </main>
  );
}
