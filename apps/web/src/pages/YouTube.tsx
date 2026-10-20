import { Fragment, useMemo, useState, type FormEvent } from "react";
import { api, type YouTubeOrder, type YouTubeResult, type YouTubeComment, type YouTubeVideo, type YouTubeVideoComments } from "../api/client";
import Tile from "../components/Tile";
import { fmtCompact, fmtDate, fmtDuration, fmtNum, fmtPct } from "../lib/format";
import { useWorkspace } from "../workspace/WorkspaceContext";

type SortKey = "views" | "likes" | "comments" | "engagement_rate" | "published_at";

const TOP_N = 10;
type CommentsByVideo = Record<string, YouTubeVideoComments>;

const COLUMNS: [SortKey, string][] = [
  ["published_at", "Published"], ["views", "Views"], ["likes", "Likes"],
  ["comments", "Comments"], ["engagement_rate", "Engagement"],
];

export default function YouTube() {
  const { workspace } = useWorkspace();
  const [q, setQ] = useState("");
  const [limit, setLimit] = useState(10);
  const [order, setOrder] = useState<YouTubeOrder>("relevance");
  const [language, setLanguage] = useState("en");
  const [result, setResult] = useState<YouTubeResult | null>(null);
  const [sort, setSort] = useState<SortKey>("views");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [comments, setComments] = useState<CommentsByVideo | null>(null);
  const [commentsBusy, setCommentsBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return setError("Enter a keyword or paste a YouTube link.");
    setError("");
    setComments(null);
    setBusy(true);
    try { setResult(await api.youtubeSearch(workspace!.id, q.trim(), limit, order, language)); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function loadComments(): Promise<CommentsByVideo | null> {
    setError("");
    setCommentsBusy(true);
    try {
      const r = await api.youtubeComments(workspace!.id, result!.videos.map((v) => v.video_id), TOP_N);
      const byVideo = Object.fromEntries(r.videos.map((v) => [v.video_id, v]));
      setComments(byVideo);
      return byVideo;
    } catch (err) { setError((err as Error).message); return null; }
    finally { setCommentsBusy(false); }
  }

  // One CSV: each video's stats plus its top comments in the same row
  async function download() {
    const byVideo = comments ?? await loadComments();
    if (byVideo) downloadCsv(videos, byVideo, result!.query);
  }

  const videos = useMemo(() => {
    const list = [...(result?.videos ?? [])];
    return list.sort((a, b) => sort === "published_at"
      ? b.published_at.localeCompare(a.published_at)
      : b[sort] - a[sort]);
  }, [result, sort]);

  const s = result?.summary;
  return (
    <>
      <div className="page-head">
        <div>
          <h1>YouTube explorer</h1>
          <p className="muted">Search by keyword or paste video links to pull public stats.</p>
        </div>
        {videos.length > 0 && (
          <button className="secondary" onClick={download} disabled={commentsBusy}>
            {commentsBusy ? "Preparing CSV…" : "Download CSV"}
          </button>
        )}
      </div>

      <section className="card">
        <form onSubmit={submit} className="yt-form">
          <div className="field">
            <label htmlFor="yt-q">Keyword or video links</label>
            <input id="yt-q" value={q} maxLength={500} placeholder="e.g. running shoes ad  —  or  https://youtu.be/…"
              onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="field-row yt-options">
            <div className="field">
              <label htmlFor="yt-order">Sort YouTube results by</label>
              <select id="yt-order" value={order} onChange={(e) => setOrder(e.target.value as YouTubeOrder)}>
                <option value="relevance">Relevance</option>
                <option value="viewCount">Most viewed</option>
                <option value="date">Newest</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="yt-limit">Results</label>
              <select id="yt-limit" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
                {[10, 25, 50].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="yt-lang">Language</label>
              <select id="yt-lang" value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="en">English</option>
                <option value="hi">Hindi</option>
              </select>
            </div>
          </div>
          {error && <div className="alert error" role="alert">{error}</div>}
          <button className="primary inline" disabled={busy}>{busy ? "Fetching…" : "Fetch data"}</button>
          <p className="muted small">Pasted links use 1 quota unit; a keyword search uses about 100 (10,000 free per day).</p>
        </form>
      </section>

      {s && (
        <section className="tiles" aria-label="Summary">
          <Tile label="Videos" value={fmtNum(s.count)} note={result!.mode === "lookup" ? "From your links" : `For “${result!.query}”`} />
          <Tile label="Total views" value={fmtCompact(s.total_views)} note={`${fmtNum(s.total_views)} views`} />
          <Tile label="Average views" value={fmtCompact(s.avg_views)} note="Per video" />
          <Tile label="Avg engagement" value={fmtPct(s.avg_engagement_rate)} note="(Likes + comments) ÷ views" />
        </section>
      )}

      {result && (
        <section className="card">
          <div className="card-head">
            <h2>Videos</h2>
            <div className="head-actions">
              <span className="muted small">Click a column to sort</span>
              {videos.length > 0 && (
                <button className="secondary" onClick={loadComments} disabled={commentsBusy}>
                  {commentsBusy ? "Fetching comments…" : comments ? "Refresh comments" : `Get top ${TOP_N} comments`}
                </button>
              )}
            </div>
          </div>
          {!videos.length ? <p className="muted">No videos found. Try a different keyword.</p> : (
            <div className="table-wrap">
              <table className="runs yt-table">
                <thead>
                  <tr>
                    <th>Video</th>
                    {COLUMNS.map(([key, label]) => (
                      <th key={key} className={key === "published_at" ? "" : "num"}
                        aria-sort={sort === key ? "descending" : "none"}>
                        <button className="link sort" onClick={() => setSort(key)}>
                          {label}{sort === key ? " ↓" : ""}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {videos.map((v) => (
                    <Fragment key={v.video_id}>
                    <tr className={v.video_id === s?.top_video_id ? "top" : ""}>
                      <td>
                        <div className="yt-video">
                          {v.thumbnail_url && <img src={v.thumbnail_url} alt="" loading="lazy" width={120} height={68} />}
                          <div>
                            <a href={v.url} target="_blank" rel="noreferrer">{v.title}</a>
                            <div className="muted small">
                              {v.channel_title} · {fmtDuration(v.duration_seconds)}
                              {v.video_id === s?.top_video_id && <span className="top-tag">Most viewed</span>}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="muted nowrap">{fmtDate(v.published_at)}</td>
                      <td className="num">{fmtNum(v.views)}</td>
                      <td className="num">{fmtNum(v.likes)}</td>
                      <td className="num">{fmtNum(v.comments)}</td>
                      <td className="num">{fmtPct(v.engagement_rate)}</td>
                    </tr>
                    {comments && (
                      <tr className="yt-comments-row">
                        <td colSpan={COLUMNS.length + 1}><CommentList data={comments[v.video_id]} /></td>
                      </tr>
                    )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}

function CommentList({ data }: { data?: YouTubeVideoComments }) {
  if (!data || data.comments_disabled) return <p className="muted small">Comments are turned off for this video.</p>;
  if (!data.comments.length) return <p className="muted small">No comments yet.</p>;
  return (
    <details className="yt-comments">
      <summary>Top {data.comments.length} comments</summary>
      <ol>
        {data.comments.map((c) => (
          <li key={c.comment_id}>
            <div className="muted small">
              <strong>{c.author}</strong> · {fmtDate(c.published_at)} · {fmtNum(c.likes)} likes · {fmtNum(c.replies)} replies
            </div>
            <p>{c.text}</p>
          </li>
        ))}
      </ol>
    </details>
  );
}

// Quote every cell; a leading = + - @ is prefixed so Excel doesn't run it as a formula
const csvCell = (x: string | number) => `"${String(x).replace(/^[=+\-@]/, "'$&").replace(/"/g, '""')}"`;

// One cell per comment, e.g. "Great ad! — @ana (1,204 likes)"; line breaks flattened so rows stay one line tall
const commentCell = (c: YouTubeComment) =>
  `${c.text.replace(/\s*\n+\s*/g, " ").trim()} — ${c.author} (${fmtNum(c.likes)} likes)`;

function downloadCsv(videos: YouTubeVideo[], comments: CommentsByVideo, query: string) {
  const head = ["video_id", "url", "title", "channel", "published_at", "duration_seconds",
    "views", "likes", "comments", "engagement_rate",
    ...Array.from({ length: TOP_N }, (_, i) => `top_comment_${i + 1}`)];
  const rows = videos.map((v) => {
    const c = comments[v.video_id];
    const top = c?.comments_disabled ? ["Comments turned off"] : (c?.comments ?? []).map(commentCell);
    return [v.video_id, v.url, v.title, v.channel_title, v.published_at, v.duration_seconds,
      v.views, v.likes, v.comments, v.engagement_rate,
      ...Array.from({ length: TOP_N }, (_, i) => top[i] ?? "")];
  });
  const lines = [head.join(","), ...rows.map((r) => r.map(csvCell).join(","))];
  // BOM so Excel reads UTF-8 (emoji, Hindi) correctly
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `youtube-${query.replace(/[^\w]+/g, "-").slice(0, 40) || "videos"}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}
