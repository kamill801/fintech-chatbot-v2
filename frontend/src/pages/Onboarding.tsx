import { useMemo, useState } from "react";
import {
  ArrowLeft,
  Bank,
  BookOpenText,
  CheckCircle,
  LockKey,
  PencilSimple,
  ShieldCheck,
  Wallet,
} from "@phosphor-icons/react";
import { BookkeeperMark, CurrencyInput, Highlight, PrimaryButton, Surface } from "../components";
import { demoProfile } from "../demo";
import { useAuth } from "../auth-context";
import { useLedger } from "../ledger-context";
import { onboardingDraftKey } from "../local-drafts";
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

function writeDraft(key: string, profile: Profile) {
  window.sessionStorage.setItem(key, JSON.stringify(profile));
}

function StepHeader({ step }: { step: number }) {
  const navigate = useNavigate();
  return (
    <div className="step-header">
      {step > 1 ? (
        <button className="icon-button" aria-label="이전 단계" onClick={() => navigate(-1)}><ArrowLeft size={28} /></button>
      ) : <span />}
      <span><strong>{step}</strong> / 4</span>
      <span />
    </div>
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
  const navigate = useNavigate();
  return (
    <main className="onboarding-page trust-page">
      <StepHeader step={1} />
      <div className="onboarding-copy">
        <h1>내 돈을<br />맡기는 게 아니라,<br /><Highlight>장부</Highlight>를 맡기는 거야.</h1>
        <BookkeeperMark />
      </div>
      <Surface className="trust-list">
        <div><PencilSimple size={27} /><span>내가 직접 입력한 지출만 기록해</span></div>
        <div><ShieldCheck size={27} /><span>판단할 때 필요한 정보만 AI가 봐</span></div>
        <div><ArrowLeft className="undo-icon" size={27} /><span>언제든 수정하고 지울 수 있어</span></div>
      </Surface>
      <div className="privacy-strip"><LockKey size={25} /> 계좌 연결 없이 시작할 수 있어요</div>
      <PrimaryButton onClick={() => navigate(withDemo("/onboarding/baseline", demo))}>수기로 시작하기</PrimaryButton>
      <details className="disclosure">
        <summary>데이터 처리 방식 보기</summary>
        <p>상점명과 메모는 장부에 보관되고, 판단에는 금액·분류·예산 신호와 직접 답한 이유만 최소한으로 사용합니다.</p>
      </details>
    </main>
  );
}

export function OnboardingBaseline() {
  const { demo } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const draftKey = onboardingDraftKey(userKey, demo);
  const [draft, setDraft] = useState(() => readDraft(draftKey));
  const update = (key: keyof Profile, value: number) => setDraft((current) => ({ ...current, [key]: value }));
  const freeMoney = Math.max(0, draft.monthly_income_krw - draft.fixed_expenses_krw - draft.monthly_debt_payment_krw - draft.discretionary_budget_krw);

  return (
    <main className="onboarding-page baseline-page">
      <StepHeader step={2} />
      <div className="onboarding-title with-mark">
        <div>
          <h1>내 소비를 볼<br /><Highlight>기준</Highlight>부터 맞춰요.</h1>
          <p>수입과 고정비를 함께 봐야 같은 지출도 내 상황에 맞게 판단할 수 있어요.</p>
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
      <PrimaryButton onClick={() => { writeDraft(draftKey, draft); navigate(withDemo("/onboarding/goal", demo)); }}>기준 저장하기</PrimaryButton>
    </main>
  );
}

export function OnboardingGoal() {
  const { demo } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const draftKey = onboardingDraftKey(userKey, demo);
  const [draft, setDraft] = useState(() => readDraft(draftKey));
  const progress = Math.min(100, Math.round((draft.goal.current_amount_krw / Math.max(draft.goal.target_amount_krw, 1)) * 100));
  const months = Math.max(1, Math.ceil((new Date(draft.goal.target_date).getTime() - Date.now()) / 2_629_800_000));
  const monthly = Math.max(0, Math.ceil((draft.goal.target_amount_krw - draft.goal.current_amount_krw) / months / 1000) * 1000);
  const updateGoal = (patch: Partial<Profile["goal"]>) => setDraft((current) => ({ ...current, goal: { ...current.goal, ...patch } }));

  return (
    <main className="onboarding-page goal-page">
      <StepHeader step={3} />
      <div className="onboarding-title">
        <h1><Highlight>딱 하나,</Highlight><br />어디까지 모을까?</h1>
        <p>지금 가장 중요한 목표만 잡자.</p>
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
      <PrimaryButton onClick={() => { writeDraft(draftKey, draft); navigate(withDemo("/onboarding/source", demo)); }}>목표 시작하기</PrimaryButton>
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
        <h1>일단 <Highlight>손으로,</Highlight><br />나중엔 연결로.</h1>
        <p>오늘부터 쓰는 게 먼저야.</p>
      </div>
      <div className="source-options">
        <button className="source-option selected" type="button">
          <span className="source-icon"><BookOpenText size={33} /></span>
          <span><strong>수기 입력</strong><em>지금 바로 사용 가능</em><small>직접 기록하고 바로 판단받기</small></span>
          <CheckCircle size={29} weight="fill" />
        </button>
        <button className="source-option disabled" type="button" disabled>
          <span className="source-icon"><Bank size={34} /></span>
          <span><strong>계좌 연결 <i>준비 중</i></strong><em>읽기 전용으로 가져오기</em><small>결제 차단·이체·자동저축은 하지 않아요</small></span>
        </button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <PrimaryButton disabled={saving} onClick={() => void finish()}>{saving ? "기준 저장 중" : "수기 입력으로 시작"}</PrimaryButton>
    </main>
  );
}
