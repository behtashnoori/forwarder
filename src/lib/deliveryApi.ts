import { request } from "@/lib/api";

export interface DeliveryCargo {
  public_id: string; label: string; customer_label: string; uom_public_id: string; uom_symbol: string;
  known_actual: string | null; delivered: string; remaining: string | null; excess: string | null;
  has_delivery: boolean; can_record: boolean;
}
export interface DeliveryFact {
  public_id: string; cargo_public_id: string; quantity: string; uom_symbol: string; destination_text: string;
  occurred_at: string; recorded_at: string; revision: number; status: "CURRENT" | "SUPERSEDED";
  is_correction: boolean; actor_label: string; reason: string | null; corrects_public_id: string | null;
  evidence: Array<{ public_id: string; filename: string; version: number; status: string }>;
}
export interface DeliveryDraft {
  cargo_public_id: string; quantity: string; uom_public_id: string; destination_text: string;
  occurred_at: string; expected_version: number; corrects_public_id?: string; reason?: string | null;
  evidence_document_public_ids?: string[];
}
export interface DeliveryList { cargo: DeliveryCargo[]; items: DeliveryFact[]; can_manage: boolean; page: number; total: number }
const path = (shipment: string) => `/api/operational-shipments/${encodeURIComponent(shipment)}/deliveries`;
export const listDeliveries = (shipment: string, page = 1) => request<{ data: DeliveryList }>(`${path(shipment)}?page=${page}`, { cache: "no-store" });
export const recordDelivery = (shipment: string, draft: DeliveryDraft, key: string) => request<{ public_id: string; revision: number; created: boolean }>(path(shipment), {
  method: "POST", headers: { "Idempotency-Key": key }, body: JSON.stringify(draft),
});
