import { useMemo, useState } from "react";
import {
  ArrowLeft,
  CalendarBlank,
  CaretDown,
  CaretRight,
  FileText,
  Lightbulb,
  LinkSimple,
  LockKey,
  MagnifyingGlass,
  SlidersHorizontal,
  Target,
  Trash,
  UserCircle,
  Wallet,
} from "@phosphor-icons/react";
import {
  AppShell,
  BookkeeperMark,
  CategoryIcon,
  FieldRow,
  Highlight,
  InfoCallout,
  JudgmentBadge,
  ModePill,
  PrimaryButton,
  Surface,
  Toggle,
  TransactionRow,
} from "../components";
import { demoJudgment } from "../demo";
import { useLedger } from "../ledger-context";
import { Link, useNavigate } from "../router";
import type { Transaction } from "../types";
import { categoryNames, formatWon, withDemo } from "../utils";

function groupTransactions(transactions: Transaction[]) {
  const groups = new Map<string, Transaction[]>();
  for (const transaction of transactions) {
    const key = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "long", day: "numeric" }).format(new Date(transaction.occurred_at));
    groups.set(key, [...(groups.get(key) ?? []), transaction]);
  }
  return [...groups.entries()];
}

export function LedgerPage() {
  const { demo, profile, summary, transactions } = useLedger();
  const navigate = useNavigate();
  const [view, setView] = useState<"list" | "calendar">("list");
  const groups = useMemo(() => groupTransactions(transactions), [transactions]);
  return (
    <AppShell active="/ledger" showAdd>
      <div className="screen ledger-screen">
        <header className="ledger-header"><h1>장부</h1><button className="month-select">2026년 8월 <CaretDown /></button><button className="icon-button" aria-label="검색"><MagnifyingGlass size={27} /></button><button className="icon-button" aria-label="필터"><SlidersHorizontal size={27} /></button></header>
        <div className="segmented-control"><button className={view === "list" ? "selected" : ""} onClick={() => setView("list")}>내역</button><button className={view === "calendar" ? "selected" : ""} onClick={() => setView("calendar")}>달력</button></div>
        <section className="ledger-summary"><h2>이번 달 <Highlight>{formatWon(summary?.total_spent_krw || 377_500)}</Highlight> 썼어.</h2><p><span>수입 <strong>{formatWon(profile?.monthly_income_krw || 3_500_000)}</strong></span><i /><span>지출 <strong>{formatWon(summary?.total_spent_krw || 377_500)}</strong></span></p></section>
        {view === "calendar" ? (
          <Surface className="calendar-placeholder">
            <CalendarBlank size={38} /><h2>8월 지출 달력</h2><p>날짜를 누르면 그날의 지출을 보여줘요.</p>
            <div className="calendar-grid">{Array.from({ length: 31 }, (_, index) => <button key={index + 1} className={[2, 3].includes(index + 1) ? "has-spend" : ""}>{index + 1}</button>)}</div>
          </Surface>
        ) : (
          <Surface className="ledger-list">
            {groups.length ? groups.map(([date, items], index) => (
              <div className="ledger-day" key={date}><h3>{index === 0 ? "오늘" : "이전"} · {date}</h3>{items.map((transaction) => <TransactionRow key={transaction.transaction_id} transaction={transaction} onClick={() => navigate(withDemo(`/transactions/${transaction.transaction_id}`, demo))} />)}</div>
            )) : <p className="empty-copy">아직 기록한 지출이 없어요.</p>}
          </Surface>
        )}
      </div>
    </AppShell>
  );
}

export function AgentPage() {
  const { demo, settings, transactions } = useLedger();
  const navigate = useNavigate();
  const pending = transactions.find((item) => item.status === "awaiting_reason") ?? (demo ? transactions[0] : undefined);
  const recent = transactions.filter((item) => item.status === "judged").slice(0, 2);
  return (
    <AppShell active="/agent">
      <div className="screen agent-screen">
        <header><h1>에이전트</h1><Link to={withDemo("/settings", demo)}><ModePill enabled={settings.roast_enabled} /></Link></header>
        <section className="agent-intro"><h2>물어볼 건 <Highlight>먼저,</Highlight> 잔소리는 나중에.</h2><BookkeeperMark compact /></section>
        <h3>답변 대기 <b>{pending ? 1 : 0}</b></h3>
        {pending ? (
          <section className="pending-card">
            <div><CategoryIcon category={pending.category} /><strong>{pending.merchant || categoryNames[pending.category]}</strong><b>{formatWon(pending.amount_krw)}</b></div>
            <p>꼭 필요했던 이유가 뭐야?</p>
            <button onClick={() => navigate(withDemo(`/transactions/${pending.transaction_id}/reason`, demo))}>이유 답하기</button>
          </section>
        ) : <InfoCallout>답할 질문이 없어요. 다음 지출을 기록하면 먼저 확인할게요.</InfoCallout>}
        <Surface className="weekly-word">
          <h3>이번 주 한마디</h3>
          <div><Wallet size={25} /> 생활비 예산 <strong>62%</strong> 사용</div>
          <div><CategoryIcon category="cafe" /> 카페 지출 <strong className="caution-text">3회</strong></div>
          <div className="weekly-advice"><Lightbulb size={26} /><p>이번 주 카페는 여기까지 하고<br />다음 만남은 산책 어때?</p></div>
        </Surface>
        <h3>최근 판단</h3>
        <Surface className="recent-judgments">
          {recent.map((transaction, index) => (
            <button key={transaction.transaction_id} onClick={() => navigate(withDemo(`/transactions/${transaction.transaction_id}`, demo))}><CategoryIcon category={transaction.category} /><span>{transaction.merchant || categoryNames[transaction.category]}</span><b>{formatWon(transaction.amount_krw)}</b><JudgmentBadge label={index === 0 ? "justified" : "caution"} /></button>
          ))}
        </Surface>
      </div>
    </AppShell>
  );
}

