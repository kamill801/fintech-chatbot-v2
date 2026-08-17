import { useMemo, useState } from "react";
import {
  ArrowLeft,
  CalendarBlank,
  CaretLeft,
  CaretRight,
  FileText,
  Lightbulb,
  LockKey,
  SignOut,
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
  ModePill,
  PrimaryButton,
  Surface,
  Toggle,
  TransactionRow,
} from "../components";
import { demoJudgment } from "../demo";
import { useAuth } from "../auth-context";
import { useLedger } from "../ledger-context";
import { Link, useNavigate } from "../router";
import type { Transaction } from "../types";
import { categoryNames, currentMonthKey, formatKoreanDate, formatMonthLabel, formatWon, withDemo } from "../utils";

function transactionDateKey(transaction: Transaction): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(transaction.occurred_at));
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
}

function shiftMonth(month: string, delta: number): string {
  const [year, monthNumber] = month.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, monthNumber - 1 + delta, 1));
  return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}`;
}

function calendarDays(month: string): Array<number | null> {
  const [year, monthNumber] = month.split("-").map(Number);
  const firstWeekday = new Date(Date.UTC(year, monthNumber - 1, 1)).getUTCDay();
  const lastDay = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  const cells: Array<number | null> = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: lastDay }, (_, index) => index + 1),
  ];
  while (cells.length % 7) cells.push(null);
  return cells;
}

function calendarWeeks(month: string): Array<Array<number | null>> {
  const days = calendarDays(month);
  return Array.from({ length: days.length / 7 }, (_, index) => days.slice(index * 7, index * 7 + 7));
}

function dayHeading(dateKey: string): string {
  const [, month, day] = dateKey.split("-").map(Number);
  return `${month}월 ${day}일 내역`;
}

export function LedgerPage() {
  const { demo, profile, summary, transactions } = useLedger();
  const navigate = useNavigate();
  const initialMonth = summary?.month ?? currentMonthKey();
  const [month, setMonth] = useState(initialMonth);
  const monthTransactions = useMemo(
    () => transactions.filter((transaction) => transactionDateKey(transaction).startsWith(month)),
    [month, transactions],
  );
  const initialTransactionDate = monthTransactions[0] ? transactionDateKey(monthTransactions[0]) : `${month}-01`;
  const [selectedDate, setSelectedDate] = useState(initialTransactionDate);
  const selectedTransactions = useMemo(
    () => monthTransactions.filter((transaction) => transactionDateKey(transaction) === selectedDate),
    [monthTransactions, selectedDate],
  );
  const totalsByDate = useMemo(() => monthTransactions.reduce<Record<string, number>>((totals, transaction) => {
    const date = transactionDateKey(transaction);
    totals[date] = (totals[date] ?? 0) + transaction.amount_krw;
    return totals;
  }, {}), [monthTransactions]);
  const monthTotal = month === summary?.month
    ? summary.total_spent_krw
    : monthTransactions.reduce((total, transaction) => total + transaction.amount_krw, 0);

  function moveMonth(delta: number) {
    const nextMonth = shiftMonth(month, delta);
    setMonth(nextMonth);
    setSelectedDate(`${nextMonth}-01`);
  }

  return (
    <AppShell active="/ledger" showAdd addTo={`/add?date=${selectedDate}`} addLabel={`${dayHeading(selectedDate).replace(" 내역", "")} 빠른 지출 추가`}>
      <div className="screen ledger-screen">
        <header className="ledger-header">
          <h1>장부</h1>
          <div className="calendar-month-control">
            <button type="button" onClick={() => moveMonth(-1)} aria-label="이전 달"><CaretLeft size={20} /></button>
            <span className="month-select" aria-label="현재 장부 월">{formatMonthLabel(month)}</span>
            <button type="button" onClick={() => moveMonth(1)} aria-label="다음 달"><CaretRight size={20} /></button>
          </div>
        </header>
        <section className="ledger-summary"><h2>이번 달 <Highlight>{formatWon(monthTotal)}</Highlight> 썼어요.</h2><p><span>수입 <strong>{formatWon(profile?.monthly_income_krw ?? 0)}</strong></span><i /><span>지출 <strong>{formatWon(monthTotal)}</strong></span></p></section>
        <Surface className="ledger-calendar">
          <div className="ledger-calendar-grid" role="grid" aria-label={`${formatMonthLabel(month)} 지출 달력`}>
            <div className="calendar-weekdays" role="row">{["일", "월", "화", "수", "목", "금", "토"].map((weekday) => <span key={weekday} role="columnheader">{weekday}</span>)}</div>
            <div className="calendar-grid" role="rowgroup">
              {calendarWeeks(month).map((week, weekIndex) => (
                <div className="calendar-week" role="row" key={`week-${weekIndex}`}>
                  {week.map((day, dayIndex) => {
                    if (!day) return <span className="calendar-empty-cell" role="gridcell" key={`empty-${weekIndex}-${dayIndex}`} />;
                    const dateKey = `${month}-${String(day).padStart(2, "0")}`;
                    const total = totalsByDate[dateKey] ?? 0;
                    const selected = dateKey === selectedDate;
                    return (
                      <div className="calendar-day-cell" role="gridcell" aria-selected={selected} key={dateKey}>
                        <button
                          type="button"
                          className={`${total ? "has-spend" : ""} ${selected ? "selected" : ""}`.trim()}
                          aria-label={`${Number(month.split("-")[1])}월 ${day}일${total ? `, 지출 ${formatWon(total)}` : ", 지출 없음"}`}
                          aria-pressed={selected}
                          onClick={() => setSelectedDate(dateKey)}
                        >
                          <span className="calendar-day-number">{day}</span>
                          {total > 0 && <small>{formatWon(total)}</small>}
                        </button>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </Surface>
        <section className="selected-day-section">
          <div className="section-heading">
            <h2>{dayHeading(selectedDate)}</h2>
            <Link to={withDemo(`/add?date=${selectedDate}`, demo)} aria-label={`${dayHeading(selectedDate).replace(" 내역", "")}에 지출 추가`}><CalendarBlank size={17} /> 지출 추가</Link>
          </div>
          <Surface className="selected-day-list">
            {selectedTransactions.length
              ? selectedTransactions.map((transaction) => <TransactionRow key={transaction.transaction_id} transaction={transaction} onClick={() => navigate(withDemo(`/transactions/${transaction.transaction_id}`, demo))} />)
              : <p className="empty-copy">아직 기록한 지출이 없어요.</p>}
          </Surface>
        </section>
      </div>
    </AppShell>
  );
}

export function AgentPage() {
  const { demo, settings, summary, transactions } = useLedger();
  const navigate = useNavigate();
  const pending = settings.roast_enabled
    ? transactions.find((item) => item.status === "awaiting_reason")
    : undefined;
  const recent = transactions.filter((item) => item.status === "judged").slice(0, 2);
  const briefing = summary?.weekly_briefing;
  const reflections = summary?.reflection_summary;
  const spendingRules = settings.spending_rules ?? [];
  return (
    <AppShell active="/agent">
      <div className="screen agent-screen">
        <header><h1>에이전트</h1><Link to={withDemo("/settings", demo)}><ModePill enabled={settings.roast_enabled} /></Link></header>
        <section className="agent-intro"><h2>{settings.roast_enabled ? <>이유는 듣고, 장부는 <Highlight>매섭게.</Highlight></> : <>장부는 자동으로, 중요한 건 <Highlight>또렷하게.</Highlight></>}</h2><BookkeeperMark compact /></section>
        {settings.roast_enabled && (
          <section className="roast-queue">
            <h3>답변 대기 <b>{pending ? 1 : 0}</b></h3>
            {pending ? (
              <section className="pending-card">
                <div><CategoryIcon category={pending.category} /><strong>{pending.merchant || categoryNames[pending.category]}</strong><b>{formatWon(pending.amount_krw)}</b></div>
                <p>그래, 이 돈은 왜 썼는지 한 번 말해봐.</p>
                <button onClick={() => navigate(withDemo(`/transactions/${pending.transaction_id}/reason`, demo))}>이유 답하기</button>
              </section>
            ) : <InfoCallout>답할 질문이 없어요. 다음 지출은 이유까지 확인해요.</InfoCallout>}
          </section>
        )}
        <section className="briefing-section">
          <div className="briefing-title">
            <div><span>내 평가와 저장된 판단을 함께 봤어요</span><h3>이번 주 AI 브리핑</h3></div>
            {briefing && <time>{Number(briefing.period_start.split("-")[1])}월 {Number(briefing.period_start.split("-")[2])}일 - {Number(briefing.period_end.split("-")[1])}월 {Number(briefing.period_end.split("-")[2])}일</time>}
          </div>
          {briefing ? (
            <Surface className="ai-briefing">
              <h2>{briefing.headline}</h2>
              <p className="briefing-summary">{briefing.summary}</p>
              <div className="briefing-metrics">
                <span><small>이번 주 지출</small><strong>{formatWon(briefing.total_spent_krw)}</strong></span>
                <span><small>가장 큰 분류</small><strong>{briefing.top_category ? categoryNames[briefing.top_category] ?? briefing.top_category : "아직 없음"}</strong></span>
                <span><small>후회한 소비</small><strong>{reflections?.regretted_count ?? 0}건</strong></span>
              </div>
              {briefing.regret_pattern && (
                <div className="regret-pattern">
                  <span>내 피드백에서 찾은 패턴</span>
                  <strong>{briefing.regret_pattern.category_name} {briefing.regret_pattern.count}건 · {formatWon(briefing.regret_pattern.spent_krw)}</strong>
                  <small>{briefing.goal_impact_days ? `${summary?.goal?.name ?? "목표"} 예상일에 약 ${briefing.goal_impact_days}일의 영향을 줬어요.` : "목표 영향은 데이터가 더 쌓이면 계산해요."}</small>
                </div>
              )}
              {briefing.evidence_state === "feedback_sparse" && <p className="learning-note">소비 평가가 더 쌓이면 반복되는 후회 패턴을 찾을 수 있어요.</p>}
              {briefing.concern && (
                <Link className="briefing-concern" to={withDemo(`/transactions/${briefing.concern.transaction_id}`, demo)}>
                  <CategoryIcon category={briefing.concern.category} />
                  <span><small>이번 주 점검할 지출</small><strong>{briefing.concern.merchant || categoryNames[briefing.concern.category]} · {formatWon(briefing.concern.amount_krw)}</strong></span>
                  <CaretRight size={19} />
                </Link>
              )}
              <div className="briefing-action"><Lightbulb size={26} /><span><small>다음 행동</small><strong>{briefing.improvement}</strong></span></div>
            </Surface>
          ) : <InfoCallout>지출을 기록하면 이번 주 흐름과 개선점을 정리해 드려요.</InfoCallout>}
        </section>
        <Surface className="personal-rules-card">
          <div><span>AI가 기억하는 기준</span><h3>내 소비 기준</h3></div>
          {spendingRules.length ? <ul>{spendingRules.slice(0, 3).map((rule) => <li key={rule}>{rule}</li>)}</ul> : <p>내가 중요하게 생각하는 소비 기준을 알려주면 판단과 브리핑에 반영해요.</p>}
          <Link to={withDemo("/settings", demo)}>{spendingRules.length ? "기준 관리" : "기준 만들기"}</Link>
        </Surface>
        <h3>최근 판단</h3>
        <Surface className="recent-judgments">
          {recent.map((transaction) => (
            <button key={transaction.transaction_id} onClick={() => navigate(withDemo(`/transactions/${transaction.transaction_id}`, demo))}><CategoryIcon category={transaction.category} /><span>{transaction.merchant || categoryNames[transaction.category]}</span><b>{formatWon(transaction.amount_krw)}</b><span className="judgment-state">판단 완료</span></button>
          ))}
          {recent.length === 0 && <p className="empty-copy">아직 완료된 판단이 없어요.</p>}
        </Surface>
      </div>
    </AppShell>
  );
}

const barColors: Record<string, string> = { food: "blue", shopping: "gold", cafe: "peach", transport: "green" };

export function ReportPage() {
  const { demo, profile, summary } = useLedger();
  const entries = Object.entries(summary?.by_category_krw ?? {}).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, amount]) => amount), 1);
  const goal = summary?.goal ?? profile?.goal;
  const goalProgress = goal ? Math.round((goal.current_amount_krw / Math.max(goal.target_amount_krw, 1)) * 100) : 0;
  const month = summary?.month ?? currentMonthKey();
  const topEntry = entries[0];
  const topCategory = topEntry?.[0] ?? "other";
  const topAmount = topEntry?.[1] ?? 0;
  const budget = summary?.discretionary_budget_krw ?? profile?.discretionary_budget_krw ?? 0;
  const budgetRemaining = budget > 0 ? Math.max(0, Math.round((1 - ((summary?.total_spent_krw ?? 0) / budget)) * 100)) : 0;
  const reflections = summary?.reflection_summary;
  return (
    <AppShell active="/report">
      <div className="screen report-screen">
        <header><h1>{Number(month.split("-")[1])}월 리포트</h1><span className="month-select" aria-label="현재 리포트 월">{formatMonthLabel(month)}</span></header>
        <h2>{topAmount > 0 ? <>이번 달, <Highlight>{categoryNames[topCategory] ?? topCategory}</Highlight> 지출이 가장 컸어요.</> : "이번 달 지출을 기록해 보세요."}</h2>
        <div className="report-totals"><span>총 지출 <strong>{formatWon(summary?.total_spent_krw ?? 0)}</strong></span><i /><span>예산 <strong>{budgetRemaining}%</strong> 남음</span></div>
        <Surface className="category-report"><h3>어디에 썼나</h3>{entries.map(([category, amount]) => <div className="report-row" key={category}><CategoryIcon category={category} /><span>{categoryNames[category] || category}</span><strong>{formatWon(amount)}</strong><div className="report-bar"><span className={barColors[category] || "blue"} style={{ width: `${Math.round((amount / max) * 66)}%` }} /></div></div>)}{entries.length === 0 && <p className="empty-copy">지출을 기록하면 카테고리별 흐름을 보여드려요.</p>}</Surface>
        <Surface className="reflection-report">
          <div><span>이번 달 소비 회고</span><h3>{reflections?.reflected_count ? `${reflections.reflected_count}건을 돌아봤어요` : "내 기준을 학습할 준비가 됐어요"}</h3></div>
          {reflections?.reflected_count ? <>
            <div className="reflection-report-metrics"><span><small>잘 쓴 돈</small><strong>{reflections.well_spent_count}건</strong></span><span><small>후회한 돈</small><strong>{formatWon(reflections.regretted_spent_krw)}</strong></span><span><small>목표 영향</small><strong>{reflections.goal_delay_days ? `약 ${reflections.goal_delay_days}일` : "영향 없음"}</strong></span></div>
            <p>{reflections.strongest_regret_category ? `${categoryNames[reflections.strongest_regret_category] ?? reflections.strongest_regret_category}에서 후회한 소비가 가장 많이 보였어요.` : "아직 반복되는 후회 패턴은 없어요."}</p>
          </> : <p>거래 상세에서 ‘잘 쓴 돈·애매함·후회함’을 남기면 나만의 소비 기준과 변화가 보여요.</p>}
        </Surface>
        {goal && <Surface className="report-goal"><Target size={28} /><strong>{goal.name} 목표</strong><div><span>현재 {goalProgress}%</span><div className="mini-progress"><span style={{ width: `${goalProgress}%` }} /></div></div><p>목표일<br /><b>{formatKoreanDate(goal.target_date)}</b></p></Surface>}
        {entries.length > 0 ? <section className="report-advice"><Lightbulb size={28} /><p>{summary?.weekly_briefing?.improvement ?? "가장 큰 지출부터 판단 근거를 확인하고 다음 주 기준을 정해 보세요."}</p><Link to={withDemo("/agent", demo)}>AI 브리핑 보기</Link></section> : <InfoCallout>첫 지출부터 기록하면 월간 패턴을 정리해 드려요.</InfoCallout>}
      </div>
    </AppShell>
  );
}

export function SettingsPage() {
  const { deleteData, demo, profile, saveSettings, settings } = useLedger();
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const [preview, setPreview] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [savingSetting, setSavingSetting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [editingRules, setEditingRules] = useState(false);
  const [ruleDraft, setRuleDraft] = useState((settings.spending_rules ?? []).join("\n"));

  async function updateMode(checked: boolean) {
    setSavingSetting(true);
    setStatus(null);
    try {
      await saveSettings({ roast_enabled: checked });
    } catch {
      setStatus("설정을 저장하지 못했어요. 다시 시도해 주세요.");
    } finally {
      setSavingSetting(false);
    }
  }

  async function removeData() {
    setDeleting(true);
    setStatus(null);
    try {
      await deleteData();
      setConfirmDelete(false);
      navigate(withDemo("/onboarding/trust", demo));
    } catch {
      setStatus("데이터를 삭제하지 못했어요. 다시 시도해 주세요.");
    } finally {
      setDeleting(false);
    }
  }

  async function saveRules() {
    const rules = ruleDraft.split("\n").map((rule) => rule.trim()).filter(Boolean).slice(0, 8);
    setSavingSetting(true);
    setStatus(null);
    try {
      await saveSettings({ spending_rules: rules });
      setEditingRules(false);
      setStatus("내 소비 기준을 저장했어요.");
    } catch {
      setStatus("소비 기준을 저장하지 못했어요. 다시 시도해 주세요.");
    } finally {
      setSavingSetting(false);
    }
  }

  async function logout() {
    setLoggingOut(true);
    setStatus(null);
    try {
      await signOut();
    } catch {
      setStatus("로그아웃하지 못했어요. 다시 시도해 주세요.");
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <main className="standalone-screen settings-screen">
      <button className="settings-back" onClick={() => navigate(-1)} aria-label="뒤로"><ArrowLeft size={31} /></button>
      <h1>설정</h1>
      <section className="roast-setting">
        <BookkeeperMark />
        <div><h2>욕쟁이 할머니 모드</h2><p>켜면 모든 지출의 이유를 묻고, 할머니 말투로 판단해요</p><button onClick={() => setPreview(!preview)}>말투 미리보기 <CaretRight size={18} /></button></div>
        <div className="setting-toggle"><Toggle checked={settings.roast_enabled} label="욕쟁이 할머니 모드" onChange={(checked) => void updateMode(checked)} /><span>{savingSetting ? "저장 중" : settings.roast_enabled ? "켜짐" : "꺼짐"}</span></div>
      </section>
      {preview && <div className="roast-preview"><strong>기본 말투</strong><p>{demoJudgment(false).message}</p><strong>욕쟁이 할머니 말투</strong><p>{demoJudgment(true).message}</p></div>}
      <Surface className="settings-list">
        <FieldRow icon={<Wallet />} label="내 자금 기준" value={profile ? `생활비 예산 ${formatWon(profile.discretionary_budget_krw)}` : "기준 미설정"} onClick={() => navigate(withDemo("/onboarding/baseline", demo))} />
        <FieldRow icon={<Target />} label="목표" value={profile ? `${profile.goal.name} · 현재 ${Math.round((profile.goal.current_amount_krw / Math.max(profile.goal.target_amount_krw, 1)) * 100)}%` : "목표 미설정"} onClick={() => navigate(withDemo("/onboarding/goal", demo))} />
        <FieldRow icon={<Lightbulb />} label="내 소비 기준" value={(settings.spending_rules ?? []).length ? `${(settings.spending_rules ?? []).length}개 기준 학습 중` : "기준 추가"} onClick={() => { setRuleDraft((settings.spending_rules ?? []).join("\n")); setEditingRules(true); }} />
        <FieldRow icon={<FileText />} label="데이터 방식" value="수기 입력 중 · 계좌 연결 준비 중" onClick={() => navigate(withDemo("/onboarding/source", demo))} />
      </Surface>
      <Surface className="settings-list privacy-settings"><h2>개인정보와 데이터</h2>
        <FieldRow icon={<UserCircle />} label="AI가 보는 정보" value="" onClick={() => setStatus("금액, 분류, 예산 신호, 직접 남긴 이유와 소비 기준만 판단에 사용해요. 만족·후회 평가는 패턴 요약에 사용해요.")} />
        <button className="danger-row" onClick={() => setConfirmDelete(true)}><Trash size={25} /><span><strong>모든 데이터 삭제</strong><small>삭제한 데이터는 복구할 수 없어요</small></span><CaretRight /></button>
      </Surface>
      <p className="data-retention-note"><LockKey size={17} /> 장부 데이터는 마지막 변경 후 최대 365일 보관되며, 직접 삭제하면 즉시 삭제돼요.</p>
      {status && <p className="settings-status" role="status">{status}</p>}
      {!demo && <button className="logout-button" disabled={loggingOut} onClick={() => void logout()}><SignOut size={21} /> {loggingOut ? "로그아웃 중" : "로그아웃"}</button>}
      <p className="version">버전 0.1</p>
      {editingRules && <div className="dialog-backdrop" onMouseDown={() => !savingSetting && setEditingRules(false)}><section className="correction-dialog rules-dialog" role="dialog" aria-modal="true" aria-labelledby="rules-title" onMouseDown={(event) => event.stopPropagation()}><h2 id="rules-title">내 소비 기준</h2><p>한 줄에 하나씩, 최대 8개까지 적어 주세요. AI가 판단과 주간 브리핑에 참고해요.</p><label>소비 기준<textarea maxLength={960} placeholder={"배달은 주 2회까지\n친구와의 만남은 월 4회까지 괜찮음\n건강 관련 지출은 우선순위가 높음"} value={ruleDraft} onChange={(event) => setRuleDraft(event.target.value)} /></label><small>{ruleDraft.split("\n").filter((rule) => rule.trim()).length}/8개</small><PrimaryButton disabled={savingSetting || ruleDraft.split("\n").filter((rule) => rule.trim()).length > 8} onClick={() => void saveRules()}>{savingSetting ? "저장 중" : "기준 저장"}</PrimaryButton><button className="text-button" disabled={savingSetting} onClick={() => setEditingRules(false)}>취소</button></section></div>}
      {confirmDelete && <div className="dialog-backdrop" onMouseDown={() => !deleting && setConfirmDelete(false)}><section className="correction-dialog delete-dialog" role="alertdialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}><LockKey size={32} /><h2>모든 데이터를 삭제할까요?</h2><p>프로필, 지출, 이유, 판단, 소비 평가와 개인 기준이 삭제되고 복구할 수 없어요.</p><PrimaryButton disabled={deleting} onClick={() => void removeData()}>{deleting ? "삭제 중" : "삭제하기"}</PrimaryButton><button className="text-button" disabled={deleting} onClick={() => setConfirmDelete(false)}>취소</button></section></div>}
    </main>
  );
}
