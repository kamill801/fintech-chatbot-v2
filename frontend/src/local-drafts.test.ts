import { beforeEach, describe, expect, it } from "vitest";
import {
  clearFinancialDrafts,
  manualDraftKey,
  onboardingDraftKey,
} from "./local-drafts";

describe("financial draft isolation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("does not expose the raw authenticated user id in storage keys", () => {
    expect(manualDraftKey("supabase-user-123")).not.toContain("supabase-user-123");
    expect(onboardingDraftKey("supabase-user-123")).not.toContain("supabase-user-123");
  });

  it("clears current and legacy drafts without deleting another user's draft", () => {
    const current = manualDraftKey("user-a");
    const other = manualDraftKey("user-b");
    window.localStorage.setItem(current, "current");
    window.localStorage.setItem(other, "other");
    window.localStorage.setItem("jangbu-manual-draft:user-user-a", "legacy-user");
    window.localStorage.setItem("jangbu-manual-draft", "legacy-global");
    window.sessionStorage.setItem("jangbu-onboarding-draft", "legacy-onboarding");

    clearFinancialDrafts("user-a");

    expect(window.localStorage.getItem(current)).toBeNull();
    expect(window.localStorage.getItem("jangbu-manual-draft:user-user-a")).toBeNull();
    expect(window.localStorage.getItem("jangbu-manual-draft")).toBeNull();
    expect(window.sessionStorage.getItem("jangbu-onboarding-draft")).toBeNull();
    expect(window.localStorage.getItem(other)).toBe("other");
  });
});
