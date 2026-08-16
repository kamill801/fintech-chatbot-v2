import { describe, expect, it } from "vitest";
import { demoBudgetUsage, demoJudgment, demoSignals, demoSummary, demoTransactions } from "./demo";

describe("demo fixture consistency", () => {
  it("keeps judgment evidence aligned with the monthly summary and recurrence history", () => {
    const cafeTransactions = demoTransactions.filter((transaction) => transaction.category === "cafe");
    expect(demoSignals.budget_usage_after).toBe(demoBudgetUsage);
    expect(demoSummary.budget_usage).toBe(demoBudgetUsage);
    expect(cafeTransactions).toHaveLength(demoSignals.recurrence_30d);
    expect(demoJudgment(false).rationale).toContain("생활비 예산 47%");
    expect(demoJudgment(false).rationale).toContain("세 번째");
  });
});
