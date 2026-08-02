import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import OperationalPermission from "@/components/OperationalPermission";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ApiError,
  commandRouteCheckpoint,
  correctRouteMilestone,
  getOperationalShipment,
  getRoutePlan,
  getRouteTimeline,
  listRouteExceptions,
  listRoutePlans,
  reconcileRouteExceptions,
  reconcileRouteTimeline,
  replanRoute,
  resolveRouteException,
  verifyRouteMilestone,
  type OperationalShipmentSummary,
  type RouteException,
  type RoutePlanDetail,
  type RoutePlanSummary,
  type RouteTimeline,
} from "@/lib/api";
import { useI18n } from "@/i18n";
import ShipmentCargoItems from "@/components/ShipmentCargoItems";

const key = () => crypto.randomUUID();
const safeError = (error: unknown) => {
  if (error instanceof ApiError) {
    if (error.status === 403) return "You do not have permission to perform this action.";
    if (error.status === 404) return "This operational record is no longer available.";
    if (error.status === 409) return "The record changed. Refresh and try again.";
    if (error.status === 422) return "Check the entered values and try again.";
    return "The operation could not be completed.";
  }
  return error instanceof Error ? error.message : "The operation could not be completed.";
};
const when = (value: string | null | undefined, locale: string) =>
  value ? new Date(value).toLocaleString(locale, { timeZoneName: "short" }) : "Not recorded";

