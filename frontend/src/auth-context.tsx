import type { Session } from "@supabase/supabase-js";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { authConfigured, supabase } from "./auth-client";
import { awaitAuthResult } from "./auth-request";
import { finishKakaoLogin, isKakaoCallback, startKakaoLogin } from "./kakao-login";
import { clearFinancialDrafts } from "./local-drafts";

interface AuthContextValue {
  configured: boolean;
  loading: boolean;
  session: Session | null;
  userKey: string | null;
  displayName: string | null;
  avatarUrl: string | null;
  provider: string | null;
  introSeen: boolean;
  error: string | null;
  markIntroSeen(): Promise<void>;
  signIn(email: string, password: string): Promise<void>;
  signInWithKakao(): Promise<void>;
  signUp(email: string, password: string): Promise<boolean>;
  signOut(): Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function metadataValue(metadata: Record<string, unknown>, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(authConfigured);
  const [error, setError] = useState<string | null>(null);
  const callbackPending = useRef(isKakaoCallback());
  const callbackResult = useRef<Promise<Session> | null>(null);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    const auth = supabase.auth;
    let active = true;
    let authRevision = 0;
    const initialRevision = authRevision;
    const isInitialReadCurrent = () => active && authRevision === initialRevision;
    const { data } = auth.onAuthStateChange((event, nextSession) => {
      // Cached-session refreshes and SDK sign-in notifications cannot prove that
      // the current callback passed state, nonce and token exchange validation.
      if (!active || event === "INITIAL_SESSION" || callbackPending.current) return;
      // A confirmed SDK event supersedes every earlier restore/metadata snapshot.
      authRevision += 1;
      setSession(nextSession);
      setError(null);
      setLoading(false);
    });
    if (callbackPending.current) {
      // Each real callback request is bounded and aborted by authFetch, including
      // the Supabase token response body. Do not race the session-writing SDK call.
      // Effect replay must reuse this operation: it consumes the pending state
      // and URL synchronously, before the provider response arrives.
      callbackResult.current ??= finishKakaoLogin(supabase);
      void callbackResult.current.then((nextSession) => {
        if (!active) return;
        callbackPending.current = false;
        setSession(nextSession);
        setError(null);
      }).catch(() => {
        if (!active) return;
        callbackPending.current = false;
        setSession(null);
        setError("카카오 로그인을 완료하지 못했어요. 다시 시도해 주세요.");
      }).finally(() => {
        if (active) setLoading(false);
      });
    } else {
      void (async () => {
        try {
          const { data, error: sessionError } = await awaitAuthResult(auth.getSession(), 15_000);
          if (!isInitialReadCurrent()) return;
          let nextSession = data.session;
          if (nextSession) {
            try {
              const { data: userData } = await awaitAuthResult(auth.getUser(), 8_000);
              if (userData.user?.id === nextSession.user.id) {
                nextSession = { ...nextSession, user: userData.user };
              }
            } catch {
              // Preserve cached introduction metadata if its refresh is unavailable.
            }
          }
          if (!isInitialReadCurrent()) return;
          setSession(nextSession);
          setError(sessionError ? "로그인 상태를 확인하지 못했어요. 다시 로그인해 주세요." : null);
        } catch (restoreError) {
          if (!isInitialReadCurrent()) return;
          setError(restoreError instanceof DOMException && restoreError.name === "TimeoutError"
            ? "로그인 상태를 확인하는 데 시간이 오래 걸려요. 카카오 또는 이메일로 다시 로그인해 주세요."
            : "로그인 상태를 확인하지 못했어요. 다시 로그인해 주세요.");
        } finally {
          if (isInitialReadCurrent()) setLoading(false);
        }
      })();
    }
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error("auth_not_configured");
    setError(null);
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (signInError) {
      setError("이메일 또는 비밀번호를 확인해 주세요.");
      throw signInError;
    }
  }, []);

  const signInWithKakao = useCallback(async () => {
    if (!supabase) throw new Error("auth_not_configured");
    setError(null);
    try {
      await startKakaoLogin();
    } catch (oauthError) {
      setError("카카오 로그인을 시작하지 못했어요. 잠시 후 다시 시도해 주세요.");
      throw oauthError;
    }
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error("auth_not_configured");
    setError(null);
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
    });
    if (signUpError) {
      setError("회원가입하지 못했어요. 입력한 정보를 확인해 주세요.");
      throw signUpError;
    }
    return data.session !== null;
  }, []);

  const signOut = useCallback(async () => {
    if (!supabase) return;
    setError(null);
    const currentUserKey = session?.user?.id ?? session?.user?.email ?? null;
    try {
      const { error: signOutError } = await supabase.auth.signOut();
      if (signOutError) {
        setError("로그아웃하지 못했어요. 잠시 후 다시 시도해 주세요.");
        throw signOutError;
      }
      clearFinancialDrafts(currentUserKey);
    } catch (signOutError) {
      setError("로그아웃하지 못했어요. 잠시 후 다시 시도해 주세요.");
      throw signOutError;
    }
  }, [session]);

  const markIntroSeen = useCallback(async () => {
    if (!supabase || !session) throw new Error("auth_not_configured");
    const { data, error: updateError } = await supabase.auth.updateUser({
      data: { jangbu_intro_seen: true },
    });
    if (updateError || !data.user) throw updateError ?? new Error("intro_update_failed");
    setSession((current) => current?.user.id === data.user.id
      ? { ...current, user: data.user }
      : current);
  }, [session]);

  const value = useMemo<AuthContextValue>(() => {
    const metadata = (session?.user?.user_metadata ?? {}) as Record<string, unknown>;
    const provider = session?.user?.app_metadata?.provider;
    return {
      avatarUrl: metadataValue(metadata, "avatar_url", "picture", "profile_image_url"),
      configured: authConfigured,
      displayName: metadataValue(metadata, "name", "full_name", "preferred_username")
        ?? session?.user?.email?.split("@")[0]
        ?? null,
      error,
      introSeen: metadata.jangbu_intro_seen === true,
      loading,
      markIntroSeen,
      provider: typeof provider === "string" ? provider : null,
      session,
      signIn,
      signInWithKakao,
      signOut,
      signUp,
      userKey: session?.user?.id ?? null,
    };
  }, [error, loading, markIntroSeen, session, signIn, signInWithKakao, signOut, signUp]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
