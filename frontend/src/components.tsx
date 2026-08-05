import { useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import {
  ArrowLeft,
  Basket,
  BookOpenText,
  Bus,
  CalendarBlank,
  CaretRight,
  ChartBar,
  Coffee,
  ForkKnife,
  Gear,
  House,
  Lightbulb,
  Plus,
  ShieldCheck,
  ShoppingBag,
  UserCircle,
  Wallet,
  X,
} from "@phosphor-icons/react";
import { useLedger } from "./ledger-context";
import { NavLink, useNavigate } from "./router";
import type { Judgment, JudgmentLabel, Transaction } from "./types";
import { categoryNames, formatTime, formatWon, labelText, withDemo } from "./utils";

export function Highlight({ children }: { children: ReactNode }) {
  return <span className="highlight">{children}</span>;
}

export function Surface({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`surface ${className}`}>{children}</section>;
}

export function PrimaryButton({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`primary-button ${className}`} {...props} />;
}

export function CurrencyInput({
  ariaLabel,
  className = "",
  id,
  minimum = 0,
  onChange,
  value,
}: {
  ariaLabel: string;
  className?: string;
  id?: string;
  minimum?: number;
  onChange(value: number): void;
  value: number;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value));

  useEffect(() => {
    if (!editing) setDraft(String(value));
  }, [editing, value]);

  function commit() {
    const parsed = draft === "" ? minimum : Number(draft);
    onChange(Math.max(minimum, Number.isSafeInteger(parsed) ? parsed : minimum));
    setEditing(false);
  }

  return (
    <span className={`currency-input ${className}`}>
      <input
        id={id}
        type="text"
        inputMode="numeric"
        pattern="[0-9]*"
        maxLength={15}
        aria-label={ariaLabel}
        value={editing ? draft : Math.round(value).toLocaleString("ko-KR")}
        onFocus={(event) => {
          setDraft(String(value));
          setEditing(true);
          event.currentTarget.select();
        }}
        onChange={(event) => {
          const next = event.target.value.replace(/[^0-9]/g, "").slice(0, 15);
          setDraft(next);
          if (next !== "") onChange(Math.max(minimum, Number(next)));
        }}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") event.currentTarget.blur();
        }}
      />
      <span aria-hidden="true">원</span>
    </span>
  );
}

export function TextButton({ className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={`text-button ${className}`} {...props} />;
}

export function PageHeader({
  title,
  close = false,
  right,
}: {
  title: string;
  close?: boolean;
  right?: ReactNode;
}) {
  const navigate = useNavigate();
  return (
    <header className="page-header">
      <button className="icon-button" aria-label={close ? "닫기" : "뒤로"} onClick={() => navigate(-1)}>
        {close ? <X size={29} /> : <ArrowLeft size={29} />}
      </button>
      <h1>{title}</h1>
      <div className="page-header-right">{right}</div>
    </header>
  );
}

export function ModePill({ enabled }: { enabled: boolean }) {
  return (
    <span className={`mode-pill ${enabled ? "is-roast" : ""}`} aria-label={`Roast ${enabled ? "켜짐" : "꺼짐"}`}>
      <span className="mode-dot" /> Roast {enabled ? "켜짐" : "꺼짐"}
    </span>
  );
}

export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange(checked: boolean): void;
  label: string;
}) {
  return (
    <button
      type="button"
      className={`toggle ${checked ? "is-on" : ""}`}
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
    >
      <span />
    </button>
  );
}

export function BookkeeperMark({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`bookkeeper ${compact ? "bookkeeper-compact" : ""}`} aria-label="장부지기">
      <UserCircle size={compact ? 36 : 64} weight="duotone" />
      {!compact && <span>장부지기</span>}
    </div>
  );
}

export function CategoryIcon({ category, size = 22 }: { category: string; size?: number }) {
  const icon = (() => {
    switch (category) {
      case "cafe":
        return <Coffee size={size} />;
      case "food":
        return <ForkKnife size={size} />;
      case "transport":
        return <Bus size={size} />;
      case "shopping":
        return <ShoppingBag size={size} />;
      case "housing":
        return <House size={size} />;
      case "health":
        return <ShieldCheck size={size} />;
      default:
        return <Basket size={size} />;
    }
  })();
  return <span className={`category-icon category-${category}`}>{icon}</span>;
}

