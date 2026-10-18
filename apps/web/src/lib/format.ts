const usd = new Intl.NumberFormat("en-IN", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
const num = new Intl.NumberFormat("en-IN");
const dt = new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" });

export const fmtUsd = (n: number) => usd.format(n);
export const fmtNum = (n: number) => num.format(n);
export const fmtDate = (iso: string) => dt.format(new Date(iso));

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return fmtDate(iso);
}

const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });
export const fmtCompact = (n: number) => compact.format(n);
export const fmtPct = (r: number) => `${(r * 100).toFixed(2)}%`;

export function fmtDuration(sec: number): string {
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const mmss = `${m}:${String(s).padStart(2, "0")}`;
  return h ? `${h}:${mmss.padStart(5, "0")}` : mmss;
}
