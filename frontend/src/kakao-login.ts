import type { Session, SupabaseClient } from "@supabase/supabase-js";
import { apiUrl } from "./api";

const PENDING_KEY = "jangbu:kakao-login";
const MAX_PENDING_AGE_MS = 10 * 60 * 1000;

interface PendingLogin {
  state: string;
  nonce: string;
  codeVerifier: string;
  createdAt: number;
}

function randomHex(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function sha256(value: string): Promise<string> {
  const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function pkceChallenge(verifier: string): Promise<string> {
  const bytes = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier)));
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function post<T>(path: string, body: Record<string, string>): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) throw new Error("kakao_request_failed");
  const payload = await response.json() as { data?: T };
  if (!payload.data) throw new Error("kakao_response_invalid");
  return payload.data;
}

export function isKakaoCallback(): boolean {
  return window.location.pathname === "/auth/kakao";
}

export async function startKakaoLogin(): Promise<void> {
  const pending: PendingLogin = {
    state: randomHex(),
    nonce: randomHex(),
    codeVerifier: randomHex(),
    createdAt: Date.now(),
  };
  const { authorization_url } = await post<{ authorization_url: string }>(
    "/api/v1/auth/kakao/start",
    {
      state: pending.state,
      nonce_hash: await sha256(pending.nonce),
      code_challenge: await pkceChallenge(pending.codeVerifier),
    },
  );
  const destination = new URL(authorization_url);
  if (destination.origin !== "https://kauth.kakao.com" || destination.pathname !== "/oauth/authorize") {
    throw new Error("kakao_authorization_url_invalid");
  }
  sessionStorage.setItem(PENDING_KEY, JSON.stringify(pending));
  window.location.assign(destination.href);
}

export async function finishKakaoLogin(supabase: SupabaseClient): Promise<Session> {
  const query = new URLSearchParams(window.location.search);
  const saved = sessionStorage.getItem(PENDING_KEY);
  sessionStorage.removeItem(PENDING_KEY);
  window.history.replaceState(null, "", "/");
  let pending: PendingLogin | null = null;
  try {
    pending = saved ? JSON.parse(saved) as PendingLogin : null;
  } catch {
    // Treat a damaged login attempt as invalid.
  }
  if (!pending || !pending.state || !pending.nonce || !pending.codeVerifier
    || !Number.isFinite(pending.createdAt)
    || Date.now() - pending.createdAt > MAX_PENDING_AGE_MS
    || Date.now() < pending.createdAt
    || query.get("state") !== pending.state) {
    throw new Error("kakao_state_invalid");
  }
  if (query.has("error")) throw new Error("kakao_authorization_denied");
  const code = query.get("code");
  if (!code) throw new Error("kakao_code_missing");
  const { id_token } = await post<{ id_token: string }>("/api/v1/auth/kakao/exchange", {
    code,
    code_verifier: pending.codeVerifier,
  });
  const { data, error } = await supabase.auth.signInWithIdToken({
    provider: "kakao",
    token: id_token,
    nonce: pending.nonce,
  });
  if (error || !data.session) throw error ?? new Error("kakao_session_missing");
  return data.session;
}
