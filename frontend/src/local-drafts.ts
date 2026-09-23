const ONBOARDING_PREFIX = "jangbu-onboarding-draft";
const ONBOARDING_STAGE_PREFIX = "jangbu-onboarding-stage";
const MANUAL_PREFIX = "jangbu-manual-draft";

function scopePart(userKey: string | null | undefined, demo = false): string {
  if (demo) return "demo";
  return userKey ? `user-${hashUserKey(userKey)}` : "anonymous";
}

function legacyScopePart(userKey: string): string {
  return `user-${userKey}`;
}

function hashUserKey(value: string): string {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(36);
}

export function onboardingDraftKey(userKey: string | null | undefined, demo = false): string {
  return `${ONBOARDING_PREFIX}:${scopePart(userKey, demo)}`;
}

export function onboardingStageKey(userKey: string | null | undefined, demo = false): string {
  return `${ONBOARDING_STAGE_PREFIX}:${scopePart(userKey, demo)}`;
}

export function onboardingResumePath(userKey: string | null | undefined, demo = false): string {
  try {
    const draft = window.sessionStorage.getItem(onboardingDraftKey(userKey, demo));
    const stage = window.sessionStorage.getItem(onboardingStageKey(userKey, demo));
    if (draft && (stage === "goal" || stage === "source")) return `/onboarding/${stage}`;
  } catch {
    // Browser storage is optional; the baseline screen is always a safe resume point.
  }
  return "/onboarding/baseline";
}

export function manualDraftKey(userKey: string | null | undefined, demo = false): string {
  return `${MANUAL_PREFIX}:${scopePart(userKey, demo)}`;
}

function removeMatching(storage: Storage, userKey?: string | null) {
  const scoped = userKey
    ? [scopePart(userKey), legacyScopePart(userKey), "anonymous"]
    : null;
  for (let index = storage.length - 1; index >= 0; index -= 1) {
    const key = storage.key(index);
    if (!key) continue;
    const financialDraft =
      key === ONBOARDING_PREFIX ||
      key === ONBOARDING_STAGE_PREFIX ||
      key === MANUAL_PREFIX ||
      key.startsWith(`${ONBOARDING_PREFIX}:`) ||
      key.startsWith(`${ONBOARDING_STAGE_PREFIX}:`) ||
      key.startsWith(`${MANUAL_PREFIX}:`);
    if (!financialDraft) continue;
    const legacyBareKey = key === ONBOARDING_PREFIX || key === ONBOARDING_STAGE_PREFIX || key === MANUAL_PREFIX;
    if (legacyBareKey || !scoped || scoped.some((scope) => key.endsWith(`:${scope}`))) {
      storage.removeItem(key);
    }
  }
}

export function clearFinancialDrafts(userKey?: string | null) {
  try {
    removeMatching(window.sessionStorage, userKey);
    removeMatching(window.localStorage, userKey);
  } catch {
    // Storage can be unavailable in private contexts; API state clearing still proceeds.
  }
}
