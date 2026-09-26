import { request } from "@/lib/api";

export type TransferPerson = { id: number; display_name: string };
export type OwnerTransfer = {
  public_id: string; sequence: number; old_owner: TransferPerson; new_owner: TransferPerson;
  actor: TransferPerson; reason: string; occurred_at: string; recorded_at: string;
  previous_shipment_version: number; next_shipment_version: number;
};
export type OwnerTransferView = {
  shipment_public_id: string; shipment_version: number; current_owner: TransferPerson;
  initial_owner: TransferPerson & { provenance: string; occurred_at: null };
  transfers: OwnerTransfer[]; page: number; has_more: boolean;
  capabilities: { TRANSFER_OWNER: boolean }; available: boolean; old_owner_open_work_count: number | null;
};
export type TransferCommand = { expected_owner_id: number; target_owner_id: number; expected_version: number; reason: string };
export const getOwnerTransfers = (shipment: string, page = 1, signal?: AbortSignal) =>
  request<{data: OwnerTransferView}>(`/api/operational-shipments/${shipment}/owner-transfers?page=${page}`, {cache: "no-store", signal});
export const getOwnerCandidates = (shipment: string, search = "", page = 1, signal?: AbortSignal) =>
  request<{data: {candidates: TransferPerson[]; page: number; has_more: boolean}}>(
    `/api/operational-shipments/${shipment}/owner-transfer-candidates?${new URLSearchParams({search, page: String(page)})}`, {cache: "no-store", signal});
export const transferOwner = (shipment: string, payload: TransferCommand, key: string) =>
  request<{data: {public_id: string; created: boolean}}>(`/api/operational-shipments/${shipment}/owner-transfers`,
    {method: "POST", cache: "no-store", headers: {"Idempotency-Key": key}, body: JSON.stringify(payload)});
