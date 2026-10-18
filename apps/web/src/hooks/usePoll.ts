import { useEffect, useRef } from "react";

/** Calls `fn` every `ms` while `enabled` and the tab is visible. Stops when the tab is hidden
 *  so idle tabs don't keep hitting the API. */
export function usePoll(fn: () => void, ms: number, enabled: boolean) {
  const saved = useRef(fn);
  saved.current = fn;
  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => { if (!document.hidden) saved.current(); }, ms);
    return () => clearInterval(id);
  }, [ms, enabled]);
}
