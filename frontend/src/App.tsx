import { Navigate, Route, Routes, useLocation } from "./router";
import { useLedger } from "./ledger-context";
import { OnboardingBaseline, OnboardingGoal, OnboardingSource, OnboardingTrust } from "./pages/Onboarding";
import { HomePage, ManualTransactionPage, ReasonPage } from "./pages/HomeFlow";
import { JudgmentPage, SharePage, TransactionDetailPage } from "./pages/JudgmentFlow";
import { AgentPage, LedgerPage, ReportPage, SettingsPage } from "./pages/MainPages";

function LoadingScreen() {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <span className="loading-mark" />
      장부를 펼치는 중
    </div>
  );
}

function AppRoutes() {
  const { loading, profile, demo } = useLedger();
  const location = useLocation();
  if (loading) return <LoadingScreen />;

  const onboarding = location.pathname.startsWith("/onboarding");
  if (!profile && !onboarding) {
    return <Navigate replace to={demo ? "/onboarding/trust?demo=1" : "/onboarding/trust"} />;
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
      <Route path="/agent" element={<AgentPage />} />
      <Route path="/report" element={<ReportPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="/share/:transactionId" element={<SharePage />} />
      <Route path="*" element={<Navigate replace to={demo ? "/?demo=1" : "/"} />} />
    </Routes>
  );
}

export default function App() {
  return <AppRoutes />;
}
