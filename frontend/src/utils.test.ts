import { describe, expect, it } from "vitest";
import { confidenceText, formatCompactWon, formatWon, labelText, withDemo } from "./utils";

describe("Korean ledger formatting", () => {
  it("formats won without decimals", () => {
    expect(formatWon(623000)).toBe("623,000원");
    expect(formatCompactWon(10000000)).toBe("1,000만원");
  });

  it("uses plain-language judgment labels", () => {
    expect(labelText("caution")).toBe("주의가 필요한 지출");
    expect(confidenceText(0.81)).toBe("어느 정도 확실함");
  });

  it("keeps demo state across routes", () => {
    expect(withDemo("/ledger", true)).toBe("/ledger?demo=1");
    expect(withDemo("/ledger", false)).toBe("/ledger");
  });
});
