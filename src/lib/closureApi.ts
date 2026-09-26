import { request } from "@/lib/api";

export type Criterion = {public_id?: string; scope: string; code: string; mandatory: boolean; label?: string};
export type ClosurePolicy = {public_id: string; version: number; effective_from: string; effective_until: string | null; recorded_at: string; criteria: Criterion[]};
export type ClosureItem = {code: string; label: string; mandatory: boolean; state: "PASS" | "FAIL" | "UNKNOWN"; criteria: Criterion[]};
export type Assessment = {policy: ClosurePolicy | null; shipment_version: number; lifecycle_status: string; assessed_at: string; modes: string[];
  items: ClosureItem[]; missing: ClosureItem[]; normal_ready: boolean; message: string | null; fingerprint: string};
export type ClosureView = {assessment: Assessment; decision: null | {public_id: string; kind: "NORMAL" | "EXCEPTIONAL"; reason: string | null;
  actor: string; occurred_at: string; recorded_at: string; shipment_version: number; assessment: Assessment; missing_items: ClosureItem[]}; can_close: boolean; can_close_exceptionally: boolean};
export type ClosureConfiguration = {versions: ClosurePolicy[]; criteria: Record<string,string>; scopes: string[]};
const post = (path: string, payload: unknown, key: string) => request<{data: {public_id: string; created: boolean}}>(path,
  {method: "POST", cache: "no-store", headers: {"Idempotency-Key": key}, body: JSON.stringify(payload)});
export const getClosure = (id: string, signal?: AbortSignal) => request<{data: ClosureView}>(`/api/operational-shipments/${id}/closure`, {cache:"no-store", signal});
export const getClosureConfiguration = (signal?: AbortSignal) => request<{data: ClosureConfiguration}>("/api/admin/closure-policy", {cache:"no-store", signal});
export const saveClosurePolicy = (payload: {expected_version: number; effective_from: string; criteria: Criterion[]}, key: string) => post("/api/admin/closure-policy/versions", payload, key);
export const closeShipment = (id: string, assessment: Assessment, kind: "NORMAL" | "EXCEPTIONAL", reason: string, key: string) => post(`/api/operational-shipments/${id}/close`, {
  kind, reason: reason.trim() || null, expected_shipment_version: assessment.shipment_version,
  policy_version_public_id: assessment.policy?.public_id, assessment_fingerprint: assessment.fingerprint,
}, key);
