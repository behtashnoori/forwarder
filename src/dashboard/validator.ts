import type { AnalyticsSemanticRegistry } from "@/lib/api";
import { DASHBOARD_SEMANTIC_VERSION, type DashboardDefinition, executableReadiness } from "./types";

export type DefinitionIssue = { widget_id?: string; message: string };
export function validateDashboardDefinition(definition: DashboardDefinition, registry: AnalyticsSemanticRegistry): DefinitionIssue[] {
  const issues: DefinitionIssue[] = [];
  if (definition.semantic_version !== DASHBOARD_SEMANTIC_VERSION || registry.semantic_version !== definition.semantic_version) issues.push({ message: "Semantic version is not compatible with this dashboard." });
  const widgetIds = new Set<string>();
  for (const widget of definition.widgets) {
    if (widgetIds.has(widget.widget_id)) issues.push({ widget_id: widget.widget_id, message: "Widget IDs must be unique." });
    widgetIds.add(widget.widget_id);
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
  }
  return issues;
}
