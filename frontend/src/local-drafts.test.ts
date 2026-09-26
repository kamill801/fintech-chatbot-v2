import { beforeEach, describe, expect, it } from "vitest";
import {
  clearFinancialDrafts,
  manualDraftKey,
  onboardingDraftKey,
  onboardingResumePath,
  onboardingStageKey,
  planDraftKey,
} from "./local-drafts";

describe("financial draft isolation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("does not expose the raw authenticated user id in storage keys", () => {
    expect(manualDraftKey("supabase-user-123")).not.toContain("supabase-user-123");
    expect(onboardingDraftKey("supabase-user-123")).not.toContain("supabase-user-123");
    expect(planDraftKey("supabase-user-123")).not.toContain("supabase-user-123");
  });

  it("clears current and legacy drafts without deleting another user's draft", () => {
    const current = manualDraftKey("user-a");
    const other = manualDraftKey("user-b");
    const currentPlan = planDraftKey("user-a");
    const otherPlan = planDraftKey("user-b");
    window.localStorage.setItem(current, "current");
    window.localStorage.setItem(other, "other");
    window.sessionStorage.setItem(currentPlan, "plan-current");
    window.sessionStorage.setItem(otherPlan, "plan-other");
    window.localStorage.setItem("jangbu-manual-draft:user-user-a", "legacy-user");
    window.localStorage.setItem("jangbu-manual-draft", "legacy-global");
    window.sessionStorage.setItem("jangbu-onboarding-draft", "legacy-onboarding");
    window.sessionStorage.setItem("jangbu-plan-draft", "legacy-plan");

    clearFinancialDrafts("user-a");

    expect(window.localStorage.getItem(current)).toBeNull();
    expect(window.localStorage.getItem("jangbu-manual-draft:user-user-a")).toBeNull();
    expect(window.localStorage.getItem("jangbu-manual-draft")).toBeNull();
    expect(window.sessionStorage.getItem("jangbu-onboarding-draft")).toBeNull();
    expect(window.sessionStorage.getItem("jangbu-plan-draft")).toBeNull();
    expect(window.sessionStorage.getItem(currentPlan)).toBeNull();
    expect(window.localStorage.getItem(other)).toBe("other");
    expect(window.sessionStorage.getItem(otherPlan)).toBe("plan-other");
  });

  it("resumes a setup step only when that account still has its draft", () => {
    window.sessionStorage.setItem(onboardingDraftKey("user-a"), "{\"budget\":1}");
    window.sessionStorage.setItem(onboardingStageKey("user-a"), "goal");

    expect(onboardingResumePath("user-a")).toBe("/onboarding/goal");
    expect(onboardingResumePath("user-b")).toBe("/onboarding/baseline");

    clearFinancialDrafts("user-a");
    expect(onboardingResumePath("user-a")).toBe("/onboarding/baseline");
  });
});
