import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import AuthLayout from "../components/AuthLayout";
import PasswordInput from "../components/PasswordInput";

export default function ResetPassword() {
  // Read the token once, then drop it from the address bar so it isn't kept in history
  const [token] = useState(() => new URLSearchParams(window.location.search).get("token") ?? "");
  useEffect(() => { window.history.replaceState(null, "", window.location.pathname); }, []);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    if (password !== confirm) return setError("Passwords do not match.");
    try { setMessage((await api.reset(token, password)).message); }
    catch (err) { setError((err as Error).message); }
  }

  return (
    <AuthLayout title="Choose a new password">
      {message ? <div className="alert ok" role="status">{message}</div> : (
        <form onSubmit={submit}>
          <PasswordInput id="password" label="New password" value={password} onChange={setPassword} autoComplete="new-password" />
          <PasswordInput id="confirm" label="Confirm new password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
          {error && <div className="alert error" role="alert">{error}</div>}
          <button className="primary" disabled={!token}>Update password</button>
        </form>
      )}
      <p className="muted center"><Link to="/login">Go to sign in</Link></p>
    </AuthLayout>
  );
}
