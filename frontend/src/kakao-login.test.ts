import type { SupabaseClient } from "@supabase/supabase-js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { finishKakaoLogin, startKakaoLogin } from "./kakao-login";

const pendingKey = "jangbu:kakao-login";

describe("Kakao callback", () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  afterEach(() => {
    vi.useRealTimers();
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
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ data: { id_token: "kakao-id-token" } }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));
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

  it("releases a stalled login start without saving an unusable pending attempt", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("crypto", {
      getRandomValues: (value: Uint8Array) => value.fill(7),
      subtle: { digest: vi.fn().mockResolvedValue(new Uint8Array(32).buffer) },
    });
    let requestSignal: AbortSignal | null | undefined;
    vi.stubGlobal("fetch", vi.fn((_input, init: RequestInit) => {
      requestSignal = init.signal;
      return new Promise(() => undefined);
    }));
    const pending = startKakaoLogin();
    const failure = expect(pending).rejects.toThrow("Authentication timed out.");
    await vi.advanceTimersByTimeAsync(90_000);
    await failure;
    expect(requestSignal?.aborted).toBe(true);
    expect(sessionStorage.getItem(pendingKey)).toBeNull();
  });

  it("aborts a stalled token exchange instead of leaving the callback pending forever", async () => {
    vi.useFakeTimers();
    sessionStorage.setItem(pendingKey, JSON.stringify({
      state: "expected-state", nonce: "raw-nonce", codeVerifier: "v".repeat(64), createdAt: Date.now(),
    }));
    window.history.pushState(null, "", "/auth/kakao?state=expected-state&code=one-time-code");
    let requestSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn((_url, options: RequestInit) => {
      requestSignal = options.signal ?? undefined;
      return new Promise(() => undefined);
    }));
    const signInWithIdToken = vi.fn();
    let outcome = "pending";
    void finishKakaoLogin({ auth: { signInWithIdToken } } as unknown as SupabaseClient)
      .catch(() => { outcome = "rejected"; });

    await vi.advanceTimersByTimeAsync(90_000);

    expect(requestSignal?.aborted).toBe(true);
    expect(outcome).toBe("rejected");
    expect(signInWithIdToken).not.toHaveBeenCalled();
  });

  it("ends a token response whose body never arrives without creating a late session", async () => {
    vi.useFakeTimers();
    sessionStorage.setItem(pendingKey, JSON.stringify({
      state: "expected-state", nonce: "raw-nonce", codeVerifier: "v".repeat(64), createdAt: Date.now(),
    }));
    window.history.pushState(null, "", "/auth/kakao?state=expected-state&code=one-time-code");
    let resolveBody!: (body: string) => void;
    const body = new Promise<string>((resolve) => { resolveBody = resolve; });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true, status: 200, statusText: "OK", headers: new Headers(),
      text: () => body, json: async () => JSON.parse(await body),
    }));
    const signInWithIdToken = vi.fn();
    let outcome = "pending";
    void finishKakaoLogin({ auth: { signInWithIdToken } } as unknown as SupabaseClient)
      .catch(() => { outcome = "rejected"; });

    await vi.advanceTimersByTimeAsync(90_000);
    expect(outcome).toBe("rejected");
    resolveBody(JSON.stringify({ data: { id_token: "late-token" } }));
    await vi.advanceTimersByTimeAsync(0);
    expect(signInWithIdToken).not.toHaveBeenCalled();
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
