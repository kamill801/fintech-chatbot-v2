import { type FormEvent, useEffect, useRef, useState } from "react";
import {
  CalendarBlank,
  CaretRight,
  MapPin,
  NotePencil,
  Wallet,
} from "@phosphor-icons/react";
import {
  AppShell,
  CategoryIcon,
  CurrencyInput,
  Highlight,
  ModePill,
  PageHeader,
  PrimaryButton,
  ProfileButton,
  Surface,
  TransactionRow,
} from "../components";
import { useAuth } from "../auth-context";
import { ApiError } from "../api";
import { useLedger } from "../ledger-context";
import { manualDraftKey } from "../local-drafts";
import { Link, useNavigate, useParams } from "../router";
import type { Transaction, TransactionDraft, TransactionType } from "../types";
import { categoryNames, createClientId, formatCompactWon, formatDate, formatTodayLabel, formatWon, isValidDateKey, transactionDateKey, withDemo } from "../utils";

const expenseCategories = ["cafe", "food", "transport", "shopping", "housing", "health", "other"];
const incomeCategories = ["salary", "other"];

interface StoredManualDraft {
  version?: 1;
  draft: TransactionDraft;
  operationId: string;
  date?: string;
  pendingRequest?: TransactionDraft;
  completed?: boolean;
}

function monthlyRemaining(total: number, budget?: number): number {
  return (budget ?? 0) - total;
}

export function HomePage() {
  const { demo, plan, profile, refresh, settings, summary, syncWarning, transactions } = useLedger();
  const navigate = useNavigate();
  const pending = settings.roast_enabled
    ? transactions.find((item) => item.status === "awaiting_reason")
    : undefined;
  const total = summary?.budget_spent_krw ?? summary?.total_spent_krw ?? 0;
  const budget = summary?.discretionary_budget_krw ?? profile?.discretionary_budget_krw ?? 0;
  const usage = budget ? Math.min(1, total / budget) : 0;
  const remaining = monthlyRemaining(total, budget);
  const goal = summary?.goal ?? profile?.goal;
  const goalProgress = goal ? Math.min(100, Math.round((goal.current_amount_krw / Math.max(goal.target_amount_krw, 1)) * 100)) : 0;
  const currentSegment = plan?.progress.segments.find((item) => item.allocation_id === plan.progress.current_segment_id);

  return (
    <AppShell active="/" showAdd>
      <div className="screen home-screen">
        <header className="home-header">
          <div><h1>장부 AI</h1><time>{demo ? "8월 3일 월요일" : formatTodayLabel()}</time></div>
          <ProfileButton demo={demo} />
        </header>
        {settings.roast_enabled && <Link className="home-mode-link" to={withDemo("/settings", demo)}><ModePill enabled /></Link>}
        {syncWarning && <p className="ledger-sync-warning" role="status">{syncWarning} <button type="button" onClick={() => void refresh()}>다시 불러오기</button></p>}
        {plan ? <section className="home-hero plan-home-hero reveal-1">
          <h2>계획상 남은 생활비</h2>
          <p>{plan.plan.period_start} ~ {plan.plan.period_end}</p>
          <strong className={`hero-amount ${plan.progress.flexible_remaining_krw < 0 ? "expense-text" : ""}`}>{plan.progress.flexible_remaining_krw < 0 ? `${formatWon(Math.abs(plan.progress.flexible_remaining_krw))} 부족` : formatWon(plan.progress.flexible_remaining_krw)}</strong>
          <span>{plan.progress.latest_input_at ? `${formatDate(plan.progress.latest_input_at)}까지 직접 입력된 거래 기준` : "아직 입력된 지출이 없는 계획 기준"}</span>
          <div className="home-week-plan"><span>이번 주 배정 <b>{currentSegment ? formatWon(currentSegment.amount_krw) : "기간 밖"}</b></span><span>이번 주 남음 <b>{currentSegment ? formatWon(currentSegment.flexible_remaining_krw) : "-"}</b></span></div>
          <Link className="home-plan-action" to={withDemo("/plan", demo)}>생활비 계획 확인 <CaretRight size={18} /></Link>
        </section> : <section className="home-hero plan-empty-hero reveal-1">
          <h2>이번 달 지출</h2>
          <strong className="hero-amount">{formatWon(total)}</strong>
          <p>{budget > 0 ? `설정한 생활비 ${formatWon(budget)} 중 ${Math.round(usage * 100)}% 사용` : "기록한 내역 기준"}</p>
          <Link className="home-plan-action" to={withDemo("/plan", demo)}>생활비 계획 만들기 <CaretRight size={18} /></Link>
          {budget > 0 && <small>{remaining < 0 ? `생활비 ${formatWon(Math.abs(remaining))} 부족` : `생활비 ${formatWon(remaining)} 남음`}</small>}
        </section>}

        <section className="recent-section">
          <div className="section-heading"><h2>최근 내역</h2><Link to={withDemo("/ledger", demo)}>전체 보기 <CaretRight size={16} /></Link></div>
          <div className="flat-list">
            {transactions.slice(0, 3).map((transaction) => (
              <TransactionRow key={transaction.transaction_id} transaction={transaction} onClick={() => navigate(withDemo(`/transactions/${transaction.transaction_id}`, demo))} />
            ))}
            {transactions.length === 0 && <div className="home-empty-transactions"><p className="empty-copy">아직 기록이 없어요.</p><Link to={withDemo("/add", demo)}>첫 지출 기록하기</Link></div>}
          </div>
        </section>
        {goal && <Surface className="goal-strip reveal-2"><Wallet size={29} /><strong>{goal.name} {formatCompactWon(goal.target_amount_krw)}</strong><div><span>{goalProgress}% 달성</span><div className="mini-progress"><span style={{ width: `${goalProgress}%` }} /></div></div></Surface>}
        {pending && <section className="agent-brief reveal-3"><div><strong>답변을 기다리는 지출이 있어요</strong><p>{pending.merchant || categoryNames[pending.category]} · {formatWon(pending.amount_krw)}</p><button onClick={() => navigate(withDemo(`/transactions/${pending.transaction_id}/reason`, demo))}>이유 답하기</button></div><CaretRight size={24} /></section>}
      </div>
    </AppShell>
  );
}

