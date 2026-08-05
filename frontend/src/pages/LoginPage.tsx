import { EnvelopeSimple, LockKey } from "@phosphor-icons/react";
import { type FormEvent, useState } from "react";
import { useAuth } from "../auth-context";
import { BookkeeperMark, Highlight, PrimaryButton, Surface } from "../components";

export function LoginPage() {
  const { configured, error, signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!configured || !email.trim()) return;
    setSubmitting(true);
    try {
      await signIn(email.trim());
      setSent(true);
    } catch {
      setSent(false);
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
        <span className="auth-icon"><EnvelopeSimple size={28} /></span>
        <div>
          <h2>{sent ? "메일함을 확인해 주세요" : "이메일로 시작하기"}</h2>
          <p>{sent ? `${email}로 로그인 링크를 보냈어요.` : "비밀번호 없이 일회용 로그인 링크를 보내드려요."}</p>
        </div>
        {!sent && (
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
            <PrimaryButton type="submit" disabled={submitting || !configured}>
              {submitting ? "보내는 중" : "로그인 링크 받기"}
            </PrimaryButton>
          </form>
        )}
        {sent && <button className="text-button" onClick={() => setSent(false)}>다른 이메일 사용</button>}
        {!configured && <p className="form-error" role="alert">인증 서비스 연결이 아직 완료되지 않았어요.</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
      </Surface>

      <p className="auth-privacy"><LockKey size={17} /> 로그인 토큰은 장부 서버에서 검증하며 이메일은 금융 기록에 저장하지 않아요.</p>
      <a className="auth-demo-link" href="/?demo=1">계정 없이 데모 보기</a>
    </main>
  );
}