export default function OperationalShipmentDetail() {
  const shipmentId = Number(useParams().id);
  const { t, direction, locale } = useI18n();
  const [data, setData] = useState<OperationalShipmentSummary>();
  const [plans, setPlans] = useState<RoutePlanSummary[]>([]);
  const [plan, setPlan] = useState<RoutePlanDetail>();
  const [timeline, setTimeline] = useState<RouteTimeline>();
  const [exceptions, setExceptions] = useState<RouteException[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState("");
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const activePlan = useMemo(() => plans.find((item) => item.is_active), [plans]);

  const load = useCallback(async () => {
    try {
      setError("");
      const [shipment, revisions, routeTimeline, routeExceptions] = await Promise.all([
        getOperationalShipment(shipmentId),
        listRoutePlans(shipmentId),
        getRouteTimeline(shipmentId),
        listRouteExceptions(shipmentId),
      ]);
      setData(shipment.data);
      setPlans(revisions.data);
      setTimeline(routeTimeline.data);
      setExceptions(routeExceptions.data);
      const active = revisions.data.find((item) => item.is_active);
      setPlan(active ? (await getRoutePlan(shipmentId, active.id)).data : undefined);
    } catch (caught) {
      setError(safeError(caught));
    }
  }, [shipmentId]);

  useEffect(() => { void load(); }, [load]);

  const run = async (name: string, action: () => Promise<unknown>, success: string) => {
    if (pending) return;
    try {
      setPending(name); setError(""); setNotice("");
      const response = await action() as { data?: { replayed?: boolean; updated_checkpoints?: number } };
      const noOp = response?.data?.replayed || response?.data?.updated_checkpoints === 0;
      setNotice(noOp ? "No timeline changes were required." : success);
      await load();
    } catch (caught) {
      setError(safeError(caught));
    } finally {
      setPending("");
    }
  };
  const requireReason = (name: string, action: (reason: string) => Promise<unknown>, success: string) => {
    const reason = reasons[name]?.trim();
    if (!reason) { setError("A reason is required."); return; }
    void run(name, () => action(reason), success);
  };

  if (!data && !error) return <p className="p-8">{t("operations.loading")}</p>;
  return (
    <main className="min-h-screen overflow-x-hidden bg-slate-50 p-3 sm:p-4 md:p-8" dir={direction}>
      <div className="mx-auto max-w-6xl space-y-5">
        <Link className="inline-flex min-h-11 items-center" to="/operations/shipments">← {t("operations.back")}</Link>
        {error && <div role="alert" className="rounded bg-red-50 p-3 text-red-700">{error} <Button variant="link" onClick={() => void load()}>{t("operations.retry")}</Button></div>}
        {notice && <div role="status" className="rounded bg-emerald-50 p-3 text-emerald-800">{notice}</div>}
        {data && <>
          <header>
            <h1 className="text-2xl font-bold">{t("operations.shipmentDetail")} #{data.id}</h1>
            <p>{data.customer || "Not provided"} · Quote #{data.source.accepted_quote_id} · Request #{data.source.shipment_request_id} · {data.status} · Shipment v{data.version}</p>
          </header>

          <Card>
            <CardHeader><CardTitle>Active route plan</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <p>{activePlan ? `Revision ${activePlan.revision_number} · ${activePlan.status} · plan v${activePlan.version}` : "No active route plan"}</p>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-label="Multi-leg route">
                {(plan?.legs || data.route_legs || [data.route_leg]).map((leg, index) => (
                  <article key={leg.id} className="min-w-0 rounded border p-3">
                    <strong>Leg {index + 1}</strong>
                    <p className="break-words">{leg.origin.display_name || "Unknown"} → {leg.destination.display_name || "Unknown"}</p>
                    <p>{leg.transport_mode} · {leg.status || "planned"} · v{leg.version}</p>
                    <p>Planned: {when(leg.planned_departure, locale)} → {when(leg.planned_arrival, locale)}</p>
                    {"projected_departure" in leg && <p>Projected: {when(leg.projected_departure, locale)} → {when(leg.projected_arrival, locale)}</p>}
                    {"actual_departure" in leg && <p>Actual: {when(leg.actual_departure, locale)} → {when(leg.actual_arrival, locale)}</p>}
                    {"source_route_leg_id" in leg && leg.source_route_leg_id && <p>Copied from leg #{leg.source_route_leg_id}</p>}
                  </article>
                ))}
              </div>
            </CardContent>
          </Card>

          <ShipmentCargoItems shipmentPublicId={data.public_id} legacyDescription={(data as OperationalShipmentSummary & {legacy_cargo_description?:string|null}).legacy_cargo_description} />

          <Card>
            <CardHeader><CardTitle>Timeline reconciliation</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p>Revision {timeline?.route_plan_revision ?? "—"} · reconciliation v{timeline?.reconciliation_version ?? "—"} · reconciled {when(timeline?.reconciled_at, locale)}</p>
              <div className="overflow-x-auto rounded border">
                <table className="min-w-[760px] w-full text-sm">
                  <thead><tr className="bg-slate-100 text-start"><th className="p-2">Checkpoint</th><th>Planned</th><th>Projected</th><th>Actual</th><th>Effective / source</th><th>Delay</th></tr></thead>
                  <tbody>{(timeline?.planned || []).map((row) => {
                    const projected = timeline?.projected.find((item) => item.checkpoint_id === row.checkpoint_id);
                    const actual = timeline?.actual.find((item) => item.checkpoint_id === row.checkpoint_id);
                    const effective = timeline?.effective.find((item) => item.checkpoint_id === row.checkpoint_id);
                    const delay = timeline?.delays.find((item) => item.checkpoint_id === row.checkpoint_id);
                    return <tr key={row.checkpoint_id} className="border-t align-top">
                      <td className="p-2">#{row.checkpoint_id}</td>
                      <td>{when(row.arrival_at, locale)}<br />{when(row.departure_at, locale)}</td>
                      <td>{when(projected?.arrival_at, locale)}<br />{when(projected?.departure_at, locale)}</td>
                      <td>{when(actual?.arrival_at, locale)}<br />{when(actual?.departure_at, locale)}</td>
                      <td>{when(effective?.arrival_at, locale)} ({effective?.arrival_source || "—"})<br />{when(effective?.departure_at, locale)} ({effective?.departure_source || "—"})</td>
                      <td>{delay ? `${Math.ceil(delay.seconds / 60)} min` : "No delay"}</td>
                    </tr>;
                  })}</tbody>
                </table>
              </div>
              {!timeline?.planned.length && <p>No timeline entries.</p>}
              {activePlan && <OperationalPermission permission="route_plan.replan"><Button className="min-h-11" disabled={!!pending} onClick={() => void run("timeline", () => reconcileRouteTimeline(shipmentId, activePlan.version, key()), "Timeline reconciled.")}>{pending === "timeline" ? "Reconciling…" : "Reconcile timeline"}</Button></OperationalPermission>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Checkpoints and milestone lifecycle</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {!plan?.checkpoints.length && <p>No checkpoints.</p>}
              {plan?.checkpoints.map((checkpoint) => <article key={checkpoint.id} className="rounded border p-3">
                <h3 className="font-semibold">#{checkpoint.sequence_number} {checkpoint.checkpoint_type} · {checkpoint.status} · checkpoint v{checkpoint.version}</h3>
                <p>Planned arrival/departure: {when(checkpoint.planned_arrival_at, locale)} / {when(checkpoint.planned_departure_at, locale)}</p>
                <p>Projected arrival/departure: {when(checkpoint.projected_arrival_at, locale)} / {when(checkpoint.projected_departure_at, locale)}</p>
                <p>Actual arrival/departure: {when(checkpoint.actual_arrival_at, locale)} / {when(checkpoint.actual_departure_at, locale)}</p>
                <div className="my-3 flex flex-wrap gap-2">
                  <OperationalPermission permission="checkpoint.report">
                    {(checkpoint.status === "planned" || checkpoint.status === "approaching") && <Button className="min-h-11" disabled={!!pending} variant="outline" onClick={() => void run(`${checkpoint.id}-arrive`, () => commandRouteCheckpoint(shipmentId, checkpoint.id, "arrive", new Date().toISOString(), checkpoint.version, key()), "Arrival recorded.")}>Report arrival</Button>}
                    {(checkpoint.status === "arrived" || checkpoint.status === "processing") && <Button className="min-h-11" disabled={!!pending} variant="outline" onClick={() => void run(`${checkpoint.id}-complete-processing`, () => commandRouteCheckpoint(shipmentId, checkpoint.id, "complete-processing", new Date().toISOString(), checkpoint.version, key()), "Processing completion recorded.")}>Report processing complete</Button>}
                    {checkpoint.status === "ready_to_depart" && <Button className="min-h-11" disabled={!!pending} variant="outline" onClick={() => void run(`${checkpoint.id}-depart`, () => commandRouteCheckpoint(shipmentId, checkpoint.id, "depart", new Date().toISOString(), checkpoint.version, key()), "Departure recorded.")}>Report departure</Button>}
                  </OperationalPermission>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">{checkpoint.milestones.map((milestone) => {
                  const reasonKey = `milestone-${milestone.id}`;
                  return <div key={milestone.id} className="rounded bg-slate-50 p-3">
                    <strong>{milestone.type}</strong> · {milestone.verification_state} · milestone v{milestone.version}
                    <p>Planned {when(milestone.planned_at, locale)} · Projected {when(milestone.projected_at, locale)} · Actual {when(milestone.occurred_at, locale)}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {milestone.verification_state === "reported" && <OperationalPermission permission="checkpoint.verify"><Button className="min-h-11" disabled={!!pending} onClick={() => void run(`verify-${milestone.id}`, () => verifyRouteMilestone(shipmentId, checkpoint.id, milestone.id, milestone.version, key()), "Milestone verified or re-verified.")}>Verify / re-verify</Button></OperationalPermission>}
                    </div>
                    {milestone.verification_state === "verified" && <OperationalPermission permission="milestone.correct"><div className="mt-2 flex flex-col gap-2 sm:flex-row"><Input aria-label={`Correction reason ${milestone.id}`} placeholder="Correction reason (required)" value={reasons[reasonKey] || ""} onChange={(event) => setReasons({...reasons,[reasonKey]:event.target.value})}/><Button className="min-h-11" disabled={!!pending} variant="secondary" onClick={() => requireReason(reasonKey, (reason) => correctRouteMilestone(shipmentId, checkpoint.id, milestone.id, new Date().toISOString(), reason, milestone.version, key()), "Milestone corrected.")}>Correct</Button></div></OperationalPermission>}
                  </div>;
                })}</div>
              </article>)}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Replan and revision history</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {plans.map((item) => <div key={item.id} className="rounded border p-3"><strong>Revision {item.revision_number}</strong> · {item.is_active ? "Active target" : item.status} · v{item.version}{item.created_from_plan_id ? ` · supersedes plan #${item.created_from_plan_id}` : ""}<br />{item.replan_reason && `Reason: ${item.replan_reason}`}</div>)}
              {activePlan && <OperationalPermission permission="route_plan.replan"><div className="flex flex-col gap-2 sm:flex-row"><Input aria-label="Replan reason" placeholder="Replan reason (required)" value={reasons.replan || ""} onChange={(event) => setReasons({...reasons,replan:event.target.value})}/><Button className="min-h-11" disabled={!!pending} onClick={() => requireReason("replan", (reason) => replanRoute(shipmentId, activePlan.id, activePlan.version, reason, key()), "A new active revision was created.")}>Replan future segments</Button></div><p className="text-sm text-slate-600">Completed segments remain read-only; only future segments are copied into the new revision.</p></OperationalPermission>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Route exceptions and work items</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {activePlan && <OperationalPermission permission="route_exception.manage"><Button className="min-h-11" disabled={!!pending} onClick={() => void run("exceptions", () => reconcileRouteExceptions(shipmentId, activePlan.version, key()), "Route exceptions reconciled.")}>Reconcile exceptions</Button></OperationalPermission>}
              {!exceptions.length && <p>No route-exception history.</p>}
              {exceptions.map((exception) => {
                const reasonKey = `exception-${exception.id}`;
                return <article key={exception.id} className="rounded border p-3">
                  <strong>{exception.type}</strong> · {exception.status} · {exception.severity} · v{exception.version}
                  <p>Checkpoint #{exception.checkpoint_id ?? "—"} · plan #{exception.route_plan_id}</p>
                  <p>Detected {when(exception.detected_at, locale)} · due {when(exception.due_at, locale)} · resolved {when(exception.resolved_at, locale)}</p>
                  <p>Source: {exception.resolution_source || "Not resolved"} · Reason: {exception.resolution_reason || exception.reason || "Not provided"}</p>
                  {exception.status === "open" && <OperationalPermission permission="route_exception.manage"><div className="mt-2 flex flex-col gap-2 sm:flex-row"><Input aria-label={`Resolution reason ${exception.id}`} placeholder="Resolution reason (required)" value={reasons[reasonKey] || ""} onChange={(event) => setReasons({...reasons,[reasonKey]:event.target.value})}/><Button className="min-h-11" disabled={!!pending} onClick={() => requireReason(reasonKey, (reason) => resolveRouteException(exception.id, exception.version, reason, key()), "Exception resolved.")}>Resolve manually</Button></div></OperationalPermission>}
                </article>;
              })}
              <h3 className="font-semibold">{t("operations.workQueue")}</h3>
              {!data.open_work_items.length && <p>No actionable work items.</p>}
              {data.open_work_items.map((item) => <div key={item.id} className="rounded border p-3">#{item.id} · {item.type} · {item.status === "open" ? "Actionable" : "Non-actionable"} · due {when(item.due_at, locale)} · v{item.version}</div>)}
            </CardContent>
          </Card>

          <Card><CardHeader><CardTitle>{t("operations.eventHistory")}</CardTitle></CardHeader><CardContent>{!data.recent_events.length ? <p>No event history.</p> : data.recent_events.map((event) => <div key={event.id}>{event.event_type} · {when(event.occurred_at, locale)} {event.reason && `· ${event.reason}`}</div>)}</CardContent></Card>
          <Card><CardHeader><CardTitle>Audit history</CardTitle></CardHeader><CardContent>{!data.audit_summary.length ? <p>No audit history.</p> : data.audit_summary.map((item) => <div key={item.id}>{item.action} · {when(item.recorded_at, locale)}</div>)}</CardContent></Card>
        </>}
      </div>
    </main>
  );
}