function todayForInput(): string {
  return transactionDateKey(new Date());
}

function requestedDateForInput(): string | null {
  const requested = new URLSearchParams(window.location.search).get("date");
  return requested && isValidDateKey(requested) ? requested : null;
}

function initialDateForInput(): string {
  return requestedDateForInput() ?? todayForInput();
}

function blankManualDraft(demo: boolean): TransactionDraft {
  return demo
    ? { amount_krw: 12_000, category: "cafe", merchant: "카페 온도", transaction_type: "expense", account_id: "bank" }
    : { amount_krw: 0, category: "other", merchant: "", transaction_type: "expense" };
}

function readManualDraft(key: string, demo: boolean): StoredManualDraft {
  try {
    const saved = window.localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved) as Partial<StoredManualDraft> & TransactionDraft;
      if ("draft" in parsed && parsed.draft && parsed.operationId) {
        if (parsed.completed) return { version: 1, draft: blankManualDraft(demo), operationId: createClientId(), date: initialDateForInput() };
        return { version: 1, draft: parsed.draft, operationId: parsed.operationId, date: parsed.date, pendingRequest: parsed.pendingRequest };
      }
      return { version: 1, draft: parsed as TransactionDraft, operationId: createClientId() };
    }
  } catch {
    // Start from a safe blank draft if local storage is unavailable.
  }
  return { version: 1, draft: blankManualDraft(demo), operationId: createClientId() };
}

