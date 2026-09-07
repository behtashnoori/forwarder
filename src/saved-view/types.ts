import type { SemanticQueryDefinition } from "@/dashboard/types";

export const SAVED_VIEW_SCHEMA_VERSION = "saved-view-definition-v1" as const;
export const SAVED_VIEW_SEMANTIC_VERSION = "analytics-semantic-v1" as const;
export type SavedViewColumn = "CUSTOMER"|"ROUTE"|"PLANNED_TIME"|"PROJECT"|"SOURCE"|"MILESTONE"|"OPEN_WORK_ITEMS"|"SHIPMENT_STATUS";
export interface SavedViewDefinition {
  schema_version: typeof SAVED_VIEW_SCHEMA_VERSION;
  semantic_version: typeof SAVED_VIEW_SEMANTIC_VERSION;
  surface: "OPERATIONAL_SHIPMENTS";
  query_definition: SemanticQueryDefinition;
  presentation: { columns: SavedViewColumn[]; sort: { field:"PLANNED_DEPARTURE"|"PLANNED_ARRIVAL"|"CREATED_AT"|"SHIPMENT_STATUS"; direction:"ASC"|"DESC" }; display_type:"LIST"; limit:number };
}
export interface SavedView { public_id:string; name:string; description:string; visibility:"PRIVATE"; status:"ACTIVE"|"ARCHIVED"; semantic_version:string; saved_view_schema_version:string; version:number; definition:SavedViewDefinition; }
