import { type FormEvent, useEffect, useState } from "react";
import {
  CalendarBlank,
  CaretRight,
  MapPin,
  NotePencil,
  Wallet,
} from "@phosphor-icons/react";
import {
  AppShell,
  BookkeeperMark,
  CategoryIcon,
  CurrencyInput,
  Highlight,
  InfoCallout,
  ModePill,
  PageHeader,
  PrimaryButton,
  Surface,
  TransactionRow,
} from "../components";
import { useAuth } from "../auth-context";
import { useLedger } from "../ledger-context";
import { manualDraftKey } from "../local-drafts";
import { Link, useNavigate, useParams } from "../router";
import type { Transaction, TransactionDraft } from "../types";
import { categoryNames, formatCompactWon, formatDate, formatTodayLabel, formatWon, withDemo } from "../utils";

const categories = ["cafe", "food", "transport", "shopping", "housing", "health", "other"];

interface StoredManualDraft {
  draft: TransactionDraft;
  operationId: string;
}

function monthlyRemaining(total: number, budget?: number): number {
  return Math.max(0, (budget ?? 0) - total);
}

export function HomePage() {
  const { demo, profile, settings, summary, transactions } = useLedger();
  const navigate = useNavigate();
  const pending = transactions.find((item) => item.status === "awaiting_reason") ?? (demo ? transactions[0] : undefined);
  const total = summary?.total_spent_krw ?? 0;
  const budget = summary?.discretionary_budget_krw ?? profile?.discretionary_budget_krw ?? 0;
  const usage = demo ? 0.48 : budget ? Math.min(1, total / budget) : 0;
  const remaining = demo ? 623_000 : monthlyRemaining(total, budget);
  const goal = summary?.goal ?? profile?.goal;
  const goalProgress = demo ? 70 : goal ? Math.min(100, Math.round((goal.current_amount_krw / Math.max(goal.target_amount_krw, 1)) * 100)) : 0;

  return (
    <AppShell active="/" showAdd>
      <div className="screen home-screen">
        <header className="home-header">
          <time>{demo ? "8월 3일 월요일" : formatTodayLabel()}</time>
          <Link to={withDemo("/settings", demo)}><ModePill enabled={settings.roast_enabled} /></Link>
        </header>
        <section className="home-hero reveal-1">
          <h1>이번 달,<br />아직 <Highlight>괜찮아.</Highlight></h1>
          <BookkeeperMark />
          <p>이번 달 쓸 수 있는 돈</p>
          <strong className="hero-amount">{formatWon(remaining)}</strong>
          <span>예산의 {Math.max(0, Math.round((1 - usage) * 100))}% 남음</span>
          <div className="budget-track" aria-label={`예산 ${Math.round(usage * 100)}% 사용`}>
            <span style={{ width: `${Math.round(usage * 100)}%` }} />
          </div>
          <div className="budget-labels"><span>사용 {Math.round(usage * 100)}%</span><span>남음 {Math.max(0, Math.round((1 - usage) * 100))}%</span></div>
        </section>

        {goal && (
          <Surface className="goal-strip reveal-2">
            <Wallet size={29} />
            <strong>{goal.name} {formatCompactWon(goal.target_amount_krw)}</strong>
            <div><span>목표까지 {goalProgress}%</span><div className="mini-progress"><span style={{ width: `${goalProgress}%` }} /></div></div>
          </Surface>
        )}

        {pending ? (
          <section className="agent-brief reveal-3">
            <BookkeeperMark compact />
            <div>
              <strong>장부가 물어볼 게 있어</strong>
              <p>오늘 {formatWon(pending.amount_krw)} {pending.merchant || categoryNames[pending.category]} 결제,<br />꼭 필요했던 이유가 뭐야?</p>
              <button onClick={() => navigate(withDemo(`/transactions/${pending.transaction_id}/reason`, demo))}>이유 답하기</button>
            </div>
            <CaretRight size={24} />
          </section>
        ) : (
          <section className="agent-brief quiet reveal-3">
            <BookkeeperMark compact />
            <div><strong>밀린 질문이 없어</strong><p>지출을 기록하면 근거부터 확인할게.</p></div>
          </section>
        )}

        <section className="recent-section">
          <div className="section-heading"><h2>최근 내역</h2><Link to={withDemo("/ledger", demo)}>전체 보기 <CaretRight size={16} /></Link></div>
          <div className="flat-list">
            {transactions.slice(0, 3).map((transaction) => (
              <TransactionRow key={transaction.transaction_id} transaction={transaction} onClick={() => navigate(withDemo(`/transactions/${transaction.transaction_id}`, demo))} />
            ))}
            {transactions.length === 0 && <p className="empty-copy">첫 지출을 기록하면 이번 달 장부가 시작돼요.</p>}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function todayForInput(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function blankManualDraft(demo: boolean): TransactionDraft {
  return demo
    ? { amount_krw: 12_000, category: "cafe", merchant: "카페 온도" }
    : { amount_krw: 0, category: "other", merchant: "" };
}

function readManualDraft(key: string, demo: boolean): StoredManualDraft {
  try {
    const saved = window.localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved) as Partial<StoredManualDraft> & TransactionDraft;
      if ("draft" in parsed && parsed.draft && parsed.operationId) {
        return { draft: parsed.draft, operationId: parsed.operationId };
      }
      return { draft: parsed as TransactionDraft, operationId: crypto.randomUUID() };
    }
  } catch {
    // Start from a safe blank draft if local storage is unavailable.
  }
  return { draft: blankManualDraft(demo), operationId: crypto.randomUUID() };
}

export function ManualTransactionPage() {
  const { createTransaction, demo } = useLedger();
  const { userKey } = useAuth();
  const navigate = useNavigate();
  const draftKey = manualDraftKey(userKey, demo);
  const [storedDraft, setStoredDraft] = useState<StoredManualDraft>(() => readManualDraft(draftKey, demo));
  const { draft, operationId } = storedDraft;
  const [date, setDate] = useState(todayForInput);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    window.localStorage.setItem(draftKey, JSON.stringify(storedDraft));
  }, [draftKey, storedDraft]);

  function updateDraft(patch: Partial<TransactionDraft>) {
    setStoredDraft((current) => ({ ...current, draft: { ...current.draft, ...patch } }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.amount_krw || draft.amount_krw < 1) {
      setError("금액을 입력해 주세요.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const occurredAt = new Date(`${date}T12:00:00+09:00`).toISOString();
      const result = await createTransaction({ ...draft, occurred_at: occurredAt }, operationId);
      window.localStorage.removeItem(draftKey);
      if (result.pending_question) {
        navigate(withDemo(`/transactions/${result.transaction.transaction_id}/reason`, demo));
      } else {
        navigate(withDemo(`/judgments/${result.transaction.transaction_id}`, demo));
      }
    } catch {
      setError(navigator.onLine ? "지출을 저장하지 못했어요. 다시 시도해 주세요." : "오프라인이에요. 입력 내용은 이 기기에 보관했어요.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="standalone-screen composer-screen">
      <PageHeader title="지출 기록" right={<span className="source-pill"><i /> 수기 입력</span>} />
      <form onSubmit={submit} noValidate>
        <section className="amount-entry">
          <h1>얼마 썼어?</h1>
          <CurrencyInput className="composer-money-input" ariaLabel="금액" value={draft.amount_krw} onChange={(amount_krw) => updateDraft({ amount_krw })} />
        </section>
        <div className="transaction-type"><button className="selected" type="button">지출</button></div>
        <Surface className="composer-fields">
          <label className="field-row">
            <span className="warm-icon"><CategoryIcon category={draft.category} /></span><strong>분류</strong>
            <select value={draft.category} onChange={(event) => updateDraft({ category: event.target.value })}>
              {categories.map((category) => <option key={category} value={category}>{categoryNames[category]}</option>)}
            </select><CaretRight size={19} />
          </label>
          <label className="field-row">
            <span className="warm-icon"><MapPin size={23} /></span><strong>사용처</strong>
            <input value={draft.merchant ?? ""} placeholder="사용처 입력" onChange={(event) => updateDraft({ merchant: event.target.value })} /><CaretRight size={19} />
          </label>
          <label className="field-row">
            <span className="warm-icon"><CalendarBlank size={23} /></span><strong>날짜</strong>
            <input type="date" value={date} onChange={(event) => setDate(event.target.value)} /><CaretRight size={19} />
          </label>
          <label className="field-row">
            <span className="warm-icon"><NotePencil size={23} /></span><strong>메모</strong>
            <input value={draft.description ?? ""} placeholder="선택 입력" onChange={(event) => updateDraft({ description: event.target.value })} /><CaretRight size={19} />
          </label>
        </Surface>
        <InfoCallout>정보가 부족하면 이유를 한 번 물어봐요</InfoCallout>
        {error && <p className="form-error" role="alert">{error}</p>}
        <PrimaryButton disabled={saving}>{saving ? "기록하는 중" : "기록하고 판단받기"}</PrimaryButton>
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
  const budgetUsage = budget > 0 ? Math.round(((summary?.total_spent_krw ?? 0) / budget) * 100) : 0;
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const sameCategoryCount = Math.max(1, transactions.filter((item) => item.category === transaction.category && (demo || new Date(item.occurred_at).getTime() >= weekAgo)).length);
  return (
    <main className="standalone-screen reason-screen">
      <PageHeader title="이유 한 번만" close />
      <Surface className="reason-transaction">
        <CategoryIcon category={transaction.category} />
        <span><small>{categoryNames[transaction.category]}</small><strong>{transaction.merchant || "지출"}</strong></span>
        <time>{formatDate(transaction.occurred_at)}</time>
        <b>{formatWon(transaction.amount_krw)}</b>
      </Surface>
      <section className="reason-hero">
        <div><h1>이 지출이<br />꼭 필요했던<br /><Highlight>이유</Highlight>가 뭐야?</h1></div>
        <BookkeeperMark />
      </section>
      <div className="reason-signals"><span><i /> 생활비 예산 {budgetUsage}% 사용</span><span><CalendarBlank size={19} /> 이번 주 같은 분류 {sameCategoryCount}번째</span></div>
      <label className="reason-box">
        <span className="sr-only">지출 이유</span>
        <textarea maxLength={120} value={reason} onChange={(event) => setReason(event.target.value)} />
        <small>{reason.length} / 120</small>
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <PrimaryButton disabled={saving || !reason.trim()} onClick={() => void submit()}>{saving ? "판단하는 중" : "이유 보내기"}</PrimaryButton>
      <button className="skip-reason" onClick={() => navigate(withDemo("/", demo))}>나중에 답하기</button>
    </main>
  );
}
