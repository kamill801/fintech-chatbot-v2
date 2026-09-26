import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Bank,
  BookOpenText,
  CheckCircle,
  PencilSimple,
  SignOut,
  Wallet,
} from "@phosphor-icons/react";
import { BookkeeperMark, CurrencyInput, Highlight, PrimaryButton, Surface } from "../components";
import { demoProfile } from "../demo";
import { useAuth } from "../auth-context";
import { useLedger } from "../ledger-context";
import { onboardingDraftKey, onboardingStageKey } from "../local-drafts";
import { useNavigate } from "../router";
import type { Profile } from "../types";
import { formatWon, withDemo } from "../utils";

function readDraft(key: string): Profile {
  try {
    const saved = window.sessionStorage.getItem(key);
    return saved ? (JSON.parse(saved) as Profile) : demoProfile;
  } catch {
    return demoProfile;
  }
}

function writeDraft(key: string, stageKey: string, profile: Profile, nextStage: "goal" | "source") {
  window.sessionStorage.setItem(key, JSON.stringify(profile));
  window.sessionStorage.setItem(stageKey, nextStage);
}

function StepHeader({ step }: { step: number }) {
  const { demo } = useLedger();
  const { signOut, userKey } = useAuth();
  const navigate = useNavigate();
  const [logoutError, setLogoutError] = useState(false);

  useEffect(() => {
    const stage = step === 2 ? "baseline" : step === 3 ? "goal" : "source";
    try {
      window.sessionStorage.setItem(onboardingStageKey(userKey, demo), stage);
    } catch {
      // The setup flow still works when browser storage is unavailable.
    }
  }, [demo, step, userKey]);

  return (
    <>
      <div className="step-header">
        {step > 2 ? (
          <button className="icon-button" aria-label="이전 단계" onClick={() => navigate(-1)}><ArrowLeft size={28} /></button>
        ) : <span />}
        <span><strong>{step - 1}</strong> / 3</span>
        {!demo && <button className="onboarding-signout" type="button" onClick={() => void signOut().catch(() => setLogoutError(true))}>로그아웃</button>}
      </div>
      {logoutError && <p className="form-error" role="alert">로그아웃하지 못했어요. 다시 시도해 주세요.</p>}
    </>
  );
}

function MoneyEditRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange(value: number): void;
}) {
  return (
    <div className="money-edit-row">
      <label htmlFor={`money-${label}`}>{label}</label>
      <PencilSimple size={19} aria-hidden="true" />
      <CurrencyInput id={`money-${label}`} ariaLabel={`${label} 금액`} value={value} onChange={onChange} />
    </div>
  );
}

export function OnboardingTrust() {
  const { demo } = useLedger();
  const { markIntroSeen, signOut } = useAuth();
  const navigate = useNavigate();
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState(false);

  async function start() {
    setStarting(true);
    setStartError(false);
    try {
      if (!demo) await markIntroSeen();
      navigate(withDemo("/onboarding/baseline", demo));
    } catch {
      setStartError(true);
      setStarting(false);
    }
  }

  async function logout() {
    setLoggingOut(true);
    setLogoutError(false);
    try {
      await signOut();
    } catch {
      setLogoutError(true);
      setLoggingOut(false);
    }
  }

  return (
    <main className="onboarding-page welcome-page">
      <div className="welcome-content">
        <p className="welcome-label">AI 가계부 에이전트</p>
        <h1>장부 AI</h1>
        <p>지출을 기록하고, 예산과 소비 계획을 함께 관리하세요.</p>
      </div>
      <div className="welcome-actions">
        {startError && <p className="form-error" role="alert">시작 상태를 저장하지 못했어요. 다시 시도해 주세요.</p>}
        <PrimaryButton disabled={starting} onClick={() => void start()}>{starting ? "시작하는 중" : "시작하기"}</PrimaryButton>
        <details className="disclosure welcome-disclosure">
          <summary>데이터 처리 방식 보기</summary>
          <p>직접 입력한 기록은 장부에 보관하고, AI에는 판단에 필요한 정보만 전달합니다. 계좌를 연결하지 않아도 사용할 수 있어요.</p>
        </details>
        {!demo && <button className="logout-button" type="button" disabled={loggingOut} onClick={() => void logout()}><SignOut size={18} /> {loggingOut ? "로그아웃 중" : "로그아웃"}</button>}
        {logoutError && <p role="alert">로그아웃하지 못했어요. 다시 시도해 주세요.</p>}
      </div>
    </main>
  );
}

