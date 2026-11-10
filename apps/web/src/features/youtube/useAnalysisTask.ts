import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type TaskStatus, type YouTubeInsights } from "../../api/client";

const POLL_MS = 3000;
const MAX_FAILS = 10;   // ~30s of failed polls in a row before giving up

// The task id survives a page refresh in this tab, so a long analysis isn't lost
const storeKey = (wsId: number) => `laya-task:${wsId}`;
const readId = (wsId: number | undefined) => {
  if (!wsId) return null;
  try { return sessionStorage.getItem(storeKey(wsId)); } catch { return null; }
};
const writeId = (wsId: number, id: string | null) => {
  try {
    if (id) sessionStorage.setItem(storeKey(wsId), id);
    else sessionStorage.removeItem(storeKey(wsId));
  } catch { /* storage blocked: resuming after refresh just won't work */ }
};

/** Queues a CSV for the model machine (POST taskinput) and polls until task_complete is 1. */
export function useAnalysisTask(wsId: number | undefined) {
  const [taskId, setTaskId] = useState<string | null>(() => readId(wsId));
  const [status, setStatus] = useState<TaskStatus | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [result, setResult] = useState<YouTubeInsights | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Switching workspace: pick up that workspace's running task, if any
  useEffect(() => { setTaskId(readId(wsId)); setStatus(null); }, [wsId]);

  const stop = useCallback(() => {
    if (wsId) writeId(wsId, null);
    setTaskId(null);
    setStatus(null);
    setStartedAt(null);
  }, [wsId]);

  const start = useCallback(async (csv: Blob, filename: string) => {
    if (!wsId) return;
    setError("");
    setResult(null);
    setSubmitting(true);
    try {
      const r = await api.taskInput(wsId, csv, filename);
      writeId(wsId, r.task_id);
      setStatus(r.status);
      setStartedAt(Date.now());
      setTaskId(r.task_id);
    } catch (err) { setError((err as Error).message); }
    finally { setSubmitting(false); }
  }, [wsId]);

  useEffect(() => {
    if (!wsId || !taskId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let fails = 0;
    const tick = async () => {
      try {
        const t = await api.analysisTask(wsId, taskId);
        if (cancelled) return;
        fails = 0;
        setStatus(t.status);
        setStartedAt(Date.parse(t.created_at));
        if (t.task_complete) {
          stop();
          if (t.status === "done" && t.output) setResult(t.output);
          else setError(t.error ?? "The analysis failed. Please try again.");
          return;
        }
      } catch (err) {
        if (cancelled) return;
        const gone = err instanceof ApiError && [401, 404, 422].includes(err.status);
        if (gone || ++fails >= MAX_FAILS) {
          stop();
          setError(gone ? "That analysis is no longer available." : "Lost contact with the server. Please try again.");
          return;
        }
      }
      timer = setTimeout(tick, POLL_MS);
    };
    void tick();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [wsId, taskId, stop]);

  const clear = useCallback(() => { setResult(null); setError(""); }, []);

  return {
    start, clear, result, error,
    busy: submitting || !!taskId,
    status: submitting ? null : status,   // null while uploading
    startedAt,
  };
}
