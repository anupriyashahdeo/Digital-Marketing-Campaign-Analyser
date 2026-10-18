import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type Run } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import { usePoll } from "../hooks/usePoll";
import { fmtDate, fmtNum, fmtUsd } from "../lib/format";
import { useWorkspace } from "../workspace/WorkspaceContext";

// The six pipeline steps from the architecture doc. Per-step progress arrives in Step 3+.
const STEPS = [
  ["Collect", "Find ads for these brands on YouTube"],
  ["Turn into text", "Transcripts, on-screen text, landing pages"],
  ["Ask questions", "Hook, format, offer, call to action"],
  ["Double-check", "Re-check low-confidence answers"],
  ["Score", "Label Winner, Watch or Dog"],
  ["Summarise", "Roll up by brand and pattern"],
] as const;

export default function RunDetail() {
  const { runId } = useParams();
  const { workspace } = useWorkspace();
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const id = Number(runId);
  const active = run?.status === "queued" || run?.status === "running";
  const canEdit = workspace?.role !== "viewer";

  const load = useCallback(() => {
    if (!Number.isInteger(id) || id < 1) return setError("Analysis not found");
    api.run(workspace!.id, id).then((r) => { setRun(r); setError(""); })
      .catch((e) => setError(e instanceof ApiError && e.status === 404 ? "Analysis not found" : (e as Error).message));
  }, [workspace, id]);

  useEffect(load, [load]);
  usePoll(load, 5_000, active);

  async function cancel() {
    if (!confirm("Cancel this analysis? Work done so far will be kept.")) return;
    setBusy(true);
    try { setRun(await api.cancelRun(workspace!.id, id)); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (error && !run) return <><p><Link to="/">← Dashboard</Link></p><div className="alert error" role="alert">{error}</div></>;
  if (!run) return <p className="muted">Loading…</p>;

  return (
    <>
      <p><Link to="/">← Dashboard</Link></p>
      <div className="page-head">
        <div>
          <h1>{run.category}</h1>
          <StatusBadge status={run.status} />
        </div>
        {active && canEdit && <button className="secondary" disabled={busy} onClick={cancel}>Cancel analysis</button>}
      </div>
      {error && <div className="alert error" role="alert">{error}</div>}
      {run.status === "failed" && run.error && <div className="alert error" role="alert">{run.error}</div>}

      <div className="detail-grid">
        <section className="card">
          <h2>Details</h2>
          <dl className="facts">
            <dt>Brands / keywords</dt><dd>{run.keywords.join(", ")}</dd>
            <dt>Region</dt><dd>{run.region}</dd>
            <dt>Language</dt><dd>{run.language === "hi" ? "Hindi" : "English"}</dd>
            <dt>Started</dt><dd>{fmtDate(run.created_at)}</dd>
            <dt>Finished</dt><dd>{run.finished_at ? fmtDate(run.finished_at) : "—"}</dd>
            <dt>Ads found</dt><dd>{fmtNum(run.ad_count)}</dd>
            <dt>Cost so far</dt><dd>{fmtUsd(run.spent_usd)}</dd>
          </dl>
        </section>

        <section className="card">
          <h2>Progress</h2>
          <ol className="steps">
            {STEPS.map(([name, desc]) => (
              <li key={name} className={run.status === "completed" ? "done" : ""}>
                <strong>{name}</strong><span className="muted">{desc}</span>
              </li>
            ))}
          </ol>
          {run.status === "queued" && (
            <p className="muted small">Waiting in the queue. This page refreshes on its own.</p>
          )}
        </section>
      </div>
    </>
  );
}
