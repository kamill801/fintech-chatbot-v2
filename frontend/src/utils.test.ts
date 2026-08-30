import { describe, expect, it } from "vitest";
import { confidenceText, createClientId, currentMonthKey, formatCalendarWon, formatCompactWon, formatMonthLabel, formatTodayLabel, formatWon, labelText, withDemo } from "./utils";

describe("Korean ledger formatting", () => {
  it("formats won without decimals", () => {
    expect(formatWon(623000)).toBe("623,000원");
    expect(formatCompactWon(10000000)).toBe("1,000만원");
    expect(formatCalendarWon(78500)).toBe("7.9만");
    expect(formatCalendarWon(9000)).toBe("9천");
  });

  it("uses plain-language judgment labels", () => {
    expect(labelText("caution")).toBe("주의가 필요한 지출");
    expect(confidenceText(0.81)).toBe("어느 정도 확실함");
  });

  it("keeps demo state across routes", () => {
    expect(withDemo("/ledger", true)).toBe("/ledger?demo=1");
    expect(withDemo("/ledger", false)).toBe("/ledger");
  });

  it("derives Korean month and today labels without fixed production dates", () => {
    const date = new Date("2026-08-05T12:00:00+09:00");
    expect(currentMonthKey(date)).toBe("2026-08");
    expect(formatMonthLabel("2026-08")).toBe("2026년 8월");
    expect(formatTodayLabel(date)).toBe("8월 5일 수요일");
  });

  it("creates a UUID when randomUUID is unavailable on a local origin", () => {
    const localCrypto = {
      getRandomValues(array: Uint8Array) {
        array.forEach((_, index) => { array[index] = index; });
        return array;
      },
    } as unknown as Crypto;

    expect(createClientId(localCrypto)).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  });
});
