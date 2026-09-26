import { useState } from "react";
import { CurrencyInput, PrimaryButton, Surface } from "../components";
import { useLedger } from "../ledger-context";
import { Link, useNavigate } from "../router";
import type { Profile } from "../types";
import { formatWon, isValidDateKey, withDemo } from "../utils";

const moneyFields: Array<{ key: keyof Pick<Profile, "liquid_assets_krw" | "monthly_income_krw" | "fixed_expenses_krw" | "monthly_debt_payment_krw" | "discretionary_budget_krw">; label: string }> = [
  { key: "liquid_assets_krw", label: "보유 현금·예금" },
  { key: "monthly_income_krw", label: "월 수입" },
  { key: "fixed_expenses_krw", label: "고정지출" },
  { key: "monthly_debt_payment_krw", label: "빚 상환" },
  { key: "discretionary_budget_krw", label: "생활비 예산" },
];

export function ProfileSettingsPage({ section }: { section: "budget" | "goal" }) {
  const { demo, profile, saveProfile } = useLedger();
  const navigate = useNavigate();
  const [draft, setDraft] = useState<Profile | null>(() => profile ? structuredClone(profile) : null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!profile || !draft) return <main className="standalone-screen profile-edit-screen"><p>예산 설정을 먼저 완료해 주세요.</p><Link to={withDemo("/settings", demo)}>설정으로 돌아가기</Link></main>;

  const remaining = draft.monthly_income_krw - draft.fixed_expenses_krw - draft.monthly_debt_payment_krw - draft.discretionary_budget_krw;
  const updateGoal = (patch: Partial<Profile["goal"]>) => setDraft((current) => current ? { ...current, goal: { ...current.goal, ...patch } } : current);

  async function save() {
    setError(null);
    if (!draft) return;
    if (moneyFields.some(({ key }) => !Number.isSafeInteger(draft[key]) || draft[key] < 0) || draft.discretionary_budget_krw < 1) {
      setError("금액은 0원 이상의 정수로 입력하고 생활비 예산은 1원 이상으로 설정해 주세요.");
      return;
    }
    if (!draft.goal.name.trim() || !Number.isSafeInteger(draft.goal.target_amount_krw) || draft.goal.target_amount_krw < 1 || !Number.isSafeInteger(draft.goal.current_amount_krw) || draft.goal.current_amount_krw < 0 || !isValidDateKey(draft.goal.target_date)) {
      setError("목표 이름, 금액, 날짜를 확인해 주세요.");
      return;
    }
    setSaving(true);
    try {
      await saveProfile({ ...draft, goal: { ...draft.goal, name: draft.goal.name.trim() } });
      navigate(withDemo("/settings", demo));
    } catch {
      setError("변경 내용을 저장하지 못했어요. 입력값을 확인하고 다시 시도해 주세요.");
    } finally {
      setSaving(false);
    }
  }

  return <main className="standalone-screen profile-edit-screen">
    <header className="profile-edit-header"><Link to={withDemo("/settings", demo)}>취소</Link><h1>{section === "budget" ? "예산 수정" : "목표 수정"}</h1></header>
    {section === "budget" ? <>
      <p>현재 저장된 금액을 수정해 주세요. 보유 현금·예금은 매달 쓰는 돈과 구분해요.</p>
      <Surface className="profile-edit-form">
        {moneyFields.map(({ key, label }) => <label key={key}><span>{label}</span><CurrencyInput ariaLabel={label} value={draft[key]} onChange={(value) => setDraft((current) => current ? { ...current, [key]: value } : current)} /></label>)}
      </Surface>
      <p className="profile-edit-balance">입력한 금액 기준 월 잔여 예상: <strong>{remaining >= 0 ? formatWon(remaining) : `${formatWon(Math.abs(remaining))} 부족`}</strong></p>
      <p>생활비 예산은 고정지출과 빚 상환을 제외하고 입력해 주세요.</p>
    </> : <>
      <p>목표까지의 금액과 날짜를 확인해 주세요.</p>
      <Surface className="profile-edit-form">
        <label><span>목표 이름</span><input value={draft.goal.name} onChange={(event) => updateGoal({ name: event.target.value })} maxLength={80} /></label>
        <label><span>목표 금액</span><CurrencyInput ariaLabel="목표 금액" value={draft.goal.target_amount_krw} onChange={(value) => updateGoal({ target_amount_krw: value })} /></label>
        <label><span>현재 금액</span><CurrencyInput ariaLabel="현재 금액" value={draft.goal.current_amount_krw} onChange={(value) => updateGoal({ current_amount_krw: value })} /></label>
        <label><span>목표 날짜</span><input type="date" value={draft.goal.target_date} onChange={(event) => updateGoal({ target_date: event.target.value })} /></label>
      </Surface>
    </>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <PrimaryButton disabled={saving} onClick={() => void save()}>{saving ? "저장 중" : "변경사항 저장"}</PrimaryButton>
  </main>;
}
