import type { AnalyticsSemanticRegistry } from "@/lib/api";
import { DASHBOARD_SEMANTIC_VERSION, type DashboardDefinition, executableReadiness } from "./types";

export type DefinitionIssue = { widget_id?: string; message: string };
export function validateDashboardDefinition(definition: DashboardDefinition, registry: AnalyticsSemanticRegistry): DefinitionIssue[] {
  const issues: DefinitionIssue[] = [];
  if (![DASHBOARD_SEMANTIC_VERSION, "analytics-semantic-v2"].includes(definition.semantic_version) || registry.semantic_version !== DASHBOARD_SEMANTIC_VERSION) issues.push({ message: "Semantic version is not compatible with this dashboard." });
  const widgetIds = new Set<string>();
  for (const widget of definition.widgets) {
    if (widgetIds.has(widget.widget_id)) issues.push({ widget_id: widget.widget_id, message: "Widget IDs must be unique." });
    widgetIds.add(widget.widget_id);
    if (widget.query.query_kind === "ROWSET") {
      if (widget.query.semantic_version !== "analytics-semantic-v2" || widget.query.population !== "SHIPMENTS" || !widget.query.columns?.length)
        issues.push({ widget_id: widget.widget_id, message: "A row-set widget requires the governed Shipment v2 contract." });
      continue;
    }
    if (!widget.query.metric_keys.length) issues.push({ widget_id: widget.widget_id, message: "A widget requires a metric." });
    for (const metricKey of widget.query.metric_keys) {
      const metric = registry.metrics.find((item) => item.metric_key === metricKey);
      if (!metric) { issues.push({ widget_id: widget.widget_id, message: `Unknown metric: ${metricKey}.` }); continue; }
      if (!executableReadiness(metric.readiness)) issues.push({ widget_id: widget.widget_id, message: `Metric is not executable: ${metricKey}.` });
      for (const dimension of widget.query.dimension_keys) if (!metric.supported_dimensions.includes(dimension)) issues.push({ widget_id: widget.widget_id, message: `${metricKey} cannot use ${dimension}.` });
      for (const filter of widget.query.filters || []) if (!(metric.supported_filters || []).includes(filter.dimension)) issues.push({ widget_id: widget.widget_id, message: `${metricKey} cannot be filtered by ${filter.dimension}.` });
      if (widget.query.time_dimension && !(metric.supported_time_dimensions || []).includes(widget.query.time_dimension)) issues.push({ widget_id: widget.widget_id, message: `${metricKey} has no ${widget.query.time_dimension} time role.` });
      if (widget.query.time_grain && (!(widget.query.dimension_keys.includes("TIME")) || !(metric.supported_time_grains || []).includes(widget.query.time_grain))) issues.push({ widget_id: widget.widget_id, message: `${metricKey} cannot use this time grain.` });
      if (widget.drilldown.enabled && !metric.drilldown_supported) issues.push({ widget_id: widget.widget_id, message: `${metricKey} does not support drilldown.` });
    }
    for (const dimension of widget.query.dimension_keys) if (!registry.dimensions.some((item) => item.dimension_key === dimension)) issues.push({ widget_id: widget.widget_id, message: `Unknown dimension: ${dimension}.` });
    const dimensions = widget.query.dimension_keys;
    if (widget.widget_type === "KPI_CARD" && (widget.query.metric_keys.length !== 1 || dimensions.length !== 0)) issues.push({widget_id:widget.widget_id,message:"KPI card requires one metric and no dimensions."});
    if (widget.widget_type === "TREND" && (widget.query.metric_keys.length !== 1 || dimensions.length !== 1 || dimensions[0] !== "TIME" || !widget.query.time_dimension || !widget.query.time_grain)) issues.push({widget_id:widget.widget_id,message:"Trend requires governed time configuration."});
    if (["BAR","STACKED_BAR","STATUS_DISTRIBUTION"].includes(widget.widget_type) && (widget.query.metric_keys.length !== 1 || dimensions.length !== 1 || dimensions[0] === "TIME")) issues.push({widget_id:widget.widget_id,message:"Chart requires one metric and one categorical dimension."});
    if (![1,2,3,4].includes(widget.layout.col_span) || !Number.isInteger(widget.layout.order)) issues.push({widget_id:widget.widget_id,message:"Widget layout is invalid."});
  }
  const references = definition.sections.flatMap((section) => section.widget_ids);
  if (new Set(references).size !== references.length || references.length !== widgetIds.size || references.some((id) => !widgetIds.has(id))) issues.push({message:"Sections must reference every widget exactly once."});
  for (const filter of definition.global_filters) {
    if (!["TIME","CUSTOMER","PROJECT"].includes(filter.dimension_key) || !filter.applicable_widget_ids.length || filter.applicable_widget_ids.some((id)=>!widgetIds.has(id))) issues.push({message:"Global filter applicability is invalid."});
  }
  return issues;
}
