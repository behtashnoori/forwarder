import { request } from "@/lib/api";

export type ShipmentStageDefinition = {
  public_id: string;
  configuration_public_id: string;
  code: string;
  display_name_fa: string;
  sequence: number;
  active: boolean;
  required_for_completion: boolean;
};

export type ShipmentStageVersion = {
  public_id: string;
  version: number;
  effective_from: string;
  recorded_at: string;
  stages: ShipmentStageDefinition[];
};

export type ShipmentStageConfiguration = {
  canonical_stages: Array<{code: string; display_name_fa: string}>;
  versions: ShipmentStageVersion[];
};

export type ShipmentStageProgress = ShipmentStageDefinition & {
  status: "NOT_STARTED" | "STARTED" | "COMPLETED";
  started_at: string | null;
  completed_at: string | null;
};

export type ShipmentStagesView = {
  configuration: ShipmentStageVersion | null;
  pinned: boolean;
  instance_public_id: string | null;
  stages: ShipmentStageProgress[];
  can_record: boolean;
  project_required: false;
};

export type ShipmentStageDraft = {
  code: string;
  display_name_fa: string;
  sequence: number;
  active: boolean;
  required_for_completion: boolean;
};

export const getShipmentStageConfiguration = () => request<{data: ShipmentStageConfiguration}>(
  "/api/admin/shipment-stage-configuration", {cache: "no-store"},
);

export const saveShipmentStageConfiguration = (payload: {
  expected_version: number; effective_from: string; stages: ShipmentStageDraft[];
}, key: string) => request<{data: {public_id: string; created: boolean}}>(
  "/api/admin/shipment-stage-configuration/versions",
  {method: "POST", headers: {"Idempotency-Key": key}, body: JSON.stringify(payload)},
);

export const getShipmentOperationalStages = (shipment: string) => request<{data: ShipmentStagesView}>(
  `/api/operational-shipments/${encodeURIComponent(shipment)}/operational-stages`, {cache: "no-store"},
);

export const recordShipmentStageEvent = (
  shipment: string,
  definition: string,
  payload: {event_type: "STARTED" | "COMPLETED"; occurred_at: string; expected_policy_version_public_id: string},
  key: string,
) => request<{data: {public_id: string; created: boolean}}>(
  `/api/operational-shipments/${encodeURIComponent(shipment)}/operational-stages/${encodeURIComponent(definition)}/events`,
  {method: "POST", headers: {"Idempotency-Key": key}, body: JSON.stringify(payload)},
);

