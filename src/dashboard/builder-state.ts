import type { AnalyticsSemanticRegistry } from "@/lib/api";
import type { DashboardDefinition, WidgetDefinition, WidgetType } from "./types";
import { validateDashboardDefinition, type DefinitionIssue } from "./validator";

export type BuilderStatus = "READY_CLEAN" | "READY_DIRTY_VALID" | "READY_DIRTY_INVALID" | "SAVING" | "SAVE_ERROR" | "CONFLICT";
export interface BuilderDraft { name:string; description:string; definition:DashboardDefinition }
export interface BuilderState { persisted:BuilderDraft; draft:BuilderDraft; selectedWidgetId:string|null; status:BuilderStatus; issues:DefinitionIssue[]; message?:string }
export type BuilderAction =
  | {type:"CHANGE_META"; field:"name"|"description"; value:string; registry:AnalyticsSemanticRegistry}
  | {type:"REPLACE_DEFINITION"; definition:DashboardDefinition; registry:AnalyticsSemanticRegistry}
  | {type:"SELECT_WIDGET"; widgetId:string|null}
  | {type:"SAVING"}
  | {type:"SAVED"; persisted:BuilderDraft}
  | {type:"SAVE_ERROR"; message:string}
  | {type:"CONFLICT"; message:string};

const canonical = (value:BuilderDraft) => JSON.stringify(value);
export const assess = (persisted:BuilderDraft, draft:BuilderDraft, registry:AnalyticsSemanticRegistry) => {
  const issues = validateDashboardDefinition(draft.definition, registry);
  if (!draft.name.trim() || draft.name.length > 120) issues.unshift({message:"نام داشبورد باید بین ۱ تا ۱۲۰ نویسه باشد."});
  if (draft.description.length > 1000) issues.unshift({message:"توضیح داشبورد بیش از حد طولانی است."});
  const dirty = canonical(persisted) !== canonical(draft);
  return {issues, status:(!dirty ? "READY_CLEAN" : issues.length ? "READY_DIRTY_INVALID" : "READY_DIRTY_VALID") as BuilderStatus};
};
export function builderReducer(state:BuilderState, action:BuilderAction):BuilderState {
  if (action.type === "SELECT_WIDGET") return {...state,selectedWidgetId:action.widgetId};
  if (action.type === "SAVING") return {...state,status:"SAVING",message:undefined};
  if (action.type === "SAVED") return {...state,persisted:action.persisted,draft:action.persisted,status:"READY_CLEAN",issues:[],message:"تغییرات ذخیره شد."};
  if (action.type === "SAVE_ERROR") return {...state,status:"SAVE_ERROR",message:action.message};
  if (action.type === "CONFLICT") return {...state,status:"CONFLICT",message:action.message};
  const draft = action.type === "CHANGE_META" ? {...state.draft,[action.field]:action.value} : {...state.draft,definition:action.definition};
  return {...state,draft,...assess(state.persisted,draft,action.registry),message:undefined};
}

export const widgetShape = (type:WidgetType) => ({needsDimension:type !== "KPI_CARD", time:type === "TREND"});
export function newWidget(type:WidgetType, metricKey:string, metricLabel:string, dimension?:string, timeDimension?:string, timeGrain?:WidgetDefinition["query"]["time_grain"]):WidgetDefinition {
  const widgetId = globalThis.crypto?.randomUUID?.() ?? `widget-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return {widget_id:widgetId,widget_type:type,title:metricLabel,query:{metric_keys:[metricKey],dimension_keys:dimension?[dimension]:[],...(timeDimension?{time_dimension:timeDimension}:{}),...(timeGrain?{time_grain:timeGrain}:{}),limit:type === "KPI_CARD"?undefined:20},coverage_policy:"SHOW_WHEN_PARTIAL",warnings_policy:"SHOW_WHEN_PRESENT",drilldown:{enabled:false},layout:{col_span:type === "KPI_CARD"?1:2,order:0},required_permissions:["operational_shipment.read"]};
}

export function normalizeWidgetOrder(definition:DashboardDefinition, ids:string[]):DashboardDefinition {
  const order = new Map(ids.map((id,index)=>[id,index+1]));
  return {...definition,widgets:definition.widgets.map((widget)=>({...widget,layout:{...widget.layout,order:order.get(widget.widget_id) ?? widget.layout.order}})),sections:definition.sections.map((section,index)=>index===0?{...section,widget_ids:ids}:section)};
}
