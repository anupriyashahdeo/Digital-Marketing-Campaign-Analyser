import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type RunPage } from "../api/client";
import RunsTable from "../components/RunsTable";
import { useWorkspace } from "../workspace/WorkspaceContext";

const PAGE = 20;

export default function Runs() {
  const { workspace } = useWorkspace();
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<RunPage | null>(null);
  const [error, setError] = useState("");
  const canEdit = workspace?.role !== "viewer";

  useEffect(() => {
    api.runs(workspace!.id, PAGE, offset).then(setPage).catch((e) => setError((e as Error).message));
  }, [workspace, offset]);

  return (
    <>
      <div className="page-head">
        <h1>Analyses</h1>
        {canEdit && <Link className="button primary inline" to="/runs/new">New analysis</Link>}
      </div>
      {error && <div className="alert error" role="alert">{error}</div>}
      <section className="card">
        {page ? <RunsTable runs={page.items} /> : <p className="muted">Loading…</p>}
        {page && page.total > PAGE && (
          <div className="pager">
            <button className="secondary" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
            <span className="muted">{offset + 1}–{Math.min(offset + PAGE, page.total)} of {page.total}</span>
            <button className="secondary" disabled={offset + PAGE >= page.total}
              onClick={() => setOffset(offset + PAGE)}>Next</button>
          </div>
        )}
      </section>
    </>
  );
}
