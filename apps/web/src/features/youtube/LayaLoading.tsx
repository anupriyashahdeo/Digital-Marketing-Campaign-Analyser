import { useEffect, useState } from "react";
import type { TaskStatus } from "../../api/client";

const STEPS: { key: "upload" | "queued" | "processing"; label: string }[] = [
  { key: "upload", label: "Uploading CSV" },
  { key: "queued", label: "Waiting for the model" },
  { key: "processing", label: "Laya is reading comments" },
];

function elapsed(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** Shown while a queued analysis runs on the model machine. */
export default function LayaLoading({ status, startedAt }: { status: TaskStatus | null; startedAt: number | null }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const current = status === "processing" ? 2 : status === "queued" ? 1 : 0;
  return (
    <section className="card laya-loading" role="status" aria-live="polite" aria-busy="true">
      <div className="spinner" aria-hidden="true" />
      <div>
        <h2>{STEPS[current].label}…</h2>
        <ol className="laya-steps">
          {STEPS.map((s, i) => (
            <li key={s.key} className={i < current ? "done" : i === current ? "current" : ""}>
              <span aria-hidden="true">{i < current ? "✓" : i === current ? "•" : "○"}</span> {s.label}
            </li>
          ))}
        </ol>
        <p className="muted small">
          {startedAt ? `${elapsed(now - startedAt)} elapsed. ` : ""}
          Large CSVs can take a few minutes. You can keep using this page, or refresh it — the
          results will appear here when they're ready.
        </p>
      </div>
    </section>
  );
}
