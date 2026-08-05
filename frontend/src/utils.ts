import type { JudgmentLabel } from "./types";

export const categoryNames: Record<string, string> = {
  cafe: "카페·간식",
  food: "식비",
  transport: "교통",
  shopping: "쇼핑",
  housing: "주거",
  health: "건강",
  education: "교육",
  leisure: "여가",
  other: "기타",
};

export function formatWon(value: number): string {
  return `${Math.round(value).toLocaleString("ko-KR")}원`;
}

export function formatCompactWon(value: number): string {
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString("ko-KR")}만원`;
  return formatWon(value);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date(value));
}

export function formatTime(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

export function formatTodayLabel(value = new Date()): string {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "long",
    day: "numeric",
    weekday: "long",
  }).format(value);
}

export function currentMonthKey(value = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
  }).formatToParts(value);
  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  return year && month ? `${year}-${month}` : "";
}

export function formatMonthLabel(value: string): string {
  const [year, month] = value.split("-").map(Number);
  return Number.isInteger(year) && Number.isInteger(month) ? `${year}년 ${month}월` : value;
}

export function formatKoreanDate(value: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(new Date(value));
}

export function labelText(label: JudgmentLabel): string {
  return {
    justified: "납득 가능한 지출",
    caution: "주의가 필요한 지출",
    overspending: "과소비",
    insufficient_context: "정보가 더 필요함",
  }[label];
}

export function confidenceText(confidence: number): string {
  if (confidence >= 0.8) return "어느 정도 확실함";
  if (confidence >= 0.65) return "조금 더 볼 필요 있음";
  return "정보가 더 필요함";
}

export function withDemo(path: string, demo: boolean): string {
  return demo ? `${path}${path.includes("?") ? "&" : "?"}demo=1` : path;
}