const barColors: Record<string, string> = { food: "blue", shopping: "gold", cafe: "peach", transport: "green" };

export function ReportPage() {
  const { profile, summary } = useLedger();
  const [applied, setApplied] = useState(false);
  const entries = Object.entries(summary?.by_category_krw ?? { food: 160_000, shopping: 95_000, cafe: 72_000, transport: 50_500 }).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, amount]) => amount), 1);
  const goal = summary?.goal ?? profile?.goal;
  const goalProgress = goal ? Math.round((goal.current_amount_krw / Math.max(goal.target_amount_krw, 1)) * 100) : 70;
  return (
    <AppShell active="/report">
      <div className="screen report-screen">
        <header><h1>8월 리포트</h1><button className="month-select">2026년 8월 <CaretDown /></button></header>
        <h2>이번 달, <Highlight>카페</Highlight>가 발목 잡았어.</h2>
        <div className="report-totals"><span>총 지출 <strong>{formatWon(summary?.total_spent_krw || 377_500)}</strong></span><i /><span>예산 <strong>52%</strong> 남음</span></div>
        <Surface className="category-report"><h3>어디에 썼나</h3>{entries.map(([category, amount]) => <div className="report-row" key={category}><CategoryIcon category={category} /><span>{categoryNames[category] || category}</span><strong>{formatWon(amount)}</strong><div className="report-bar"><span className={barColors[category] || "blue"} style={{ width: `${Math.round((amount / max) * 66)}%` }} /></div></div>)}</Surface>
        {goal && <Surface className="report-goal"><Target size={28} /><strong>{goal.name} 목표</strong><div><span>현재 {goalProgress}%</span><div className="mini-progress"><span style={{ width: `${goalProgress}%` }} /></div></div><p>이대로면 목표가<br /><b>8일</b> 늦어질 수 있어</p></Surface>}
        <section className="report-advice"><Lightbulb size={28} /><p>다음 7일은 카페 예산을 쉬고<br />72,000원을 목표에 남겨두자.</p><button onClick={() => setApplied(true)}>{applied ? "반영 완료" : "다음 주 계획에 반영"}</button></section>
      </div>
    </AppShell>
  );
}

export function SettingsPage() {
  const { deleteData, demo, profile, saveSettings, settings } = useLedger();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  async function removeData() {
    await deleteData();
    setConfirmDelete(false);
    navigate(withDemo("/onboarding/trust", demo));
  }

  return (
    <main className="standalone-screen settings-screen">
      <button className="settings-back" onClick={() => navigate(-1)} aria-label="뒤로"><ArrowLeft size={31} /></button>
      <h1>설정</h1>
      <section className="roast-setting">
        <BookkeeperMark />
        <div><h2>Roast 모드</h2><p>말투만 바뀌고 판단과 추천은 같아요</p><button onClick={() => setPreview(!preview)}>말투 미리보기 <CaretRight size={18} /></button></div>
        <div className="setting-toggle"><Toggle checked={settings.roast_enabled} label="Roast 모드" onChange={(checked) => void saveSettings({ roast_enabled: checked })} /><span>{settings.roast_enabled ? "켜짐" : "꺼짐"}</span></div>
      </section>
      {preview && <div className="roast-preview"><strong>Normal</strong><p>{demoJudgment(false).message}</p><strong>Roast</strong><p>{demoJudgment(true).message}</p></div>}
      <Surface className="settings-list">
        <FieldRow icon={<Wallet />} label="내 자금 기준" value={`생활비 예산 ${formatWon(profile?.discretionary_budget_krw || 800_000)}`} onClick={() => navigate(withDemo("/onboarding/baseline", demo))} />
        <FieldRow icon={<Target />} label="목표" value={`${profile?.goal.name || "비상금"} · 현재 ${profile ? Math.round((profile.goal.current_amount_krw / profile.goal.target_amount_krw) * 100) : 70}%`} onClick={() => navigate(withDemo("/onboarding/goal", demo))} />
        <FieldRow icon={<FileText />} label="데이터 방식" value="수기 입력 중 · 계좌 연결 준비 중" onClick={() => navigate(withDemo("/onboarding/source", demo))} />
      </Surface>
      <Surface className="settings-list privacy-settings"><h2>개인정보와 데이터</h2>
        <FieldRow icon={<UserCircle />} label="AI가 보는 정보" value="" onClick={() => setStatus("금액, 분류, 예산 신호와 직접 답한 이유만 판단에 사용해요.")} />
        <FieldRow icon={<LinkSimple />} label="연결 권한 철회" value="" onClick={() => setStatus("현재 연결된 계좌가 없어요.")} />
        <button className="danger-row" onClick={() => setConfirmDelete(true)}><Trash size={25} /><span><strong>모든 데이터 삭제</strong><small>삭제한 데이터는 복구할 수 없어요</small></span><CaretRight /></button>
      </Surface>
      {status && <p className="settings-status" role="status">{status}</p>}
      <p className="version">버전 0.1</p>
      {confirmDelete && <div className="dialog-backdrop" onMouseDown={() => setConfirmDelete(false)}><section className="correction-dialog delete-dialog" role="alertdialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}><LockKey size={32} /><h2>모든 데이터를 삭제할까요?</h2><p>프로필, 지출, 이유, 판단 기록이 삭제되고 복구할 수 없어요.</p><PrimaryButton onClick={() => void removeData()}>삭제하기</PrimaryButton><button className="text-button" onClick={() => setConfirmDelete(false)}>취소</button></section></div>}
    </main>
  );
}
