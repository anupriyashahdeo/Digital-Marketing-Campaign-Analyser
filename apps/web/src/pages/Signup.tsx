import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AuthLayout from "../components/AuthLayout";
import PasswordInput from "../components/PasswordInput";

export default function Signup() {
  const { signup } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    if (password !== confirm) return setError("Passwords do not match.");
    setBusy(true);
    try { await signup(email.trim(), password); nav("/", { replace: true }); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <AuthLayout title="Create your account" subtitle="Your email will be your username.">
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="email">Email (username)</label>
          <input id="email" type="email" value={email} required autoComplete="username"
            placeholder="you@company.com" onChange={(e) => setEmail(e.target.value)} />
        </div>
        <PasswordInput id="password" value={password} onChange={setPassword} autoComplete="new-password" />
        <PasswordInput id="confirm" label="Confirm password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
        <p className="hint">At least 8 characters.</p>
        {error && <div className="alert error" role="alert">{error}</div>}
        <button className="primary" disabled={busy}>{busy ? "Creating…" : "Sign up"}</button>
      </form>
      <p className="muted center">Already have an account? <Link to="/login">Sign in</Link></p>
    </AuthLayout>
  );
}