export function OnboardingBaseline() {
  const { demo } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const draftKey = onboardingDraftKey(userKey, demo);
  const [draft, setDraft] = useState(() => readDraft(draftKey));
  const [saveError, setSaveError] = useState(false);
  const update = (key: keyof Profile, value: number) => setDraft((current) => ({ ...current, [key]: value }));
  const freeMoney = Math.max(0, draft.monthly_income_krw - draft.fixed_expenses_krw - draft.monthly_debt_payment_krw - draft.discretionary_budget_krw);

  function continueToGoal() {
    setSaveError(false);
    try {
      writeDraft(draftKey, onboardingStageKey(userKey, demo), draft, "goal");
      navigate(withDemo("/onboarding/goal", demo));
    } catch {
      setSaveError(true);
    }
  }

  return (
    <main className="onboarding-page baseline-page">
      <StepHeader step={2} />
      <div className="onboarding-title with-mark">
        <div>
          <h1>내 <Highlight>예산 기준</Highlight>을<br />정해요.</h1>
          <p>월 수입과 고정지출을 입력해 생활비 예산을 확인해 보세요.</p>
        </div>
        <BookkeeperMark compact />
      </div>
      <Surface className="edit-sheet">
        <MoneyEditRow label="보유 현금·예금" value={draft.liquid_assets_krw} onChange={(value) => update("liquid_assets_krw", value)} />
        <MoneyEditRow label="월 수입" value={draft.monthly_income_krw} onChange={(value) => update("monthly_income_krw", value)} />
        <MoneyEditRow label="고정지출" value={draft.fixed_expenses_krw} onChange={(value) => update("fixed_expenses_krw", value)} />
        <MoneyEditRow label="빚 상환" value={draft.monthly_debt_payment_krw} onChange={(value) => update("monthly_debt_payment_krw", value)} />
        <MoneyEditRow label="생활비 예산" value={draft.discretionary_budget_krw} onChange={(value) => update("discretionary_budget_krw", Math.max(1, value))} />
      </Surface>
      <div className="goal-callout"><Wallet size={27} /><span>매달 자유롭게 쓸 돈의 기준이에요</span><strong>{formatWon(draft.discretionary_budget_krw)}</strong></div>
      {freeMoney > 0 && <p className="baseline-note">기준을 지키면 매달 {formatWon(freeMoney)}을 남길 수 있어요.</p>}
      {saveError && <p className="form-error" role="alert">입력 내용을 임시 저장하지 못했어요. 브라우저 저장소 설정을 확인한 뒤 다시 시도해 주세요.</p>}
      <PrimaryButton onClick={continueToGoal}>다음: 목표 설정</PrimaryButton>
    </main>
  );
}

