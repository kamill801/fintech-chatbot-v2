import type { Session } from "@supabase/supabase-js";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { authConfigured, supabase } from "./auth-client";
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
  error: string | null;
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

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    let active = true;
    const callbackPending = isKakaoCallback();
    if (callbackPending) {
      void finishKakaoLogin(supabase).then((nextSession) => {
        if (!active) return;
        setSession(nextSession);
      }).catch(() => {
        if (!active) return;
        setError("카카오 로그인을 완료하지 못했어요. 다시 시도해 주세요.");
      }).finally(() => {
        if (active) setLoading(false);
      });
    } else {
      void supabase.auth.getSession().then(({ data, error: sessionError }) => {
        if (!active) return;
        setSession(data.session);
        setError(sessionError ? "로그인 상태를 확인하지 못했어요." : null);
        setLoading(false);
      });
    }
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return;
      setSession(nextSession);
      if (!callbackPending) setLoading(false);
    });
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
      loading,
      provider: typeof provider === "string" ? provider : null,
      session,
      signIn,
      signInWithKakao,
      signOut,
      signUp,
      userKey: session?.user?.id ?? null,
    };
  }, [error, loading, session, signIn, signInWithKakao, signOut, signUp]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
