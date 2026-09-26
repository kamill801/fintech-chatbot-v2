import { useEffect, useMemo, useRef, useState } from "react";
import { CalendarBlank, CheckCircle, Lightbulb, PencilSimple, Target } from "@phosphor-icons/react";
import { AppShell, CategoryIcon, CurrencyInput, InfoCallout, PrimaryButton, Surface, TextButton } from "../components";
import { useAuth } from "../auth-context";
import { useLedger } from "../ledger-context";
import { planDraftKey } from "../local-drafts";
import { Link, useNavigate } from "../router";
import type { PlanDraft, PlanRevisionPreview, SpendingPlanState } from "../types";
import { categoryNames, formatWon, isValidDateKey, withDemo } from "../utils";


function monthDates(): { start: string; end: string } {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const start = new Date(year, month, 1);
  const end = new Date(year, month + 1, 0);
  const local = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  return { start: local(start), end: local(end) };
}

function initialDraft(plan: SpendingPlanState | null, budget: number): PlanDraft {
  if (plan) {
    return {
      period_start: plan.plan.period_start,
      period_end: plan.plan.period_end,
      confirmed_budget_krw: plan.plan.confirmed_budget_krw,
      priorities: plan.plan.priorities,
      planned_expenses: plan.plan.planned_expenses.map((item) => ({
        planned_expense_id: item.planned_expense_id,
        name: item.name,
        amount_krw: item.amount_krw,
        due_date: item.due_date,
        category: item.category,
      })),
    };
  }
  const dates = monthDates();
  return {
    period_start: dates.start,
    period_end: dates.end,
    confirmed_budget_krw: budget,
    priorities: [],
    planned_expenses: [],
  };
}

type ExpenseDraft = PlanDraft["planned_expenses"][number];

interface StoredPlanDraft {
  version: 1;
  step: number;
  editing: boolean;
  baseVersion: number | null;
  draft: PlanDraft;
  priorityText: string;
  expenseDraft: ExpenseDraft;
  reason: string;
}

function emptyExpenseDraft(dueDate: string): ExpenseDraft {
  return { name: "", amount_krw: 0, due_date: dueDate, category: "other" };
}

function readStoredPlanDraft(key: string): StoredPlanDraft | null {
  try {
    const raw = window.sessionStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredPlanDraft;
    if (parsed.version !== 1 || !parsed.draft) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeStoredPlanDraft(key: string, value: StoredPlanDraft) {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // A plan can still be reviewed and saved when browser storage is unavailable.
  }
}

function clearStoredPlanDraft(key: string) {
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Storage failures should not turn a successful plan save into a failed save.
  }
}

function normalizedPlanDraft(draft: PlanDraft): PlanDraft {
  return {
    ...draft,
    priorities: draft.priorities.map((item) => typeof item === "string" ? item.trim() : { ...item, name: item.name.trim() }).filter((item) => typeof item === "string" ? item : item.name),
    planned_expenses: draft.planned_expenses.map((item) => ({ ...item, name: item.name.trim() })),
  };
}

function fingerprintDraft(draft: PlanDraft, editing: boolean, baseVersion: number | null, reason: string): string {
  const normalized = normalizedPlanDraft(draft);
  return JSON.stringify({
    editing,
    baseVersion,
    reason: editing ? reason.trim() : "",
    period_start: normalized.period_start,
    period_end: normalized.period_end,
    confirmed_budget_krw: normalized.confirmed_budget_krw,
    priorities: normalized.priorities.map((item) => typeof item === "string" ? item : { name: item.name, rank: item.rank }),
    planned_expenses: normalized.planned_expenses.map((item) => ({
      planned_expense_id: item.planned_expense_id ?? null,
      name: item.name,
      amount_krw: item.amount_krw,
      due_date: item.due_date,
      category: item.category,
    })),
  });
}

function hasStartedExpenseDraft(expense: ExpenseDraft): boolean {
  return Boolean(expense.name.trim() || expense.amount_krw > 0);
}