export function ManualTransactionPage() {
  const { createTransaction, demo, settings, transactions } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const draftKey = manualDraftKey(userKey, demo);
  const [storedDraft, setStoredDraft] = useState<StoredManualDraft>(() => {
    const saved = readManualDraft(draftKey, demo);
    return requestedDateForInput() && !saved.pendingRequest ? { ...saved, date: requestedDateForInput()! } : saved;
  });
  const { draft, operationId } = storedDraft;
  const date = storedDraft.date ?? initialDateForInput();
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  const completed = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);
  const transactionType = draft.transaction_type ?? "expense";
  const configuredAccounts = settings.accounts ?? [{ account_id: "cash", name: "현금", account_type: "cash" as const, opening_balance_krw: 0, archived: false }];
  const activeAccounts = configuredAccounts.filter((account) => !account.archived);
  const accountId = draft.account_id ?? activeAccounts[0]?.account_id ?? "cash";
  const categories = transactionType === "income" ? incomeCategories : transactionType === "transfer" ? ["transfer"] : expenseCategories;
  const recentSuggestions = (transactions ?? [])
    .filter((item) => item.transaction_type === transactionType)
    .filter((item, index, items) => items.findIndex((candidate) => `${candidate.category}:${candidate.merchant ?? ""}:${candidate.account_id}` === `${item.category}:${item.merchant ?? ""}:${item.account_id}`) === index)
    .slice(0, 3);
  const awaitingReason = (transactions ?? []).find((item) => item.status === "awaiting_reason");

  useEffect(() => {
    if (completed.current) return;
    try {
      window.localStorage.setItem(draftKey, JSON.stringify(storedDraft));
    } catch {
      setStorageWarning("입력 내용을 이 기기에 임시 보관하지 못했어요. 화면을 닫기 전에 기록해 주세요.");
    }
  }, [draftKey, storedDraft]);

  function updateDraft(patch: Partial<TransactionDraft>) {
    setStoredDraft((current) => current.pendingRequest ? current : { ...current, draft: { ...current.draft, ...patch } });
  }

  function selectTransactionType(nextType: TransactionType) {
    updateDraft({
      transaction_type: nextType,
      category: nextType === "income" ? "salary" : nextType === "transfer" ? "transfer" : "other",
      destination_account_id: nextType === "transfer" ? activeAccounts.find((account) => account.account_id !== accountId)?.account_id ?? null : null,
      exclude_from_budget: false,
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current) return;
    if (!Number.isSafeInteger(draft.amount_krw) || draft.amount_krw < 1) {
      setError("금액을 입력해 주세요.");
      return;
    }
    if (!isValidDateKey(date)) {
      setError("유효한 날짜를 선택해 주세요.");
      return;
    }
    if (!activeAccounts.some((account) => account.account_id === accountId)) {
      setError("사용할 수 있는 계좌를 선택해 주세요.");
      return;
    }
    if (transactionType === "transfer" && (!draft.destination_account_id || draft.destination_account_id === accountId)) {
      setError("보낼 계좌와 받을 계좌를 다르게 선택해 주세요.");
      return;
    }
    inFlight.current = true;
    setSaving(true);
    setError(null);
    const request = storedDraft.pendingRequest ?? {
      ...draft,
      transaction_type: transactionType,
      account_id: accountId,
      occurred_at: new Date(`${date}T12:00:00+09:00`).toISOString(),
    };
    setStoredDraft((current) => ({ ...current, date, pendingRequest: request }));
    try {
      const result = await createTransaction(request, operationId);
      completed.current = true;
      try { window.localStorage.setItem(draftKey, JSON.stringify({ ...storedDraft, date, pendingRequest: request, completed: true })); } catch { /* Storage is optional. */ }
      try { window.localStorage.removeItem(draftKey); } catch { /* The completed marker prevents replay when it was saved. */ }
      if (result.pending_question) {
        navigate(withDemo(`/transactions/${result.transaction.transaction_id}/reason`, demo));
      } else {
        const recordedDate = transactionDateKey(result.transaction.occurred_at);
        navigate(withDemo(`/ledger?date=${recordedDate}&view=calendar&saved=${encodeURIComponent(result.transaction.transaction_id)}`, demo));
      }
    } catch (nextError) {
      if (nextError instanceof ApiError && nextError.code === "pending_reason_required") {
        setError("먼저 이전 지출의 이유를 답해 주세요.");
        setStoredDraft((current) => ({ ...current, pendingRequest: undefined }));
      } else if (nextError instanceof ApiError && nextError.code === "profile_required") {
        setError("예산과 목표를 먼저 설정해 주세요. 입력한 내용은 유지했어요.");
        setStoredDraft((current) => ({ ...current, pendingRequest: undefined }));
      } else if (nextError instanceof ApiError && nextError.code === "invalid_account") {
        setError("선택한 계좌를 사용할 수 없어요. 설정에서 계좌를 확인해 주세요.");
        setStoredDraft((current) => ({ ...current, pendingRequest: undefined }));
      } else if (nextError instanceof ApiError && nextError.status === 401) {
        setError("로그인 상태를 확인해 주세요. 입력한 내용은 유지했어요.");
        setStoredDraft((current) => ({ ...current, pendingRequest: undefined }));
      } else if (nextError instanceof ApiError && nextError.status === 400) {
        setError("입력한 금액과 날짜, 계좌를 다시 확인해 주세요.");
        setStoredDraft((current) => ({ ...current, pendingRequest: undefined }));
      } else if (nextError instanceof ApiError && nextError.status === 429) {
        setError("지금은 요청 한도 때문에 기록할 수 없어요. 잠시 후 다시 시도해 주세요.");
        setStoredDraft((current) => ({ ...current, pendingRequest: undefined }));
      } else {
        setError("저장 여부를 확인하지 못했어요. 같은 요청으로 다시 확인해 주세요. 입력은 잠시 잠가 두었어요.");
      }
    } finally {
      inFlight.current = false;
      setSaving(false);
    }
  }

  return (
    <main className="standalone-screen composer-screen">
      <PageHeader title="거래 기록" />
      <form onSubmit={submit} noValidate>
        <fieldset disabled={Boolean(storedDraft.pendingRequest) || saving} className="composer-editable">
        <section className="amount-entry">
          <h1>{transactionType === "expense" ? "지출 금액" : transactionType === "income" ? "수입 금액" : "이체 금액"}</h1>
          <CurrencyInput className="composer-money-input" ariaLabel="금액" value={draft.amount_krw} onChange={(amount_krw) => updateDraft({ amount_krw })} />
        </section>
        <div className="segmented-control transaction-type-control" role="group" aria-label="거래 유형">
          {(["expense", "income", "transfer"] as const).map((type) => (
            <button type="button" key={type} className={transactionType === type ? "selected" : ""} aria-pressed={transactionType === type} onClick={() => selectTransactionType(type)}>
              {{ expense: "지출", income: "수입", transfer: "이체" }[type]}
            </button>
          ))}
        </div>
        {recentSuggestions.length > 0 && <section className="quick-entry"><span>최근 거래 빠른 입력</span><div>{recentSuggestions.map((item) => <button type="button" key={item.transaction_id} onClick={() => updateDraft({ amount_krw: item.amount_krw, category: item.category, merchant: item.merchant ?? "", description: item.description ?? "", account_id: item.account_id })}><strong>{item.merchant || categoryNames[item.category]}</strong><small>{formatWon(item.amount_krw)}</small></button>)}</div></section>}
        <Surface className="composer-fields">
          <label className="field-row">
            <span className="warm-icon"><CategoryIcon category={draft.category} /></span><strong>분류</strong>
            <select value={draft.category} onChange={(event) => updateDraft({ category: event.target.value })}>
              {categories.map((category) => <option key={category} value={category}>{categoryNames[category]}</option>)}
            </select><CaretRight size={19} />
          </label>
          <label className="field-row">
            <span className="warm-icon"><MapPin size={23} /></span><strong>{transactionType === "expense" ? "사용처" : transactionType === "income" ? "입금처" : "이체 메모"}</strong>
            <input value={draft.merchant ?? ""} placeholder="선택 입력" onChange={(event) => updateDraft({ merchant: event.target.value })} />
          </label>
          <label className="field-row">
            <span className="warm-icon"><Wallet size={23} /></span><strong>{transactionType === "transfer" ? "보낼 계좌" : "계좌"}</strong>
            <select value={accountId} onChange={(event) => updateDraft({ account_id: event.target.value })}>{activeAccounts.map((account) => <option key={account.account_id} value={account.account_id}>{account.name}</option>)}</select><CaretRight size={19} />
          </label>
          {transactionType === "transfer" && <label className="field-row"><span className="warm-icon"><Wallet size={23} /></span><strong>받을 계좌</strong><select value={draft.destination_account_id ?? ""} onChange={(event) => updateDraft({ destination_account_id: event.target.value || null })}><option value="">계좌 선택</option>{activeAccounts.filter((account) => account.account_id !== accountId).map((account) => <option key={account.account_id} value={account.account_id}>{account.name}</option>)}</select><CaretRight size={19} /></label>}
          <label className="field-row date-field-row">
            <span className="warm-icon"><CalendarBlank size={23} /></span><strong>날짜</strong>
            <input type="date" value={date} onChange={(event) => setStoredDraft((current) => ({ ...current, date: event.target.value }))} />
          </label>
          <label className="field-row">
            <span className="warm-icon"><NotePencil size={23} /></span><strong>메모</strong>
            <input value={draft.description ?? ""} placeholder="선택 입력" onChange={(event) => updateDraft({ description: event.target.value })} />
          </label>
        </Surface>
        {transactionType === "expense" && <label className="budget-exclusion"><input type="checkbox" checked={draft.exclude_from_budget ?? false} onChange={(event) => updateDraft({ exclude_from_budget: event.target.checked })} /><span><strong>이번 달 예산에서 제외</strong><small>환급·대납처럼 실제 생활비가 아닌 지출에 사용해요.</small></span></label>}
        </fieldset>
        {transactionType === "expense" && settings.roast_enabled && <p className="composer-helper">저장 후 지출 이유를 한 번 물어요.</p>}
        {storageWarning && <p className="form-error" role="status">{storageWarning}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
        {error && awaitingReason && <Link className="composer-check-ledger" to={withDemo(`/transactions/${awaitingReason.transaction_id}/reason`, demo)}>이전 지출의 이유 답하기</Link>}
        {storedDraft.pendingRequest && error && <Link className="composer-check-ledger" to={withDemo(`/ledger?date=${date}&view=calendar`, demo)}>캘린더에서 확인하기</Link>}
        <PrimaryButton disabled={saving}>{saving ? "저장 중…" : storedDraft.pendingRequest ? "같은 요청으로 확인하기" : transactionType === "expense" && settings.roast_enabled ? "저장하고 이유 답하기" : `${{ expense: "지출", income: "수입", transfer: "이체" }[transactionType]} 저장하기`}</PrimaryButton>
      </form>
    </main>
  );
}

export function ReasonPage() {
  const { transactionId = "" } = useParams();
  const { answerReason, demo, getTransaction, profile, summary, transactions } = useLedger();
  const navigate = useNavigate();
  const [transaction, setTransaction] = useState<Transaction | null>(transactions.find((item) => item.transaction_id === transactionId) ?? null);
  const [reason, setReason] = useState(demo ? "친구와 오랜만에 만나서 이야기할 곳이 필요했어." : "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!transaction) void getTransaction(transactionId).then((detail) => setTransaction(detail.transaction)).catch(() => setError("거래를 불러오지 못했어요."));
  }, [getTransaction, transaction, transactionId]);

  async function submit() {
    if (!reason.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await answerReason(transactionId, reason.trim());
      navigate(withDemo(`/judgments/${transactionId}`, demo));
    } catch {
      setError("이유를 보내지 못했어요. 내용은 그대로 남아 있어요.");
    } finally {
      setSaving(false);
    }
  }

  if (!transaction) return <div className="loading-screen">거래를 불러오는 중</div>;
  const budget = summary?.discretionary_budget_krw ?? profile?.discretionary_budget_krw ?? 0;
  const budgetUsage = budget > 0 ? Math.round(((summary?.budget_spent_krw ?? summary?.total_spent_krw ?? 0) / budget) * 100) : 0;
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const sameCategoryCount = Math.max(1, transactions.filter((item) => item.category === transaction.category && (demo || new Date(item.occurred_at).getTime() >= weekAgo)).length);
  return (
    <main className="standalone-screen reason-screen">
      <PageHeader title="할머니에게 이유 답하기" close />
      <Surface className="reason-transaction">
        <CategoryIcon category={transaction.category} />
        <span><small>{categoryNames[transaction.category]}</small><strong>{transaction.merchant || "지출"}</strong></span>
        <time>{formatDate(transaction.occurred_at)}</time>
        <b>{formatWon(transaction.amount_krw)}</b>
      </Surface>
      <section className="reason-hero">
        <div><h1>이 지출이<br />꼭 필요했던<br /><Highlight>이유</Highlight>가 뭐야?</h1></div>
      </section>
      <div className="reason-signals"><span><i /> 생활비 예산 {budgetUsage}% 사용</span><span><CalendarBlank size={19} /> 이번 주 같은 분류 {sameCategoryCount}번째</span></div>
      <label className="reason-box">
        <span className="sr-only">지출 이유</span>
        <textarea maxLength={120} value={reason} onChange={(event) => setReason(event.target.value)} />
        <small>{reason.length} / 120</small>
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <PrimaryButton disabled={saving || !reason.trim()} onClick={() => void submit()}>{saving ? "판단하는 중" : "이유 보내기"}</PrimaryButton>
      <button className="skip-reason" onClick={() => navigate(withDemo(`/ledger?date=${transactionDateKey(transaction.occurred_at)}&view=calendar&saved=${encodeURIComponent(transaction.transaction_id)}`, demo))}>나중에 답하기 · 장부로</button>
    </main>
  );
}
