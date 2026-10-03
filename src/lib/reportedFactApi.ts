import { request } from "@/lib/api";

export type ReportScope = "SHIPMENT" | "ROUTE_STAGE" | "EXECUTION_UNIT" | "CARGO";
export type ReportKind = "LOCATION" | "PROGRESS" | "TRANSPORT_CHANGE" | "EFFECT";
export type ReportSource = "CARRIER_REPORT" | "DRIVER_REPORT" | "INTERNAL_EXPERT" | "OTHER_OPERATIONAL_SOURCE";
export interface ReportDraft {
  scope: ReportScope;
  target_public_id: string | null;
  kind: ReportKind;
  source: ReportSource;
  occurred_at: string;
  location?: { location_text: string } | null;
  route_progress?: { stage_execution_public_id: string; distance_remaining_km: string } | null;
  internal_note: string | null;
  customer_message: string | null;
  customer_effect: "CHANGE" | "DELAY";
  impacted_cargo_public_ids: string[];
  corrects_public_id?: string;
  reason?: string | null;
}
export interface ReportFact extends Omit<ReportDraft, "location"> {
  public_id: string;
  location: string | null;
  scope_label: string;
  source_label: string;
  recorded_at: string;
  actor_user_id: number;
  actor_label: string;
  status: "CURRENT" | "SUPERSEDED";
  route_progress: ({ stage_execution_public_id: string; distance_remaining_km: string; planned_distance_km: string | null;
    kind: "DISTANCE_REMAINING_KM"; route_plan_revision: number; route_leg_sequence: number; route_label: string }) | null;
}
export interface ReportList {
  items: ReportFact[];
  reported_locations: ReportFact[];
  page: number;
  total: number;
  can_manage: boolean;
  options: Record<ReportScope | "cargo", Array<{ public_id: string; label: string }>> & {
    progress_stages: Record<string, Array<{ public_id: string; label: string; route_plan_revision: number; route_leg_sequence: number }>>;
  };
}
const path = (shipment: string) => `/api/operational-shipments/${encodeURIComponent(shipment)}/reported-facts`;
export const listReportedFacts = (shipment: string, page = 1, kind?: ReportKind) => {
  const query = new URLSearchParams({ page: String(page) });
  if (kind) query.set("kind", kind);
  return request<{ data: ReportList }>(`${path(shipment)}?${query.toString()}`, { cache: "no-store" });
};
export const recordReportedFact = (shipment: string, draft: ReportDraft, key: string) => request<{ public_id: string; created: boolean }>(path(shipment), {
  method: "POST", headers: { "Idempotency-Key": key }, body: JSON.stringify(draft),
});