function ProgressCards({ state }: { state: SpendingPlanState }) {
  const current = state.progress.segments.find((item) => item.allocation_id === state.progress.current_segment_id);
  return (
    <div className="plan-metrics">
      <Surface><span>계획상 남은 생활비</span><strong className={state.progress.flexible_remaining_krw < 0 ? "expense-text" : ""}>{formatWon(state.progress.flexible_remaining_krw)}</strong><small>예약 {formatWon(state.progress.reserved_remaining_krw)} 별도 반영</small></Surface>
      <Surface><span>실제 사용</span><strong>{formatWon(state.progress.actual_spent_krw)}</strong><small>확정 예산 {formatWon(state.progress.confirmed_budget_krw)}</small></Surface>
      <Surface><span>이번 주</span><strong>{current ? formatWon(current.flexible_remaining_krw) : "기간 밖"}</strong><small>{current ? `${formatWon(current.amount_krw)} 배정` : "계획 기간을 확인하세요"}</small></Surface>
    </div>
  );
}

export function PlanPage() {
  const {
    activatePlan,
    applyPlanRevision,
    checkInPlan,
    matchPlannedExpense,
    plan,
    previewPlan,
    previewPlanRevision,
    profile,
    demo,
    settings,
    summary,
    transactions,
  } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const storageKey = planDraftKey(userKey, demo);
  const storedPlanDraft = readStoredPlanDraft(storageKey);
  const canResumeStoredDraft = storedPlanDraft && (
    (!plan && !storedPlanDraft.editing) ||
    (plan && storedPlanDraft.editing && storedPlanDraft.baseVersion === plan.plan.version)
  );
  const [editing, setEditing] = useState(false);
  const [step, setStep] = useState(() => canResumeStoredDraft ? Math.min(Math.max(storedPlanDraft.step, 1), 2) : 1);
  const [draft, setDraft] = useState<PlanDraft>(() => canResumeStoredDraft ? storedPlanDraft.draft : initialDraft(plan, profile?.discretionary_budget_krw ?? 0));
  const [priorityText, setPriorityText] = useState(() => canResumeStoredDraft ? storedPlanDraft.priorityText : plan?.plan.priorities.map((item) => item.name).join("\n") ?? "");
  const [expenseDraft, setExpenseDraft] = useState<ExpenseDraft>(() => canResumeStoredDraft ? storedPlanDraft.expenseDraft : emptyExpenseDraft(plan?.plan.period_end ?? monthDates().end));
  const [preview, setPreview] = useState<SpendingPlanState | null>(null);
  const [revisionPreview, setRevisionPreview] = useState<PlanRevisionPreview | null>(null);
  const [previewFingerprint, setPreviewFingerprint] = useState<string | null>(null);
  const [reason, setReason] = useState(() => canResumeStoredDraft ? storedPlanDraft.reason : "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const previewRequestId = useRef(0);
  const eligibleTransactions = useMemo(
    () => transactions.filter((item) => item.transaction_type === "expense" && !item.exclude_from_budget),
    [transactions],
  );
  const baseVersion = editing ? plan?.plan.version ?? null : null;
  const currentFingerprint = fingerprintDraft(draft, editing, baseVersion, reason);
  const currentFingerprintRef = useRef(currentFingerprint);
  const hasCurrentPreview = Boolean((preview || revisionPreview) && previewFingerprint === currentFingerprint);
  const pending = settings.roast_enabled
    ? transactions.find((item) => item.status === "awaiting_reason")
    : undefined;
  const briefing = summary?.weekly_briefing;
  const spendingRules = settings.spending_rules ?? [];

  useEffect(() => {
    currentFingerprintRef.current = currentFingerprint;
  }, [currentFingerprint]);

  useEffect(() => {
    if (plan && !editing) return;
    writeStoredPlanDraft(storageKey, {
      version: 1,
      step: Math.min(step, 2),
      editing,
      baseVersion,
      draft,
      priorityText,
      expenseDraft,
      reason,
    });
  }, [baseVersion, draft, editing, expenseDraft, plan, priorityText, reason, step, storageKey]);

  function startEdit() {
    const stored = readStoredPlanDraft(storageKey);
    const resumable = stored?.editing && stored.baseVersion === plan?.plan.version;
    setDraft(resumable ? stored.draft : initialDraft(plan, profile?.discretionary_budget_krw ?? 0));
    setPriorityText(resumable ? stored.priorityText : plan?.plan.priorities.map((item) => item.name).join("\n") ?? "");
    setExpenseDraft(resumable ? stored.expenseDraft : emptyExpenseDraft(plan?.plan.period_end ?? monthDates().end));
    setReason(resumable ? stored.reason : "");
    setEditing(true);
    setStep(resumable ? Math.min(Math.max(stored.step, 1), 2) : 1);
    setPreview(null);
    setRevisionPreview(null);
    setPreviewFingerprint(null);
  }

  function validateStepOne(current: PlanDraft): string | null {
    if (!isValidDateKey(current.period_start) || !isValidDateKey(current.period_end)) return "계획 기간을 확인해 주세요.";
    if (current.period_start > current.period_end) return "종료일은 시작일 이후여야 해요.";
    const start = new Date(`${current.period_start}T00:00:00Z`).getTime();
    const end = new Date(`${current.period_end}T00:00:00Z`).getTime();
    if ((end - start) / 86_400_000 > 366) return "종료일은 시작일로부터 366일 이내로 정해 주세요.";
    if (!Number.isSafeInteger(current.confirmed_budget_krw) || current.confirmed_budget_krw < 1) return "이번 기간에 쓸 생활비 예산을 1원 이상 입력해 주세요.";
    return null;
  }

  function continueFromPeriod() {
    const validation = validateStepOne(draft);
    if (validation) {
      setError(validation);
      return;
    }
    setError(null);
    setStep(2);
  }

  function validateStepTwo(current: PlanDraft, priorities: string[]): string | null {
    if (priorities.length > 3) return "우선순위는 최대 3개까지만 입력할 수 있어요.";
    if (hasStartedExpenseDraft(expenseDraft)) return "작성 중인 예정 지출을 추가하거나 입력을 비워 주세요.";
    for (const expense of current.planned_expenses) {
      if (!expense.name.trim()) return "예정 지출 이름을 확인해 주세요.";
      if (!Number.isSafeInteger(expense.amount_krw) || expense.amount_krw < 1) return `${expense.name || "예정 지출"} 금액을 1원 이상 입력해 주세요.`;
      if (!isValidDateKey(expense.due_date) || expense.due_date < current.period_start || expense.due_date > current.period_end) {
        return `${expense.name || "예정 지출"} 예정일은 계획 기간 안에 있어야 해요.`;
      }
    }
    return null;
  }

  function continueFromPriorities() {
    const periodValidation = validateStepOne(draft);
    if (periodValidation) {
      setError(periodValidation);
      setStep(1);
      return;
    }
    const priorities = priorityText.split("\n").map((item) => item.trim()).filter(Boolean);
    const priorityValidation = validateStepTwo(draft, priorities);
    if (priorityValidation) {
      setError(priorityValidation);
      return;
    }
    const nextDraft = normalizedPlanDraft({ ...draft, priorities });
    const requestFingerprint = fingerprintDraft(nextDraft, editing, baseVersion, reason);
    setDraft(nextDraft);
    setStep(3);
    setSaving(true);
    setError(null);
    setPreview(null);
    setRevisionPreview(null);
    setPreviewFingerprint(null);
    const requestId = previewRequestId.current + 1;
    previewRequestId.current = requestId;
    currentFingerprintRef.current = requestFingerprint;
    const operation = editing ? previewPlanRevision(nextDraft, reason) : previewPlan(nextDraft);
    operation.then((result) => {
      if (previewRequestId.current !== requestId || currentFingerprintRef.current !== requestFingerprint) return;
      if (editing) setRevisionPreview(result as PlanRevisionPreview);
      else setPreview(result as SpendingPlanState);
      setPreviewFingerprint(requestFingerprint);
    }).catch(() => {
      if (previewRequestId.current === requestId) setError("계획 미리보기를 만들지 못했어요. 입력 내용을 유지했으니 다시 검토해 주세요.");
    }).finally(() => {
      if (previewRequestId.current === requestId) setSaving(false);
    });
  }

  function addPlannedExpense() {
    if (!expenseDraft.name.trim() || expenseDraft.amount_krw < 1 || !expenseDraft.due_date) {
      setError("예정 지출의 이름, 금액, 예정일을 확인해 주세요.");
      return;
    }
    if (expenseDraft.due_date < draft.period_start || expenseDraft.due_date > draft.period_end) {
      setError("예정 지출일은 계획 기간 안에 있어야 해요.");
      return;
    }
    setDraft((current) => ({
      ...current,
      planned_expenses: [...current.planned_expenses, { ...expenseDraft, name: expenseDraft.name.trim() }],
    }));
    setExpenseDraft(emptyExpenseDraft(draft.period_end));
    setError(null);
  }

  function updatePlannedExpense(index: number, patch: Partial<PlanDraft["planned_expenses"][number]>) {
    setDraft((current) => ({
      ...current,
      planned_expenses: current.planned_expenses.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item),
    }));
  }

  async function matchExpense(plannedExpenseId: string, transactionId: string) {
    if (!transactionId) return;
    setError(null);
    try {
      await matchPlannedExpense(plannedExpenseId, transactionId);
    } catch {
      setError("실제 지출을 연결하지 못했어요. 기간과 거래 상태를 확인해 주세요.");
    }
  }

  async function recordCheckIn(decision: "maintain" | "adjust") {
    setSaving(true);
    setError(null);
    try {
      await checkInPlan(decision);
      if (decision === "adjust") startEdit();
    } catch {
      setError("체크인을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setSaving(false);
    }
  }

  async function confirm() {
    if (!hasCurrentPreview) {
      setError("현재 입력으로 다시 검토한 뒤 확정해 주세요.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const nextDraft = normalizedPlanDraft(draft);
      if (editing) await applyPlanRevision(nextDraft, reason.trim());
      else await activatePlan(nextDraft);
      setEditing(false);
      setStep(1);
      setPreview(null);
      setRevisionPreview(null);
      setPreviewFingerprint(null);
      clearStoredPlanDraft(storageKey);
    } catch {
      setError("계획을 저장하지 못했어요. 최신 내용을 다시 확인해 주세요.");
    } finally {
      setSaving(false);
    }
  }

  if (plan && !editing) {
    return (
      <AppShell active="/plan">
        <div className="screen plan-screen">
          <header className="plan-header"><div><span>생활비 계획 · v{plan.plan.version}</span><h1>{plan.plan.period_start} ~ {plan.plan.period_end}</h1></div><button type="button" onClick={startEdit}><PencilSimple size={20} /> 계획 수정</button></header>
          <ProgressCards state={plan} />
          <Surface className="plan-coach"><Target size={28} /><div><span>계획 코치</span><h2>{plan.narrative.headline}</h2><p>{plan.narrative.explanation}</p><strong>{plan.narrative.next_action}</strong><small>신뢰도 {plan.narrative.confidence === "high" ? "높음" : plan.narrative.confidence === "medium" ? "보통" : "낮음"} · 숫자는 장부 코드가 계산했어요.</small></div></Surface>
          {pending && <Surface className="pending-card"><div><CategoryIcon category={pending.category} /><strong>{pending.merchant || categoryNames[pending.category]}</strong><b>{formatWon(pending.amount_krw)}</b></div><p>욕쟁이 할머니 모드에서 기다리는 이유 질문이 있어요.</p><button type="button" onClick={() => navigate(withDemo(`/transactions/${pending.transaction_id}/reason`, demo))}>이유 답하기</button></Surface>}
          <Surface className="ai-briefing plan-briefing"><div className="section-heading"><h2>이번 주 AI 브리핑</h2>{briefing && <time>{briefing.period_start} ~ {briefing.period_end}</time>}</div>{briefing ? <><h3>{briefing.headline}</h3><p>{briefing.summary}</p><div className="briefing-metrics"><span><small>이번 주 지출</small><strong>{formatWon(briefing.total_spent_krw)}</strong></span><span><small>가장 큰 분류</small><strong>{briefing.top_category ? categoryNames[briefing.top_category] ?? briefing.top_category : "아직 없음"}</strong></span></div><div className="briefing-action"><Lightbulb size={24} /><span><small>다음 행동</small><strong>{briefing.improvement}</strong></span></div></> : <p className="empty-copy">지출을 기록하면 이번 주 흐름과 개선점을 정리해 드려요.</p>}</Surface>
          <Surface className="personal-rules-card"><div><span>계획 판단에 반영하는 기준</span><h2>내 소비 기준</h2></div>{spendingRules.length ? <ul>{spendingRules.slice(0, 3).map((rule) => <li key={rule}>{rule}</li>)}</ul> : <p>중요하게 생각하는 소비 기준을 추가할 수 있어요.</p>}<Link to={withDemo("/settings", demo)}>{spendingRules.length ? "기준 관리" : "기준 만들기"}</Link></Surface>
          <Surface className="plan-segments"><h2>기간별 생활비</h2>{plan.progress.segments.map((segment) => <div key={segment.allocation_id} className={segment.allocation_id === plan.progress.current_segment_id ? "is-current" : ""}><span><strong>{segment.label}</strong><small>{segment.start_date} ~ {segment.end_date}</small></span><span><b>{formatWon(segment.flexible_remaining_krw)}</b><small>{formatWon(segment.amount_krw)} 중</small></span></div>)}</Surface>
          <Surface className="planned-expenses"><h2>예정 지출</h2>{plan.plan.planned_expenses.map((expense) => <div key={expense.planned_expense_id}><span><strong>{expense.name}</strong><small>{expense.due_date} · {categoryNames[expense.category] ?? expense.category}</small></span><b>{formatWon(expense.amount_krw)}</b>{expense.matched_transaction_id ? <em><CheckCircle size={18} /> 실제 지출 연결됨</em> : <label><span className="sr-only">{expense.name}과 연결할 거래</span><select defaultValue="" onChange={(event) => void matchExpense(expense.planned_expense_id, event.target.value)}><option value="">실제 지출과 연결</option>{eligibleTransactions.map((transaction) => <option key={transaction.transaction_id} value={transaction.transaction_id}>{transaction.merchant ?? categoryNames[transaction.category] ?? "지출"} · {formatWon(transaction.amount_krw)}</option>)}</select></label>}</div>)}{plan.plan.planned_expenses.length === 0 && <p className="empty-copy">예약해 둔 예정 지출이 없어요.</p>}{error && <p className="form-error" role="alert">{error}</p>}</Surface>
          <Surface className="plan-check-in"><CalendarBlank size={25} /><div><h2>이번 주 계획을 유지할까요?</h2><p>유지 기록을 남기거나, 계획 수정으로 이어갈 수 있어요.</p></div><div><button type="button" disabled={saving} onClick={() => void recordCheckIn("maintain")}>이대로 유지</button><button type="button" disabled={saving} onClick={() => void recordCheckIn("adjust")}>조정하기</button></div></Surface>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell active="/plan">
      <div className="screen plan-screen plan-setup">
        <header><span>생활비 계획 {step}/3</span><h1>{editing ? "계획을 조정해 볼게요" : "이번 기간에 쓸 돈을 먼저 정해요"}</h1></header>
        <div className="setup-progress" aria-label={`계획 설정 ${step}단계`}><span style={{ width: `${step * 33.333}%` }} /></div>
        {step === 1 && <Surface className="plan-form"><label>시작일<input type="date" value={draft.period_start} onChange={(event) => setDraft({ ...draft, period_start: event.target.value })} /></label><label>종료일<input type="date" value={draft.period_end} onChange={(event) => setDraft({ ...draft, period_end: event.target.value })} /></label><label>직접 확인한 생활비 예산<CurrencyInput ariaLabel="확정 생활비 예산" minimum={1} value={draft.confirmed_budget_krw} onChange={(confirmed_budget_krw) => setDraft({ ...draft, confirmed_budget_krw })} /></label><InfoCallout>예정 지출을 포함해 이번 기간에 쓸 생활비를 입력해 주세요.</InfoCallout>{error && <p className="form-error" role="alert">{error}</p>}<PrimaryButton onClick={continueFromPeriod} disabled={!draft.period_start || !draft.period_end || draft.confirmed_budget_krw < 1}>다음</PrimaryButton></Surface>}
        {step === 2 && <Surface className="plan-form"><label>우선순위 최대 3개<textarea value={priorityText} onChange={(event) => setPriorityText(event.target.value)} placeholder={"친구와의 약속\n건강"} /></label><h2>예정 지출 예약</h2>{draft.planned_expenses.length > 0 && <div className="planned-expense-editor">{draft.planned_expenses.map((expense, index) => <fieldset key={expense.planned_expense_id ?? `draft-${index}`}><legend>예정 지출 {index + 1}</legend><label>이름<input value={expense.name} onChange={(event) => updatePlannedExpense(index, { name: event.target.value })} /></label><label>금액<CurrencyInput ariaLabel={`예정 지출 ${index + 1} 금액`} value={expense.amount_krw} onChange={(amount_krw) => updatePlannedExpense(index, { amount_krw })} /></label><label>예정일<input type="date" value={expense.due_date} min={draft.period_start} max={draft.period_end} onChange={(event) => updatePlannedExpense(index, { due_date: event.target.value })} /></label><label>분류<select value={expense.category} onChange={(event) => updatePlannedExpense(index, { category: event.target.value })}>{["food", "cafe", "transport", "shopping", "housing", "health", "other"].map((category) => <option key={category} value={category}>{categoryNames[category]}</option>)}</select></label><button type="button" className="remove-planned-expense" onClick={() => setDraft((current) => ({ ...current, planned_expenses: current.planned_expenses.filter((_, itemIndex) => itemIndex !== index) }))}>{expense.name || `예정 지출 ${index + 1}`} 삭제</button></fieldset>)}</div>}<div className="new-planned-expense"><h3>새 예정 지출</h3><label>이름<input value={expenseDraft.name} onChange={(event) => setExpenseDraft({ ...expenseDraft, name: event.target.value })} placeholder="예: 병원비" /></label><label>금액<CurrencyInput ariaLabel="새 예정 지출 금액" value={expenseDraft.amount_krw} onChange={(amount_krw) => setExpenseDraft({ ...expenseDraft, amount_krw })} /></label><label>예정일<input type="date" value={expenseDraft.due_date} min={draft.period_start} max={draft.period_end} onChange={(event) => setExpenseDraft({ ...expenseDraft, due_date: event.target.value })} /></label><label>분류<select value={expenseDraft.category} onChange={(event) => setExpenseDraft({ ...expenseDraft, category: event.target.value })}>{["food", "cafe", "transport", "shopping", "housing", "health", "other"].map((category) => <option key={category} value={category}>{categoryNames[category]}</option>)}</select></label><button type="button" onClick={addPlannedExpense}>예정 지출 추가</button></div>{editing && <label>조정 이유<input value={reason} maxLength={200} onChange={(event) => setReason(event.target.value)} /></label>}{error && <p className="form-error" role="alert">{error}</p>}<div className="form-actions"><TextButton onClick={() => setStep(1)}>이전</TextButton><PrimaryButton onClick={continueFromPriorities}>검토하기</PrimaryButton></div></Surface>}
        {step === 3 && <Surface className="plan-review"><h2>{editing ? "변경 전후를 확인하세요" : "이 계획으로 시작할까요?"}</h2>{saving && <p>계획을 계산하는 중이에요.</p>}{hasCurrentPreview && preview && <ProgressCards state={preview} />}{hasCurrentPreview && revisionPreview && <div className="revision-compare"><span><small>변경 전 남은 생활비</small><strong>{formatWon(revisionPreview.before_progress.flexible_remaining_krw)}</strong></span><span><small>변경 후 남은 생활비</small><strong>{formatWon(revisionPreview.after_progress.flexible_remaining_krw)}</strong></span><p>예산 변화 {formatWon(revisionPreview.budget_change_krw)}</p></div>}{hasCurrentPreview && (preview?.narrative ?? revisionPreview?.narrative) && <div className="plan-review-narrative"><span>계획 코치 미리보기</span><h3>{(preview?.narrative ?? revisionPreview?.narrative)?.headline}</h3><p>{(preview?.narrative ?? revisionPreview?.narrative)?.explanation}</p><strong>{(preview?.narrative ?? revisionPreview?.narrative)?.next_action}</strong></div>}<ul><li>기간: {draft.period_start} ~ {draft.period_end}</li><li>확정 생활비: {formatWon(draft.confirmed_budget_krw)}</li><li>우선순위: {draft.priorities.map((item) => typeof item === "string" ? item : item.name).join(", ") || "없음"}</li><li>예정 지출: {formatWon(draft.planned_expenses.reduce((sum, item) => sum + item.amount_krw, 0))}</li></ul>{error && <p className="form-error" role="alert">{error}</p>}<PrimaryButton disabled={saving || !hasCurrentPreview} onClick={() => void confirm()}>{editing ? "변경 내용 적용" : "확인하고 계획 시작"}</PrimaryButton><TextButton onClick={() => setStep(2)}>다시 수정</TextButton></Surface>}
      </div>
    </AppShell>
  );
}
