import { Navigate, Route, Routes, useLocation } from "./router";
import { useLedger } from "./ledger-context";
import { OnboardingBaseline, OnboardingGoal, OnboardingSource, OnboardingTrust } from "./pages/Onboarding";
import { HomePage, ManualTransactionPage, ReasonPage } from "./pages/HomeFlow";
import { JudgmentPage, SharePage, TransactionDetailPage } from "./pages/JudgmentFlow";
import { LedgerPage, ReportPage, SettingsPage } from "./pages/MainPages";
import { AuthProvider, useAuth } from "./auth-context";
import { LedgerProvider } from "./ledger-context";
import { LoginPage } from "./pages/LoginPage";
import { PlanPage } from "./pages/PlanPage";
import { onboardingResumePath } from "./local-drafts";

function LoadingScreen() {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <span className="loading-mark" />
      장부를 펼치는 중
    </div>
  );
}

function ProfileErrorScreen({ message, onRetry }: { message: string; onRetry(): void }) {
  return (
    <main className="standalone-screen">
      <section className="surface error-state">
        <h1>장부를 불러오지 못했어요</h1>
        <p>{message}</p>
        <button className="primary-button" type="button" onClick={onRetry}>다시 시도</button>
      </section>
    </main>
  );
}

function AppRoutes() {
  const { loading, profile, profileLoadError, refresh, demo } = useLedger();
  const { introSeen, userKey } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingScreen />;
  if (profileLoadError && !profile) {
    return <ProfileErrorScreen message={profileLoadError} onRetry={() => void refresh()} />;
  }

  const onboarding = location.pathname.startsWith("/onboarding");
  if (profile && onboarding) return <Navigate replace to={demo ? "/?demo=1" : "/"} />;
  if (!profile) {
    const resume = onboardingResumePath(userKey, demo);
    const destination = !demo && !introSeen ? "/onboarding/trust" : resume;
    if (!onboarding || (location.pathname === "/onboarding/trust" && destination !== location.pathname)) {
      return <Navigate replace to={demo ? `${destination}?demo=1` : destination} />;
    }
    if (location.pathname !== "/onboarding/trust" && !demo && !introSeen) {
      return <Navigate replace to="/onboarding/trust" />;
    }
    if ((location.pathname === "/onboarding/goal" || location.pathname === "/onboarding/source")
      && resume === "/onboarding/baseline") {
      return <Navigate replace to={demo ? "/onboarding/baseline?demo=1" : "/onboarding/baseline"} />;
    }
  }

  return (
    <Routes>
      <Route path="/onboarding/trust" element={<OnboardingTrust />} />
      <Route path="/onboarding/baseline" element={<OnboardingBaseline />} />
      <Route path="/onboarding/goal" element={<OnboardingGoal />} />
      <Route path="/onboarding/source" element={<OnboardingSource />} />
      <Route path="/" element={<HomePage />} />
      <Route path="/add" element={<ManualTransactionPage />} />
      <Route path="/transactions/:transactionId/reason" element={<ReasonPage />} />
      <Route path="/judgments/:transactionId" element={<JudgmentPage />} />
      <Route path="/ledger" element={<LedgerPage />} />
      <Route path="/transactions/:transactionId" element={<TransactionDetailPage />} />
      <Route path="/agent" element={<Navigate replace to={demo ? "/plan?demo=1" : "/plan"} />} />
      <Route path="/plan" element={<PlanPage />} />
      <Route path="/report" element={<ReportPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/share/:transactionId" element={<SharePage />} />
      <Route path="*" element={<Navigate replace to={demo ? "/?demo=1" : "/"} />} />
    </Routes>
  );
}

function SessionGate() {
  const { loading, session } = useAuth();
  const query = new URLSearchParams(window.location.search);
  const demo = query.get("demo") === "1" || import.meta.env.VITE_DEMO_DEFAULT === "1";
  if (demo) return <LedgerProvider><AppRoutes /></LedgerProvider>;
  if (loading) return <LoadingScreen />;
  if (!session) return <LoginPage />;
  return <LedgerProvider><AppRoutes /></LedgerProvider>;
}

export default function App() {
  return <AuthProvider><SessionGate /></AuthProvider>;
}
