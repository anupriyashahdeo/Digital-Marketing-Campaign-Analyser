import { Link } from "react-router-dom";
import type { Run } from "../api/client";
import { fmtNum, timeAgo } from "../lib/format";
import StatusBadge from "./StatusBadge";

export default function RunsTable({ runs }: { runs: Run[] }) {
  if (!runs.length) return <p className="muted">No analyses yet.</p>;
  return (
    <div className="table-wrap">
      <table className="runs">
        <thead>
          <tr><th>Category</th><th>Brands / keywords</th><th>Status</th><th className="num">Ads</th><th>Started</th></tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id}>
              <td><Link to={`/runs/${r.id}`}>{r.category}</Link></td>
              <td className="muted kw">{r.keywords.join(", ")}</td>
              <td><StatusBadge status={r.status} /></td>
              <td className="num">{fmtNum(r.ad_count)}</td>
              <td className="muted nowrap">{timeAgo(r.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
