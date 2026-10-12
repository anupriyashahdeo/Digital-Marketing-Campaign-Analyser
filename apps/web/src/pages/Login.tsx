import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AuthLayout from "../components/AuthLayout";
import PasswordInput from "../components/PasswordInput";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(""); setBusy(true);
    try { await login(email.trim(), password); nav(from, { replace: true }); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <AuthLayout title="Sign in" subtitle="Use your email address as your username.">
      <form onSubmit={submit} noValidate={false}>
        <div className="field">
          <label htmlFor="email">Email (username)</label>
          <input id="email" type="email" value={email} required autoComplete="username"
            placeholder="you@company.com" onChange={(e) => setEmail(e.target.value)} />
        </div>
        <PasswordInput id="password" value={password} onChange={setPassword} autoComplete="current-password" />
        <div className="row-end"><Link to="/forgot-password">Forgot password?</Link></div>
        {error && <div className="alert error" role="alert">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <p className="muted center">New here? <Link to="/signup">Create an account</Link></p>
    </AuthLayout>
  );
}
