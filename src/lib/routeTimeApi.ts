import { request, type OperationalLocationRef } from "@/lib/api";

export type TimeVersion = {
  public_id: string; version: number; movement_min_minutes: number | null; movement_max_minutes: number | null;
  stop_min_minutes: number | null; stop_max_minutes: number | null; effective_from: string; effective_until: string | null;
  recorded_at: string; actor_user_id: number; recorded_by: string | null;
};
export type RouteTime = { public_id: string; origin_label: string; destination_label: string; transport_mode: string;
  latest_version: number; current: TimeVersion | null; versions: TimeVersion[] };
export type ReferenceValues = Pick<TimeVersion, "movement_min_minutes" | "movement_max_minutes" | "stop_min_minutes" | "stop_max_minutes" | "effective_from">;
export type TimeSelection = { public_id: string; selection_revision: number; reference_at: string; recorded_at: string;
  actor_user_id: number; reference: TimeVersion };
export type LegTime = { leg_id: number; leg_version: number; sequence_number: number; origin_label: string; destination_label: string;
  transport_mode: string | null; reference_at: string; time_basis: "PLANNED_DEPARTURE" | "SELECTION_TIME";
  applicable: TimeVersion | null; selected: TimeSelection | null; selection_matches_leg: boolean; history: TimeSelection[]; can_select: boolean };
export type PlanTimes = { plan_id: number; plan_revision: number; plan_status: string; items: LegTime[] };
const post = (path: string, payload: unknown, key: string) => request<{data: {public_id: string; created: boolean}}>(path,
  {method: "POST", cache: "no-store", headers: {"Idempotency-Key": key}, body: JSON.stringify(payload)});
export const listRouteTimes = (page=1, signal?: AbortSignal) => request<{data: {items: RouteTime[]; page: number; total: number; has_next: boolean}}>(`/api/organization/route-reference-times?page=${page}`, {cache: "no-store", signal});
export const createRouteTime = (payload: ReferenceValues & {origin: OperationalLocationRef; destination: OperationalLocationRef; transport_mode: string}, key: string) => post("/api/admin/organization-route-reference-times", payload, key);
export const reviseRouteTime = (id: string, payload: ReferenceValues & {expected_version: number}, key: string) => post(`/api/admin/organization-route-reference-times/${id}/versions`,payload,key);
export const getPlanTimes = (shipment: string, plan: number, signal?: AbortSignal) => request<{data: PlanTimes}>(`/api/operational-shipments/${shipment}/route-plans/${plan}/reference-times`,{cache: "no-store",signal});
export const selectPlanTime = (shipment: string, plan: number, leg: LegTime, key: string) => post(`/api/operational-shipments/${shipment}/route-plans/${plan}/legs/${leg.leg_id}/reference-time`, {
  expected_version: leg.leg_version, expected_selection_revision: leg.selected?.selection_revision ?? 0,
  reference_version_public_id: leg.applicable?.public_id,
},key);
export function timeRange(min: number | null | undefined, max: number | null | undefined) {
  if (min == null || max == null) return "تعریف نشده";
  const value = (n: number) => n % 60 === 0 ? `${(n/60).toLocaleString("fa-IR")} ساعت` : `${n.toLocaleString("fa-IR")} دقیقه`;
  return min === max ? value(min) : `${value(min)} تا ${value(max)}`;
}
