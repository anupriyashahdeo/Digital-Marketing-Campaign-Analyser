import { useEffect, useState } from "react";

export function useSSE<T>(url: string | null) {
  const [events, setEvents] = useState<T[]>([]);
  useEffect(() => {
    if (!url) return;
    const es = new EventSource(url);
    es.onmessage = (e) => setEvents((p) => [...p, JSON.parse(e.data) as T]);
    es.onerror = () => es.close();
    return () => es.close();
  }, [url]);
  return events;
}
