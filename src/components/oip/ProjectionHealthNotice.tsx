import type { OipProjectionHealth } from "@/lib/api";

export function ProjectionHealthNotice({ health }: { health: OipProjectionHealth }) {
  const message = health.health_state === "FRESH"
    ? "Projection is reconciled with authoritative sources."
    : health.health_state === "STALE"
      ? "Intelligence may be outdated. Operational truth and actions remain authoritative."
      : health.health_state === "REBUILDING"
        ? "Intelligence projection is being rebuilt. Operational truth remains usable."
        : "Intelligence reliability is impaired. Operational truth remains usable.";
  const trusted = health.health_state === "FRESH";
  return <div role={trusted ? "status" : "alert"} data-testid="projection-health"
    className={`rounded border p-3 ${trusted ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-300 bg-amber-50 text-amber-900"}`}>
    <b>Intelligence health: {health.health_state}</b>
    <p>{message}</p>
    {health.reason_code && <p className="text-xs">Code: {health.reason_code}</p>}
  </div>;
}
