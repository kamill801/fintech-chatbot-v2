import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ getAccessToken: vi.fn() }));
vi.mock("./auth-client", () => auth);

import { ledgerApi } from "./api";

describe("production API client", () => {
  beforeEach(() => {
    vi.useRealTimers();
    auth.getAccessToken.mockReset();
    auth.getAccessToken.mockResolvedValue("verified-session-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ data: { profile: null }, meta: { correlation_id: "test" } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("sends the Supabase bearer token without a development identity header", async () => {
    await ledgerApi.profile();
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer verified-session-token");
    expect(headers.has("X-User-Id")).toBe(false);
  });

  it("fails before the network when no authenticated session exists", async () => {
    auth.getAccessToken.mockResolvedValue(null);
    await expect(ledgerApi.profile()).rejects.toMatchObject({ code: "unauthorized", status: 401 });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("uses a supplied transaction idempotency key across retries", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          data: {
            transaction: {
              transaction_id: "tx-1",
              amount_krw: 12000,
              category: "cafe",
              merchant: "카페",
              description: null,
              occurred_at: "2026-08-14T03:00:00Z",
              source: "manual",
              source_reference: null,
              reason: null,
              status: "awaiting_reason",
              created_at: "2026-08-14T03:00:00Z",
            },
          },
          meta: { correlation_id: "test" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    await ledgerApi.createTransaction({ amount_krw: 12000, category: "cafe" }, "manual-op-1");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(new Headers(init?.headers).get("Idempotency-Key")).toBe("manual-op-1");
  });

  it("aborts a request that never returns instead of leaving the UI busy forever", async () => {
    vi.useFakeTimers();
    vi.mocked(fetch).mockImplementationOnce((_url, init) => {
      const signal = init?.signal as AbortSignal;
      return new Promise<Response>((_resolve, reject) => {
        signal.addEventListener("abort", () => reject(signal.reason), { once: true });
      });
    });

    const request = ledgerApi.profile();
    let rejected = false;
    const failure = request.catch((error) => {
      rejected = true;
      return error;
    });

    await vi.advanceTimersByTimeAsync(89_999);
    await Promise.resolve();
    expect(rejected).toBe(false);

    await vi.advanceTimersByTimeAsync(1);
    await expect(failure).resolves.toMatchObject({
      code: "request_timeout",
      message: "요청 시간이 오래 걸려요. 잠시 후 다시 시도해 주세요.",
      status: 0,
    });
  });

  it("aborts a response body that never finishes loading", async () => {
    vi.useFakeTimers();
    const text = vi.fn(() => new Promise<string>(() => undefined));
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers(),
      text,
    } as unknown as Response);

    const request = ledgerApi.profile();
    const failure = request.catch((error) => error);

    await vi.advanceTimersByTimeAsync(90_000);

    await expect(failure).resolves.toMatchObject({
      code: "request_timeout",
      message: "요청 시간이 오래 걸려요. 잠시 후 다시 시도해 주세요.",
      status: 0,
    });
    expect(text).toHaveBeenCalledTimes(1);
  });

  it("cleans up the timeout after a successful response", async () => {
    vi.useFakeTimers();
    let capturedSignal: AbortSignal | undefined;
    vi.mocked(fetch).mockImplementationOnce((_url, init) => {
      capturedSignal = init?.signal as AbortSignal;
      return Promise.resolve(
        new Response(
          JSON.stringify({ data: { profile: null }, meta: { correlation_id: "test" } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    });

    await ledgerApi.profile();
    expect(capturedSignal).toBeDefined();
    const signal = capturedSignal as AbortSignal;
    expect(signal.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(90_000);
    expect(signal.aborted).toBe(false);
  });

  it("keeps ordinary network failures distinct from request timeouts", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(ledgerApi.profile()).rejects.toMatchObject({
      code: "offline",
      message: "네트워크에 연결할 수 없어요.",
      status: 0,
    });
  });

  it("records a completed share through the dedicated success endpoint", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

    await ledgerApi.shareSuccess("judgment-1");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/me/judgments/judgment-1/share-success");
    expect(init?.method).toBe("POST");
  });

  it("turns HTML gateway failures into a safe API error", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("<html>Bad gateway</html>", {
        status: 502,
        headers: { "Content-Type": "text/html" },
      }),
    );

    await expect(ledgerApi.profile()).rejects.toMatchObject({
      code: "request_failed",
      message: "요청을 처리하지 못했어요.",
      status: 502,
    });
  });

  it("keeps the correlation id from a failed response for support diagnostics", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(
      JSON.stringify({ error: { code: "invalid_account", message: "계좌를 확인해 주세요." }, meta: { correlation_id: "trace-42" } }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    ));

    await expect(ledgerApi.createTransaction({ amount_krw: 9600, category: "food" }, "op-42")).rejects.toMatchObject({
      code: "invalid_account",
      correlationId: "trace-42",
    });
  });

  it("rejects an empty successful API response instead of throwing a JSON parse error", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("", { status: 200 }));

    await expect(ledgerApi.profile()).rejects.toMatchObject({
      code: "invalid_response",
      message: "서버 응답을 읽지 못했어요.",
      status: 200,
    });
  });
});
