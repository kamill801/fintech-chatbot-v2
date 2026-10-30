import { createClient } from "@supabase/supabase-js";
import { afterEach, describe, expect, it, vi } from "vitest";
import { authFetch } from "./auth-request";

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("bounded authentication transport", () => {
  it("preserves a complete JSON response and its status", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{"message":"denied"}', {
      status: 401, statusText: "Unauthorized", headers: { "Content-Type": "application/json" },
    })));

    const response = await authFetch("https://auth.example.test/auth/v1/token");

    expect(response.status).toBe(401);
    expect(response.headers.get("Content-Type")).toBe("application/json");
    expect(await response.json()).toEqual({ message: "denied" });
  });

  it("cancels an external request before or during transport", async () => {
    const alreadyCancelled = new AbortController();
    alreadyCancelled.abort();
    const fetchMock = vi.fn(() => new Promise<Response>(() => undefined));
    vi.stubGlobal("fetch", fetchMock);
    await expect(authFetch("https://auth.example.test", { signal: alreadyCancelled.signal })).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();

    const controller = new AbortController();
    const pending = authFetch("https://auth.example.test", { signal: controller.signal });
    const failure = expect(pending).rejects.toThrow();
    const transportSignal = (fetchMock.mock.calls[0] as unknown as [unknown, RequestInit])[1].signal;
    controller.abort();
    await failure;
    expect(transportSignal?.aborted).toBe(true);
  });

  it("allows a slow cold start within the existing 90-second allowance", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => {
      setTimeout(() => resolve(new Response('{"ok":true}', { status: 200 })), 60_000);
    })));
    const pending = authFetch("https://auth.example.test/auth/v1/token");
    await vi.advanceTimersByTimeAsync(60_000);
    expect(await (await pending).json()).toEqual({ ok: true });
  });

  it("aborts the real SDK token transport before a late body can install a session", async () => {
    vi.useFakeTimers();
    // Only synthetic responses enter the installed SDK. No provider is called.
    let resolveBody!: (body: string) => void;
    const body = new Promise<string>((resolve) => { resolveBody = resolve; });
    let requestSignal: AbortSignal | null | undefined;
    vi.stubGlobal("fetch", vi.fn((_input, init: RequestInit) => {
      requestSignal = init.signal;
      return Promise.resolve({
        status: 200, statusText: "OK", headers: new Headers({ "Content-Type": "application/json" }), text: () => body,
      });
    }));
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const client = createClient("https://auth.example.test", "synthetic-public-key", {
      global: { fetch: authFetch },
      auth: { autoRefreshToken: false, persistSession: false, detectSessionInUrl: false },
    });
    const events: string[] = [];
    const subscription = client.auth.onAuthStateChange((event) => { events.push(event); }).data.subscription;
    const pending = client.auth.signInWithIdToken({ provider: "kakao", token: "synthetic-id-token", nonce: "synthetic-nonce" });

    await vi.advanceTimersByTimeAsync(90_000);
    const result = await pending;
    expect(requestSignal?.aborted).toBe(true);
    expect(result.error).not.toBeNull();
    expect(result.data.session).toBeNull();

    resolveBody(JSON.stringify({
      access_token: "synthetic-access-token", refresh_token: "synthetic-refresh-token", expires_in: 3600,
      token_type: "bearer", user: { id: "late-user" },
    }));
    await vi.advanceTimersByTimeAsync(0);
    expect(events).not.toContain("SIGNED_IN");
    expect((await client.auth.getSession()).data.session).toBeNull();
    subscription.unsubscribe();
  });
});
