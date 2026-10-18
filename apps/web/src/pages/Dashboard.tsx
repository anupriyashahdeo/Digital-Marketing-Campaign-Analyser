import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Dashboard as Data } from "../api/client";
import RunsTable from "../components/RunsTable";
import Tile from "../components/Tile";
import NewRunForm from "../features/runs/NewRunForm";
import { usePoll } from "../hooks/usePoll";
import { fmtNum, fmtUsd } from "../lib/format";
import { useWorkspace } from "../workspace/WorkspaceContext";

export default function Dashboard() {
  const { workspace } = useWorkspace();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.dashboard(workspace!.id).then((d) => { setData(d); setError(""); })
      .catch((e) => setError((e as Error).message));
  }, [workspace]);

  useEffect(load, [load]);
  usePoll(load, 10_000, (data?.stats.active_runs ?? 0) > 0);

  if (error && !data) return <div className="alert error" role="alert">{error}</div>;
  if (!data) return <p className="muted">Loading dashboard…</p>;
  if (data.stats.total_runs === 0) return <Welcome canEdit={data.can_edit} />;

  const s = data.stats;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">{data.workspace.name}</p>
        </div>
        <div className="head-actions">
          <Link className="button secondary inline" to="/youtube">YouTube explorer</Link>
          {data.can_edit && <Link className="button primary inline" to="/runs/new">New analysis</Link>}
        </div>
      </div>

      <section className="tiles" aria-label="Summary">
        <Tile label="Analyses" value={fmtNum(s.total_runs)} note={`${fmtNum(s.completed_runs)} completed`} />
        <Tile label="In progress" value={fmtNum(s.active_runs)} note="Queued or running" />
        <Tile label="Ads analysed" value={fmtNum(s.ads_analysed)} note="Across all analyses" />
        <Tile label="Spend this month" value={fmtUsd(s.spent_this_month_usd)}
          note={`Cap ${fmtUsd(s.run_spend_cap_usd)} per analysis`} />
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Recent analyses</h2>
          <Link to="/runs">View all</Link>
        </div>
        <RunsTable runs={data.recent_runs} />
      </section>
    </>
  );
}

function Welcome({ canEdit }: { canEdit: boolean }) {
  return (
    <div className="welcome">
      <section className="card welcome-intro">
        <h1>Welcome to Ad Campaign Analyser</h1>
        <p className="muted">
          Tell us a category and the brands you compete with. We find their YouTube ads, ask the
          same questions about every ad, and show which hooks, formats and offers are working.
        </p>
        <ol className="checklist">
          <li className="done"><span aria-hidden="true">✓</span> Create your account</li>
          <li><span aria-hidden="true">2</span> Start your first analysis</li>
          <li><span aria-hidden="true">3</span> Review winners and gaps</li>
        </ol>
      </section>
      <section className="card">
        <h2>Start your first analysis</h2>
        {canEdit ? <NewRunForm /> : (
          <p className="muted">You have view-only access to this workspace. Ask an owner to start an analysis.</p>
        )}
      </section>
    </div>
  );
}
