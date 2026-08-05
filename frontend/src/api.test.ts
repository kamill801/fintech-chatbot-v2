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
});
