import type { AnalyticsFilter } from "@/lib/api";
import { SAVED_VIEW_SCHEMA_VERSION, SAVED_VIEW_SEMANTIC_VERSION, type SavedViewDefinition } from "./types";

export type OperationalShipmentFilters = {status:string;customer:string;origin:string;destination:string;overdue:string;date_from:string;date_to:string};
export const unsupportedSavedViewFilters = (filters:OperationalShipmentFilters) => ["customer","origin","destination","overdue"].filter(key => filters[key as keyof OperationalShipmentFilters].trim());
export function toSavedViewDefinition(filters:OperationalShipmentFilters):SavedViewDefinition {
  const governed:AnalyticsFilter[]=[];
  if(filters.status.trim()) governed.push({dimension:"SHIPMENT_STATUS",value:filters.status.trim()});
  return {schema_version:SAVED_VIEW_SCHEMA_VERSION,semantic_version:SAVED_VIEW_SEMANTIC_VERSION,surface:"OPERATIONAL_SHIPMENTS",query_definition:{query_kind:"ROWSET",semantic_version:SAVED_VIEW_SEMANTIC_VERSION,population:"SHIPMENTS",columns:["CUSTOMER","ROUTE","PLANNED_TIME","PROJECT","SOURCE","MILESTONE","OPEN_WORK_ITEMS"],filters:governed,operational_window:(filters.date_from.trim()||filters.date_to.trim())?{...(filters.date_from.trim()?{from:filters.date_from.trim()}:{}),...(filters.date_to.trim()?{to:filters.date_to.trim()}: {})}:undefined,sort:{field:"PLANNED_DEPARTURE",direction:"ASC"},limit:20,metric_keys:[],dimension_keys:[]},presentation:{display_type:"LIST"}};
}
export function applySavedViewDefinition(definition:SavedViewDefinition, current:OperationalShipmentFilters):OperationalShipmentFilters {
  const next={...current,status:"",date_from:"",date_to:"",customer:"",origin:"",destination:"",overdue:""};
  for(const filter of definition.query_definition.filters||[]){
    if(filter.dimension==="SHIPMENT_STATUS"&&typeof filter.value==="string") next.status=filter.value;
    if(filter.dimension==="TIME"&&typeof filter.value==="object"&&!Array.isArray(filter.value)){next.date_from=filter.value.from||"";next.date_to=filter.value.to||"";}
  }
  const window=definition.query_definition.operational_window; if(window){next.date_from=window.from||"";next.date_to=window.to||"";}
  return next;
}
export const isCompatibleSavedView = (view:{definition:SavedViewDefinition;runtime_definition?:SavedViewDefinition;compatibility_state?:string}) => view.compatibility_state !== "INCOMPATIBLE_LEGACY_DEFINITION" && view.compatibility_state !== "UNSUPPORTED_SCHEMA_VERSION" && (view.runtime_definition || view.definition).surface === "OPERATIONAL_SHIPMENTS";
