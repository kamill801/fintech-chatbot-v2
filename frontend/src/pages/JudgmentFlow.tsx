import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarBlank,
  Check,
  Copy,
  DownloadSimple,
  Lightbulb,
  LockKey,
  MapPin,
  NotePencil,
  PencilSimple,
  ShareNetwork,
  Sparkle,
  Wallet,
} from "@phosphor-icons/react";
import {
  BookkeeperMark,
  EvidenceList,
  Highlight,
  JudgmentBadge,
  ModePill,
  PageHeader,
  PrimaryButton,
  Surface,
  TextButton,
  Toggle,
} from "../components";
import { demoJudgment } from "../demo";
import { useLedger } from "../ledger-context";
import { Link, useNavigate, useParams } from "../router";
import type { Judgment, JudgmentLabel, SharePayload, TransactionDetail } from "../types";
import { categoryNames, confidenceText, formatDate, formatTime, formatWon, labelText, withDemo } from "../utils";

function useTransactionDetail(transactionId: string) {
  const { getTransaction, settings } = useLedger();
  const [detail, setDetail] = useState<TransactionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(async () => {
    try {
      setDetail(await getTransaction(transactionId));
      setError(null);
    } catch {
      setError("거래 판단을 불러오지 못했어요.");
    }
  }, [getTransaction, transactionId]);
  useEffect(() => { void reload(); }, [reload, settings.roast_enabled]);
  return { detail, error, reload };
}

export function JudgmentPage() {
  const { transactionId = "" } = useParams();
  const { demo, saveSettings, settings } = useLedger();
  const navigate = useNavigate();
  const { detail, error, reload } = useTransactionDetail(transactionId);
  const [notice, setNotice] = useState<string | null>(null);

  async function toggleMode() {
    await saveSettings({ roast_enabled: !settings.roast_enabled });
    await reload();
  }

  if (error) return <main className="standalone-screen"><PageHeader title="지출 판단" close /><p className="form-error">{error}</p></main>;
  if (!detail?.judgment) return <div className="loading-screen">판단 근거를 정리하는 중</div>;
  const { transaction, judgment } = detail;

  return (
    <main className={`standalone-screen judgment-screen ${settings.roast_enabled ? "roast-view" : ""}`}>
      <PageHeader title="지출 판단" close right={<button className="mode-button" onClick={() => void toggleMode()}><ModePill enabled={settings.roast_enabled} /></button>} />
      <Surface className="judgment-transaction">
        <span className="warm-icon">☕</span><strong>{transaction.merchant || categoryNames[transaction.category]}</strong><b>{formatWon(transaction.amount_krw)}</b>
      </Surface>
      <div className="judgment-meta"><JudgmentBadge label={judgment.label} /><span>{confidenceText(judgment.confidence)} · {Math.round(judgment.confidence * 100)}%</span></div>
      <section className="judgment-headline">
        <h1>{settings.roast_enabled ? (
          <>사정은 알겠는데,<br />카페에 <Highlight>네 이름</Highlight><br />박을 셈이냐?</>
        ) : (
          <>필요했지만,<br />이번 주는 <Highlight>여기까지.</Highlight></>
        )}</h1>
        {settings.roast_enabled && <BookkeeperMark compact />}
        <p className="server-message">{judgment.message}</p>
      </section>
      <h2>판단 근거</h2>
      <EvidenceList judgment={judgment} transaction={transaction} />
      <div className="recommendation"><span className="idea-icon"><Lightbulb size={28} /></span><p>{judgment.recommended_action}</p></div>
      {notice && <p className="success-notice" role="status"><Check size={18} /> {notice}</p>}
      <PrimaryButton onClick={() => setNotice("이번 주 계획에 반영했어요.")}>이번 주 계획에 반영</PrimaryButton>
      <TextButton onClick={() => navigate(withDemo(`/transactions/${transaction.transaction_id}`, demo))}>판단 수정</TextButton>
      <Link className="secondary-link" to={withDemo(`/share/${transaction.transaction_id}`, demo)}>결과 공유</Link>
    </main>
  );
}

