import type { AdComparison, ComparedAd } from "../../api/client";
import { fmtCompact, fmtDuration, fmtNum, fmtPct } from "../../lib/format";

export default function BestVsWorst({ data }: { data: AdComparison }) {
  const a = data.analysis;
  return (
    <section className="card compare">
      <div className="card-head">
        <h2>Best ad vs worst ad</h2>
        <span className="muted small">
          {a.analysed_by === "laya" ? "Text, numbers and comments (Laya)" : "Text and numbers"} ·{" "}
          {fmtNum(data.ads_judged)} ads ranked
          {data.ads_too_new > 0 && `, ${fmtNum(data.ads_too_new)} too new to judge`}
        </span>
      </div>
      {a.notice && <div className="alert error" role="status">{a.notice}</div>}
      <p className="compare-headline">{a.headline}</p>

      <div className="compare-pair">
        <AdCard label="Best" icon="↑" ad={data.best} points={a.best_strengths} />
        <AdCard label="Worst" icon="↓" ad={data.worst} points={a.worst_weaknesses} />
      </div>

      {a.differences.length > 0 && (
        <div className="table-wrap">
          <table className="runs compare-table">
            <thead><tr><th>What differs</th><th>Best ad</th><th>Worst ad</th><th>Why it matters</th></tr></thead>
            <tbody>
              {a.differences.map((d) => (
                <tr key={d.aspect}>
                  <td><strong>{d.aspect}</strong></td><td>{d.best}</td><td>{d.worst}</td>
                  <td className="muted">{d.why_it_matters}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {a.recommendations.length > 0 && (
        <>
          <h3>Do this in your next ad</h3>
          <ol className="compare-tips">{a.recommendations.map((r) => <li key={r}>{r}</li>)}</ol>
        </>
      )}
      <p className="muted small">
        {a.caveat} Ranked on views per day and engagement within this search; public numbers show
        what viewers responded to, not ad spend or sales.
      </p>
    </section>
  );
}

function AdCard({ label, icon, ad, points }: { label: string; icon: string; ad: ComparedAd; points: string[] }) {
  const v = ad.video;
  const topComment = ad.top_comments[0];
  return (
    <article className={`compare-ad compare-${label.toLowerCase()}`}>
      <div className="compare-label">
        <span className={`badge reception-${label === "Best" ? "loved" : "disliked"}`}>
          <span className="badge-icon" aria-hidden="true">{icon}</span>{label} · {ad.score}/100
        </span>
      </div>
      {v.thumbnail_url && <img src={v.thumbnail_url} alt="" loading="lazy" />}
      <a href={v.url} target="_blank" rel="noreferrer" className="compare-title">{v.title}</a>
      <div className="muted small">{v.channel_title} · {fmtDuration(v.duration_seconds)}</div>
      <dl className="facts">
        <dt>Views per day</dt><dd>{fmtCompact(ad.views_per_day)}</dd>
        <dt>Total views</dt><dd>{fmtCompact(v.views)}</dd>
        <dt>Engagement</dt><dd>{fmtPct(v.engagement_rate)}</dd>
      </dl>
      {points.length > 0 && <ul className="compare-points">{points.map((p) => <li key={p}>{p}</li>)}</ul>}
      <p className="muted small compare-quote">
        {ad.comments_disabled ? "Comments are turned off."
          : topComment ? <>Top comment: “{topComment.text}” ({fmtNum(topComment.likes)} likes)</>
          : "No comments yet."}
      </p>
    </article>
  );
}