export function OnboardingGoal() {
  const { demo } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const draftKey = onboardingDraftKey(userKey, demo);
  const [draft, setDraft] = useState(() => readDraft(draftKey));
  const [saveError, setSaveError] = useState(false);
  const progress = Math.min(100, Math.round((draft.goal.current_amount_krw / Math.max(draft.goal.target_amount_krw, 1)) * 100));
  const months = Math.max(1, Math.ceil((new Date(draft.goal.target_date).getTime() - Date.now()) / 2_629_800_000));
  const monthly = Math.max(0, Math.ceil((draft.goal.target_amount_krw - draft.goal.current_amount_krw) / months / 1000) * 1000);
  const updateGoal = (patch: Partial<Profile["goal"]>) => setDraft((current) => ({ ...current, goal: { ...current.goal, ...patch } }));

  function continueToSource() {
    setSaveError(false);
    try {
      writeDraft(draftKey, onboardingStageKey(userKey, demo), draft, "source");
      navigate(withDemo("/onboarding/source", demo));
    } catch {
      setSaveError(true);
    }
  }

  return (
    <main className="onboarding-page goal-page">
      <StepHeader step={3} />
      <div className="onboarding-title">
        <h1><Highlight>저축 목표</Highlight>를<br />설정해요.</h1>
        <p>목표 금액과 날짜를 정하면 매달 필요한 금액을 보여드려요.</p>
      </div>
      <Surface className="goal-form">
        <label>목표 이름<input value={draft.goal.name} onChange={(event) => updateGoal({ name: event.target.value })} /></label>
        <label><span>목표 금액</span><CurrencyInput ariaLabel="목표 금액" value={draft.goal.target_amount_krw} onChange={(value) => updateGoal({ target_amount_krw: value })} /></label>
        <label><span>현재 금액</span><CurrencyInput ariaLabel="현재 금액" value={draft.goal.current_amount_krw} onChange={(value) => updateGoal({ current_amount_krw: value })} /></label>
        <label>목표 날짜<input type="date" value={draft.goal.target_date} onChange={(event) => updateGoal({ target_date: event.target.value })} /></label>
      </Surface>
      <div className="goal-progress-card">
        <span>현재 {progress}%</span>
        <div className="progress-track"><span style={{ width: `${progress}%` }} /></div>
        <div><Wallet size={27} /> 매달 <strong>{formatWon(monthly)}</strong>씩 모으면 돼</div>
      </div>
      {saveError && <p className="form-error" role="alert">목표를 임시 저장하지 못했어요. 브라우저 저장소 설정을 확인한 뒤 다시 시도해 주세요.</p>}
      <PrimaryButton onClick={continueToSource}>다음: 기록 방식</PrimaryButton>
    </main>
  );
}

export function OnboardingSource() {
  const { demo, saveProfile } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const draftKey = onboardingDraftKey(userKey, demo);
  const draft = useMemo(() => readDraft(draftKey), [draftKey]);

  async function finish() {
    setSaving(true);
    setError(null);
    try {
      await saveProfile(draft);
      window.sessionStorage.removeItem(draftKey);
      window.sessionStorage.removeItem(onboardingStageKey(userKey, demo));
      navigate(withDemo("/", demo));
    } catch {
      setError("기준을 저장하지 못했어요. 입력값을 확인해 주세요.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="onboarding-page source-page">
      <StepHeader step={4} />
      <div className="onboarding-title">
        <h1><Highlight>장부 기록</Highlight>을<br />시작해 볼까요?</h1>
        <p>계좌 연결 없이 거래를 직접 기록할 수 있어요.</p>
      </div>
      <div className="source-options">
        <button className="source-option selected" type="button">
          <span className="source-icon"><BookOpenText size={33} /></span>
          <span><strong>직접 입력</strong><em>지금 바로 사용 가능</em><small>지출과 수입을 장부에 기록해요</small></span>
          <CheckCircle size={29} weight="fill" />
        </button>
        <button className="source-option disabled" type="button" disabled>
          <span className="source-icon"><Bank size={34} /></span>
          <span><strong>계좌 연결 <i>준비 중</i></strong><em>읽기 전용으로 가져오기</em><small>결제 차단·이체·자동저축은 하지 않아요</small></span>
        </button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <PrimaryButton disabled={saving} onClick={() => void finish()}>{saving ? "설정 저장 중" : "설정 완료하고 장부 보기"}</PrimaryButton>
    </main>
  );
}