export function TransactionRow({ transaction, onClick }: { transaction: Transaction; onClick?(): void }) {
  return (
    <button className="transaction-row" onClick={onClick} type="button">
      <CategoryIcon category={transaction.category} />
      <span className="transaction-copy">
        <strong>{transaction.merchant || categoryNames[transaction.category] || "지출"}</strong>
        <small>{categoryNames[transaction.category] || transaction.category}</small>
      </span>
      <time>{formatTime(transaction.occurred_at)}</time>
      <strong className="transaction-amount">{formatWon(transaction.amount_krw)}</strong>
      {onClick && <CaretRight size={18} />}
    </button>
  );
}

export function JudgmentBadge({ label, confidence }: { label: JudgmentLabel; confidence?: number }) {
  return (
    <span className={`judgment-badge judgment-${label}`}>
      {labelText(label)}
      {confidence !== undefined && ` · ${Math.round(confidence * 100)}%`}
    </span>
  );
}

export function EvidenceList({ judgment, transaction }: { judgment: Judgment; transaction: Transaction }) {
  const rows = [
    { icon: <Wallet size={21} />, text: judgment.rationale.split(".")[0] || "예산 영향 반영" },
    { icon: <CalendarBlank size={21} />, text: `${categoryNames[transaction.category] || "같은 분류"} 반복 지출 반영` },
    { icon: <UserCircle size={21} />, text: transaction.reason ? "내가 답한 이유 반영" : "입력된 거래 맥락 반영" },
  ];
  return (
    <Surface className="evidence-list">
      {rows.map((row) => (
        <div className="evidence-row" key={row.text}>
          <span className="warm-icon">{row.icon}</span>
          <span>{row.text}</span>
        </div>
      ))}
    </Surface>
  );
}

const navItems = [
  { to: "/", label: "홈", icon: House },
  { to: "/ledger", label: "장부", icon: BookOpenText },
  { to: "/agent", label: "에이전트", icon: UserCircle },
  { to: "/report", label: "리포트", icon: ChartBar },
];

export function AppShell({ children, active, showAdd = false }: { children: ReactNode; active?: string; showAdd?: boolean }) {
  const { demo } = useLedger();
  return (
    <div className="app-shell">
      <aside className="desktop-rail" aria-label="주요 메뉴">
        <div className="rail-brand"><BookOpenText size={30} /> 내 장부</div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={withDemo(item.to, demo)} className={({ isActive }) => (isActive || active === item.to ? "is-active" : "")}>
                <Icon size={23} /> {item.label}
              </NavLink>
            );
          })}
          <NavLink to={withDemo("/settings", demo)}><Gear size={23} /> 설정</NavLink>
        </nav>
        <NavLink className="rail-add" to={withDemo("/add", demo)}><Plus size={22} /> 지출 기록</NavLink>
      </aside>
      <main className="app-content">{children}</main>
      {showAdd && <NavLink className="floating-add" to={withDemo("/add", demo)} aria-label="지출 기록 추가"><Plus size={32} /></NavLink>}
      <nav className="bottom-nav" aria-label="주요 메뉴">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink key={item.to} to={withDemo(item.to, demo)} className={({ isActive }) => (isActive || active === item.to ? "is-active" : "")}>
              <Icon size={25} weight={active === item.to ? "fill" : "regular"} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}

export function InfoCallout({ children }: { children: ReactNode }) {
  return <div className="info-callout"><Lightbulb size={27} /> <span>{children}</span></div>;
}

export function FieldRow({
  icon,
  label,
  value,
  onClick,
  muted = false,
}: {
  icon?: ReactNode;
  label: string;
  value: ReactNode;
  onClick?(): void;
  muted?: boolean;
}) {
  const content = (
    <>
      {icon && <span className="warm-icon">{icon}</span>}
      <strong>{label}</strong>
      <span className={muted ? "muted" : ""}>{value}</span>
      {onClick && <CaretRight size={19} />}
    </>
  );
  return onClick ? <button className="field-row" onClick={onClick}>{content}</button> : <div className="field-row">{content}</div>;
}
