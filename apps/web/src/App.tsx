import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import AppShell from "./components/AppShell";
import Dashboard from "./pages/Dashboard";
import ForgotPassword from "./pages/ForgotPassword";
import Login from "./pages/Login";
import NewRun from "./pages/NewRun";
import ResetPassword from "./pages/ResetPassword";
import RunDetail from "./pages/RunDetail";
import Runs from "./pages/Runs";
import Signup from "./pages/Signup";
import YouTube from "./pages/YouTube";
import { WorkspaceProvider } from "./workspace/WorkspaceContext";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <p className="center muted page-msg">Loading…</p>;
  // key: a different user gets a fresh workspace state, never the previous user's
  return user
    ? <WorkspaceProvider key={user.id}>{children}</WorkspaceProvider>
    : <Navigate to="/login" replace state={{ from: loc.pathname }} />;
}

function GuestOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/" replace /> : <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Signed-in area: everything here shares the top bar and workspace */}
      <Route element={<Protected><AppShell /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/runs" element={<Runs />} />
        <Route path="/runs/new" element={<NewRun />} />
        <Route path="/runs/:runId" element={<RunDetail />} />
        <Route path="/youtube" element={<YouTube />} />
      </Route>
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/signup" element={<GuestOnly><Signup /></GuestOnly>} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
