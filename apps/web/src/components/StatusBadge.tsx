import type { RunStatus } from "../api/client";

// Icon + label, never colour alone (colour-blind and print safe).
const LOOK: Record<RunStatus, { icon: string; label: string }> = {
  queued: { icon: "◷", label: "Queued" },
  running: { icon: "◐", label: "Running" },
  completed: { icon: "✓", label: "Completed" },
  failed: { icon: "!", label: "Failed" },
  cancelled: { icon: "×", label: "Cancelled" },
};

export default function StatusBadge({ status }: { status: RunStatus }) {
  const { icon, label } = LOOK[status] ?? { icon: "?", label: status };
  return (
    <span className={`badge badge-${status}`}>
      <span className="badge-icon" aria-hidden="true">{icon}</span>{label}
    </span>
  );
}