export function TransactionDetailPage() {
  const { transactionId = "" } = useParams();
  const { correctJudgment, demo } = useLedger();
  const { detail, error, reload } = useTransactionDetail(transactionId);
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState<JudgmentLabel>("justified");
  const [reason, setReason] = useState("필요한 만남이었어요.");
  const [saving, setSaving] = useState(false);

  async function saveCorrection() {
    if (!detail?.judgment) return;
    setSaving(true);
    await correctJudgment(detail.judgment.judgment_id, label, reason);
    setEditing(false);
    setSaving(false);
    await reload();
  }

  if (error) return <main className="standalone-screen"><PageHeader title="거래 상세" /><p className="form-error">{error}</p></main>;
  if (!detail) return <div className="loading-screen">거래를 불러오는 중</div>;
  const { transaction, judgment } = detail;
  return (
    <main className="standalone-screen transaction-detail-screen">
      <PageHeader title="거래 상세" right={<span>•••</span>} />
      <section className="detail-hero">
        <h1>{formatWon(transaction.amount_krw)}</h1>
        <div><span className="detail-icon">☕</span><p><strong>{transaction.merchant || categoryNames[transaction.category]}</strong><small>{categoryNames[transaction.category]}</small></p></div>
        <span className="source-pill">수기 입력</span>
      </section>
      <Surface className="detail-fields">
        <div><strong>날짜</strong><span>{formatDate(transaction.occurred_at)} · {formatTime(transaction.occurred_at)}</span></div>
        <div><strong>메모</strong><span className="muted">{transaction.description || "선택 입력 없음"}</span></div>
      </Surface>
      {judgment && (
        <Surface className="detail-judgment">
          <h2>AI 판단</h2>
          <JudgmentBadge label={judgment.effective_label || judgment.label} confidence={judgment.confidence} />
          <p>{judgment.rationale}</p>
          {judgment.correction && <small>원래 판단: {labelText(judgment.original_label || judgment.label)} · 내가 수정함</small>}
        </Surface>
      )}
      {transaction.reason && <div className="my-reason"><strong>내가 답한 이유</strong><p>{transaction.reason}</p></div>}
      <Surface className="history-card">
        <h2>기록</h2>
        <div><PencilSimple /> <time>{formatTime(transaction.created_at)}</time> 지출 기록</div>
        {transaction.reason && <div><NotePencil /> <time>{formatTime(transaction.occurred_at)}</time> 이유 답변</div>}
        {judgment && <div><Sparkle /> <time>{formatTime(transaction.occurred_at)}</time> 판단 완료</div>}
      </Surface>
      {judgment && <button className="outline-button" onClick={() => setEditing(true)}><PencilSimple size={21} /> 판단 수정</button>}
      <TextButton onClick={() => window.alert("거래 원문 수정은 다음 버전에서 지원해요. 판단 수정은 지금 바로 남길 수 있어요.")}>거래 내용 수정</TextButton>
      <p className="muted detail-footnote">수정해도 원래 판단과 기록은 남아요</p>

      {editing && (
        <div className="dialog-backdrop" role="presentation" onMouseDown={() => setEditing(false)}>
          <section className="correction-dialog" role="dialog" aria-modal="true" aria-labelledby="correction-title" onMouseDown={(event) => event.stopPropagation()}>
            <h2 id="correction-title">판단 수정</h2>
            <p>원래 판단은 보존되고, 수정 기록이 추가돼요.</p>
            <label>내 판단<select value={label} onChange={(event) => setLabel(event.target.value as JudgmentLabel)}><option value="justified">납득 가능한 지출</option><option value="caution">주의가 필요한 지출</option><option value="overspending">과소비</option><option value="insufficient_context">정보 부족</option></select></label>
            <label>수정 이유<textarea value={reason} onChange={(event) => setReason(event.target.value)} /></label>
            <PrimaryButton disabled={saving} onClick={() => void saveCorrection()}>{saving ? "저장 중" : "수정 기록 남기기"}</PrimaryButton>
            <TextButton onClick={() => setEditing(false)}>취소</TextButton>
          </section>
        </div>
      )}
      <Link className="sr-only" to={withDemo("/ledger", demo)}>장부로</Link>
    </main>
  );
}

interface ShareOptions {
  judgment: boolean;
  recommendation: boolean;
  amount: boolean;
  merchant: boolean;
}

function roundedRect(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  context.beginPath();
  context.roundRect(x, y, width, height, radius);
  context.fill();
}

