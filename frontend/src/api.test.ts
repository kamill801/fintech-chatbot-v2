import { beforeEach, describe, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({ getAccessToken: vi.fn() }));
vi.mock("./auth-client", () => auth);

import { ledgerApi } from "./api";

describe("production API client", () => {
  beforeEach(() => {
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

  it("rejects an empty successful API response instead of throwing a JSON parse error", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response("", { status: 200 }));

    await expect(ledgerApi.profile()).rejects.toMatchObject({
      code: "invalid_response",
      message: "서버 응답을 읽지 못했어요.",
      status: 200,
    });
  });
});
