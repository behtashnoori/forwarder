import type { AnalyticsFilter } from "@/lib/api";
import { SAVED_VIEW_SCHEMA_VERSION, SAVED_VIEW_SEMANTIC_VERSION, type SavedViewDefinition } from "./types";

export type OperationalShipmentFilters = {status:string;customer:string;origin:string;destination:string;overdue:string;date_from:string;date_to:string};
export const unsupportedSavedViewFilters = (filters:OperationalShipmentFilters) => ["customer","origin","destination","overdue"].filter(key => filters[key as keyof OperationalShipmentFilters].trim());
export function toSavedViewDefinition(filters:OperationalShipmentFilters):SavedViewDefinition {
  const governed:AnalyticsFilter[]=[];
  if(filters.status.trim()) governed.push({dimension:"SHIPMENT_STATUS",value:filters.status.trim()});
  if(filters.date_from.trim()||filters.date_to.trim()) governed.push({dimension:"TIME",value:{...(filters.date_from.trim()?{from:filters.date_from.trim()}:{}),...(filters.date_to.trim()?{to:filters.date_to.trim()}: {})}});
  return {schema_version:SAVED_VIEW_SCHEMA_VERSION,semantic_version:SAVED_VIEW_SEMANTIC_VERSION,surface:"OPERATIONAL_SHIPMENTS",query_definition:{metric_keys:["SHIPMENT_COUNT"],dimension_keys:[],filters:governed,time_dimension:"created",limit:20},presentation:{columns:["CUSTOMER","ROUTE","PLANNED_TIME","PROJECT","SOURCE","MILESTONE","OPEN_WORK_ITEMS"],sort:{field:"PLANNED_DEPARTURE",direction:"ASC"},display_type:"LIST",limit:20}};
}
export function applySavedViewDefinition(definition:SavedViewDefinition, current:OperationalShipmentFilters):OperationalShipmentFilters {
  const next={...current,status:"",date_from:"",date_to:"",customer:"",origin:"",destination:"",overdue:""};
  for(const filter of definition.query_definition.filters||[]){
    if(filter.dimension==="SHIPMENT_STATUS"&&typeof filter.value==="string") next.status=filter.value;
    if(filter.dimension==="TIME"&&typeof filter.value==="object"&&!Array.isArray(filter.value)){next.date_from=filter.value.from||"";next.date_to=filter.value.to||"";}
  }
  return next;
}
export const isCompatibleSavedView = (view:{semantic_version:string;saved_view_schema_version:string;definition:SavedViewDefinition}) => view.semantic_version===SAVED_VIEW_SEMANTIC_VERSION&&view.saved_view_schema_version===SAVED_VIEW_SCHEMA_VERSION&&view.definition.surface==="OPERATIONAL_SHIPMENTS";