async function shareCardImage(
  payload: SharePayload,
  detail: TransactionDetail,
  options: ShareOptions,
): Promise<File> {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1350;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("canvas unavailable");
  context.fillStyle = "#F6F3EC";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#07113C";
  roundedRect(context, 80, 90, 920, 1170, 44);
  context.fillStyle = "#E95B43";
  context.font = "700 42px sans-serif";
  context.fillText("장부지기의 한마디", 155, 220);
  context.fillStyle = "#FFF8E7";
  context.font = "700 65px sans-serif";
  const words = payload.roast_message.split(" ");
  let line = "";
  let y = 365;
  for (const word of words) {
    const test = `${line}${word} `;
    if (context.measureText(test).width > 760) {
      context.fillText(line, 150, y);
      line = `${word} `;
      y += 92;
    } else line = test;
  }
  context.fillText(line, 150, y);
  context.strokeStyle = "#DED8CF";
  context.beginPath();
  context.moveTo(150, 850);
  context.lineTo(930, 850);
  context.stroke();
  context.font = "500 38px sans-serif";
  if (options.judgment) context.fillText(`판단 · ${labelText(payload.label)}`, 150, 945);
  if (options.recommendation) context.fillText(payload.recommended_action.slice(0, 28), 150, 1025);
  if (options.amount) context.fillText(`금액 · ${formatWon(detail.transaction.amount_krw)}`, 150, 1105);
  if (options.merchant) context.fillText(`사용처 · ${detail.transaction.merchant || "미입력"}`, 150, 1185);
  const blob = await new Promise<Blob>((resolve, reject) => canvas.toBlob((result) => result ? resolve(result) : reject(new Error("image export failed")), "image/png"));
  return new File([blob], "jangbu-roast.png", { type: "image/png" });
}

export function SharePage() {
  const { transactionId = "" } = useParams();
  const { demo, settings, share } = useLedger();
  const navigate = useNavigate();
  const { detail } = useTransactionDetail(transactionId);
  const [options, setOptions] = useState<ShareOptions>({ judgment: true, recommendation: true, amount: false, merchant: false });
  const [payload, setPayload] = useState<SharePayload | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const previewJudgment: Judgment = useMemo(() => demoJudgment(true), []);

  useEffect(() => {
    if (demo) setPayload({ label: previewJudgment.label, roast_message: previewJudgment.message, category: "cafe", recommended_action: previewJudgment.recommended_action });
  }, [demo, previewJudgment]);

  async function publish(downloadOnly = false) {
    if (!detail) return;
    if (!settings.roast_enabled && !demo) {
      setStatus("Roast 모드를 켠 판단만 공유할 수 있어요.");
      return;
    }
    try {
      const nextPayload = payload ?? await share(detail.judgment?.judgment_id ?? "");
      setPayload(nextPayload);
      const file = await shareCardImage(nextPayload, detail, options);
      if (!downloadOnly && navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ title: "내 장부 판단", files: [file] });
        setStatus("공유 창을 열었어요.");
        return;
      }
      const url = URL.createObjectURL(file);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = file.name;
      anchor.click();
      URL.revokeObjectURL(url);
      setStatus("이미지로 저장했어요.");
    } catch {
      setStatus("공유 이미지를 만들지 못했어요.");
    }
  }

  if (!detail) return <div className="loading-screen">공유 화면을 준비하는 중</div>;
  const copy = payload?.roast_message ?? previewJudgment.message;
  return (
    <main className="standalone-screen share-screen">
      <PageHeader title="결과 공유" close />
      <h1>웃기더라도, <Highlight>내 돈</Highlight>은 가리고.</h1>
      <section className="share-card" aria-label="공유 이미지 미리보기">
        <div className="share-stamp"><BookkeeperMark compact /><strong>장부지기의 한마디</strong></div>
        <blockquote>{copy}</blockquote>
        <div className="share-meta"><span><CalendarBlank size={20} /> 이번 주 같은 분류 3번째</span><strong>판단 · {labelText(previewJudgment.label)}</strong><span><Copy size={22} /> 내 장부</span></div>
      </section>
      <Surface className="share-options">
        <h2>공유에 포함</h2>
        {([
          ["judgment", "판단 결과", <Wallet size={21} />],
          ["recommendation", "추천 행동", <Lightbulb size={21} />],
          ["amount", "금액", <span aria-hidden="true">₩</span>],
          ["merchant", "사용처", <MapPin size={21} />],
        ] as const).map(([key, label, icon]) => (
          <div className="share-option" key={key}><span className="warm-icon">{icon}</span><strong>{label}</strong><Toggle checked={options[key]} label={`${label} 포함`} onChange={(checked) => setOptions({ ...options, [key]: checked })} /></div>
        ))}
      </Surface>
      <p className="privacy-note"><LockKey size={17} /> 기본값은 민감한 정보를 가려요</p>
      {status && <p className="success-notice" role="status">{status}</p>}
      <PrimaryButton onClick={() => void publish(false)}><ShareNetwork size={22} /> 이미지로 공유</PrimaryButton>
      <TextButton onClick={() => void publish(true)}><DownloadSimple size={20} /> 이미지 저장</TextButton>
      <button className="sr-only" onClick={() => navigate(-1)}>닫기</button>
    </main>
  );
}
