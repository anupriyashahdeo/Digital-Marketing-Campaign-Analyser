import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import AuthLayout from "../components/AuthLayout";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(""); setBusy(true);
    try { setMessage((await api.forgot(email.trim())).message); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <AuthLayout title="Forgot your password?" subtitle="Enter your email and we'll send you a reset link.">
      {message ? <div className="alert ok" role="status">{message}</div> : (
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" value={email} required autoComplete="username"
              onChange={(e) => setEmail(e.target.value)} />
          </div>
          {error && <div className="alert error" role="alert">{error}</div>}
          <button className="primary" disabled={busy}>{busy ? "Sending…" : "Send reset link"}</button>
        </form>
      )}
      <p className="muted center"><Link to="/login">Back to sign in</Link></p>
    </AuthLayout>
  );
}
