import type { SupabaseClient } from "@supabase/supabase-js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { finishKakaoLogin } from "./kakao-login";

const pendingKey = "jangbu:kakao-login";

describe("Kakao callback", () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.history.replaceState(null, "", "/");
  });

  it("exchanges a validated code and nonce for a Supabase session", async () => {
    sessionStorage.setItem(pendingKey, JSON.stringify({
      state: "expected-state",
      nonce: "raw-nonce",
      codeVerifier: "v".repeat(64),
      createdAt: Date.now(),
    }));
    window.history.pushState(null, "", "/auth/kakao?state=expected-state&code=one-time-code");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: { id_token: "kakao-id-token" } }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const signInWithIdToken = vi.fn().mockResolvedValue({
      data: { session: { access_token: "supabase-token" } },
      error: null,
    });
    const supabase = { auth: { signInWithIdToken } } as unknown as SupabaseClient;

    const session = await finishKakaoLogin(supabase);

    expect(session.access_token).toBe("supabase-token");
    expect(signInWithIdToken).toHaveBeenCalledWith({
      provider: "kakao",
      token: "kakao-id-token",
      nonce: "raw-nonce",
    });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string)).toEqual({
      code: "one-time-code",
      code_verifier: "v".repeat(64),
    });
    expect(sessionStorage.getItem(pendingKey)).toBeNull();
    expect(window.location.search).toBe("");
  });

  it("does not exchange a code when the state does not match", async () => {
    sessionStorage.setItem(pendingKey, JSON.stringify({
      state: "expected-state",
      nonce: "raw-nonce",
      codeVerifier: "v".repeat(64),
      createdAt: Date.now(),
    }));
    window.history.pushState(null, "", "/auth/kakao?state=other-state&code=one-time-code");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const supabase = { auth: { signInWithIdToken: vi.fn() } } as unknown as SupabaseClient;

    await expect(finishKakaoLogin(supabase)).rejects.toThrow("kakao_state_invalid");

    expect(fetchMock).not.toHaveBeenCalled();
    expect(supabase.auth.signInWithIdToken).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(pendingKey)).toBeNull();
    expect(window.location.search).toBe("");
  });
});
