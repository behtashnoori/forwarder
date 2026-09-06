import type { AnalyticsFilter, AnalyticsReadiness } from "@/lib/api";

export const DASHBOARD_SEMANTIC_VERSION = "analytics-semantic-v1" as const;
export type WidgetType = "KPI_CARD" | "TREND" | "BAR" | "STACKED_BAR" | "STATUS_DISTRIBUTION" | "TABLE" | "ATTENTION_LIST";
export type CoveragePolicy = "SHOW_ALWAYS" | "SHOW_WHEN_PARTIAL" | "REQUIRE_COMPLETE";
export type WarningPolicy = "SHOW_ALWAYS" | "SHOW_WHEN_PRESENT";
export type RefreshPolicy = { mode: "ON_PAGE_LOAD"; interval_ms?: never } | { mode: "PERIODIC"; interval_ms: number };
export type DashboardSemanticState = "LOADING" | "VALUE" | "EMPTY_ZERO" | "UNKNOWN" | "NOT_APPLICABLE" | "NOT_READY" | "PARTIAL_COVERAGE" | "INCOMPATIBLE_FILTER" | "ERROR" | "OUT_OF_SCOPE" | "STALE_VALUE";

export interface SemanticQueryDefinition {
  metric_keys: string[];
  dimension_keys: string[];
  filters?: AnalyticsFilter[];
  time_dimension?: string;
  time_grain?: "day" | "week" | "month" | "quarter" | "year";
  sort?: "ASC" | "DESC";
  limit?: number;
}
export interface WidgetLayout { col_span: 1 | 2 | 3 | 4; order: number; }
export interface DrilldownDefinition { enabled: boolean; allow_segment?: boolean; }
export interface WidgetDefinition {
  widget_id: string;
  widget_type: WidgetType;
  title: string;
  description?: string;
  query: SemanticQueryDefinition;
  coverage_policy: CoveragePolicy;
  warnings_policy: WarningPolicy;
  drilldown: DrilldownDefinition;
  layout: WidgetLayout;
  required_permissions: string[];
}
export interface DashboardSection { section_id: string; title: string; description?: string; order: number; widget_ids: string[]; }
export interface GlobalFilterDefinition { dimension_key: string; label: string; applicable_widget_ids: string[]; }
export interface DashboardDefinition {
  dashboard_id: string;
  name: string;
  description: string;
  dashboard_type: "SYSTEM";
  semantic_version: typeof DASHBOARD_SEMANTIC_VERSION;
  global_filters: GlobalFilterDefinition[];
  sections: DashboardSection[];
  widgets: WidgetDefinition[];
  refresh_policy: RefreshPolicy;
}
export const executableReadiness = (value: AnalyticsReadiness) => value === "READY" || value === "PARTIAL";
