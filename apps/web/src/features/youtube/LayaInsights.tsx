import { Fragment } from "react";
import type { AdInsight, Reception, YouTubeInsights } from "../../api/client";
import Tile from "../../components/Tile";
import { fmtCompact, fmtDuration, fmtNum, fmtPct } from "../../lib/format";

// Icon + label, never colour alone (same rule as StatusBadge)
const RECEPTION: Record<Reception, { icon: string; label: string }> = {
  loved: { icon: "♥", label: "Loved" },
  liked: { icon: "↑", label: "Liked" },
  mixed: { icon: "↔", label: "Mixed" },
  disliked: { icon: "↓", label: "Disliked" },
  "no comments": { icon: "–", label: "No comments" },
};

const TOPIC: Record<string, string> = {
  ad_creative: "The ad itself", product: "The product", annoyance: "Seeing the ad too often",
  question: "Unanswered questions", other: "Off-topic",
};

const AGE: Record<string, string> = { under_18: "Under 18", "18_24": "18–24", "25_44": "25–44", "45_plus": "45+" };

export default function LayaInsights({ data }: { data: YouTubeInsights }) {
  const s = data.summary;
  const best = s.best_ads[0];
  const [complaint, complaintAds] = Object.entries(s.top_complaints)[0] ?? [];
  const lengths = Object.entries(s.engagement_by_length);
  const bestLength = lengths.reduce<(typeof lengths)[number] | undefined>(
    (top, l) => (!top || l[1].avg_engagement_rate > top[1].avg_engagement_rate ? l : top), undefined);
  const ages = Object.entries(s.age_groups_from_comments);
  const ads = [...data.videos].sort((a, b) => b.views - a.views);

  return (
    <>
      <section className="tiles" aria-label="Laya insights">
        <Tile label="1M+ view ads" value={fmtNum(s.million_view_ads)} note={`Out of ${fmtNum(s.videos)} ads`} />
        <Tile label="Best ad" value={best ? fmtCompact(best.views) : "—"}
          note={best ? best.title : "No 1M+ ad with good comments"} />
        <Tile label="Top complaint" value={complaint ? TOPIC[complaint] ?? complaint : "None"}
          note={complaint ? `Main complaint on ${fmtNum(complaintAds!)} ad${complaintAds === 1 ? "" : "s"}` : "No ad was mostly criticised"} />
        <Tile label="Most engaging length" value={bestLength?.[0] ?? "—"}
          note={bestLength ? `${fmtPct(bestLength[1].avg_engagement_rate)} avg engagement` : ""} />
      </section>

      <section className="card">
        <div className="card-head"><h2>What viewers say</h2></div>
        <p className="muted small">
          The Laya model read each ad's top comments. Good / bad shares count a comment once per like,
          so a comment with 1,000 likes outweighs one with 3.
        </p>
        <div className="table-wrap">
          <table className="runs laya-table">
            <thead>
              <tr>
                <th>Ad</th><th className="num">Views</th><th>Reception</th>
                <th className="num">Good</th><th className="num">Bad</th><th>Main complaint</th><th>Age hint</th>
              </tr>
            </thead>
            <tbody>
              {ads.map((a) => (
                <Fragment key={a.video_id}>
                  <tr>
                    <td>
                      <a href={a.url} target="_blank" rel="noreferrer">{a.title}</a>
                      <div className="muted small">
                        {a.channel} · {fmtDuration(a.duration_seconds)} · {fmtPct(a.engagement_rate)} engagement
                        {a.million_views && <span className="top-tag">1M+ views</span>}
                      </div>
                    </td>
                    <td className="num">{fmtCompact(a.views)}</td>
                    <td><ReceptionBadge r={a.reception} /></td>
                    <td className="num">{a.positive_pct === null ? "—" : `${a.positive_pct}%`}</td>
                    <td className="num">{a.negative_pct === null ? "—" : `${a.negative_pct}%`}</td>
                    <td>{a.main_complaint ? TOPIC[a.main_complaint] ?? a.main_complaint : "—"}</td>
                    <td>{AGE[a.age_group_guess] ? `${AGE[a.age_group_guess]} (${a.age_hints})` : "—"}</td>
                  </tr>
                  {(a.best_comment || a.worst_comment) && (
                    <tr className="yt-comments-row"><td colSpan={7}><Quotes ad={a} /></td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="laya-extra">
        <div className="card">
          <h2>Engagement by ad length</h2>
          <p className="muted small">(Likes + comments) ÷ views. Real watch time is only visible to the channel owner.</p>
          <dl className="facts">
            {lengths.map(([label, v]) => (
              <Fragment key={label}>
                <dt>{label}</dt>
                <dd>{fmtPct(v.avg_engagement_rate)} <span className="muted small">· {fmtNum(v.ads)} ad{v.ads === 1 ? "" : "s"}</span></dd>
              </Fragment>
            ))}
          </dl>
        </div>
        <div className="card">
          <h2>Age hints from comments</h2>
          <p className="muted small">
            A guess from what commenters say about themselves ("my kids", "in college"), not real viewer
            ages. YouTube only shows those to the channel owner.
          </p>
          {!ages.length ? <p className="muted">No comment gave away an age.</p> : (
            <dl className="facts">
              {ages.map(([group, n]) => (
                <Fragment key={group}>
                  <dt>{AGE[group] ?? group}</dt>
                  <dd>Most likely group on {fmtNum(n)} ad{n === 1 ? "" : "s"}</dd>
                </Fragment>
              ))}
            </dl>
          )}
        </div>
      </section>
    </>
  );
}

function ReceptionBadge({ r }: { r: Reception }) {
  const { icon, label } = RECEPTION[r] ?? { icon: "?", label: r };
  return (
    <span className={`badge reception-${r.replace(" ", "-")}`}>
      <span className="badge-icon" aria-hidden="true">{icon}</span>{label}
    </span>
  );
}

function Quotes({ ad }: { ad: AdInsight }) {
  return (
    <div className="laya-quotes">
      {ad.best_comment && <p><strong>Best comment:</strong> “{ad.best_comment}”</p>}
      {ad.worst_comment && <p><strong>Worst comment:</strong> “{ad.worst_comment}”</p>}
    </div>
  );
}
