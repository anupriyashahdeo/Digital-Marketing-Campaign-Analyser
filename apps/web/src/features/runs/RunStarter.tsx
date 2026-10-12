import { useState } from "react";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { useSSE } from "../../hooks/useSSE";

export default function RunStarter() {
  const { user, logout } = useAuth();
  const [category, setCategory] = useState("");
  const [runId, setRunId] = useState<number | null>(null);
  const events = useSSE<{ step: string }>(runId ? `/api/v1/runs/${runId}/events` : null);

  return (
    <div className="home">
      <header>
        <strong>Ad Campaign Analyser</strong>
        <span>{user?.email} · <button className="link" onClick={logout}>Sign out</button></span>
      </header>
      <h1>New analysis</h1>
      <input value={category} onChange={(e) => setCategory(e.target.value)}
        placeholder="Category or brands, e.g. running shoes" />
      <button className="primary" disabled={!category}
        onClick={async () => setRunId((await api.createRun(category, [category])).id)}>Analyse</button>
      <ol>{events.map((e, i) => <li key={i}>{e.step}</li>)}</ol>
    </div>
  );
}
