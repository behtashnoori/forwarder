import type { CustomerSharedDocument } from "@/lib/customerPortalApi";

export interface CustomerShipmentIdentity {
  public_id: string; created_at: string; status: "planned" | "in_progress" | "completed" | "cancelled";
  shared_transport: boolean;
}
export interface CustomerShipmentList {
  authorization_revision: string;
  items: CustomerShipmentIdentity[];
  pagination: { page: number; total: number; has_prev: boolean; has_next: boolean };
}
export interface CustomerFactPage<T> { items: T[]; page: number; has_prev: boolean; has_next: boolean }
export interface CustomerCargo {
  public_id: string; label: string; customer_label: string; type_label: string; uom_symbol: string;
  requested: string | null; planned: string | null; known_actual: string | null;
  delivered: string; remaining: string | null; excess: string | null; has_delivery: boolean;
}
export interface CustomerDelivery {
  public_id: string; cargo_public_id: string; quantity: string; uom_symbol: string; destination_text: string;
  occurred_at: string; recorded_at: string; revision: number; status: "CURRENT" | "SUPERSEDED";
  is_correction: boolean; evidence: { public_id: string; filename: string; version: number; status: string }[];
}
export interface CustomerReport {
  public_id: string; kind: string; message: string; occurred_at: string; recorded_at: string;
  source_label: string; scope_label: string; reported_location: string | null;
  status: "CURRENT" | "SUPERSEDED"; is_correction: boolean;
}
export interface CustomerShipmentDetail extends CustomerShipmentIdentity {
  authorization_revision: string;
  cargo: CustomerCargo[];
  routes: { cargo_public_id: string; legs: { origin: string | null; destination: string | null; mode: string | null }[] }[];
  documents: CustomerFactPage<CustomerSharedDocument>;
  deliveries: CustomerFactPage<CustomerDelivery>;
  timeline: CustomerFactPage<CustomerReport>;
  reported_locations: CustomerReport[];
}
