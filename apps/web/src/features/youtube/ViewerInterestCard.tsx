import { Link } from "react-router-dom";
import type { ViewerInterest } from "../../api/client";
import { fmtNum, timeAgo } from "../../lib/format";

export default function ViewerInterestCard({ data }: { data: ViewerInterest }) {
  return (
    <section className="card">
      <div className="card-head">
        <h2>Viewer interest</h2>
        <Link to="/youtube">Analyse more videos</Link>
      </div>
      <p>
        <strong>{fmtNum(data.interested_people)} people</strong> showed interest in the product
        across {fmtNum(data.video_count)} video{data.video_count === 1 ? "" : "s"}.
      </p>
      <p className="muted small">
        Latest YouTube analysis, {timeAgo(data.analysed_at)}. Counts each commenter wanting to buy or try the
        product, plus the likes on those comments. It only covers top comments, so it shows visible interest,
        not how many viewers overall are interested.
      </p>
      <div className="table-wrap">
        <table className="runs">
          <thead>
            <tr><th>Video</th><th className="num">Interested</th></tr>
          </thead>
          <tbody>
            {data.top_videos.map((v) => (
              <tr key={v.url}>
                <td><a href={v.url} target="_blank" rel="noreferrer">{v.title}</a></td>
                <td className="num">
                  {fmtNum(v.interested_people)}
                  <div className="muted small nowrap">{v.interested_comments} of {v.comments_read} comments</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
