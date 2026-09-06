"""Server authority for dashboard-definition-v1.  It mirrors, but does not trust, the UI validator."""
import json
from backend.analytics import SEMANTIC_VERSION
from backend.analytics.registry import METRICS, DIMENSIONS, READY, PARTIAL

class DashboardValidationError(ValueError):
    """A controlled validation failure that is safe to expose to API clients."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

DASHBOARD_SCHEMA_VERSION = "dashboard-definition-v1"
MAX_WIDGETS, MAX_SECTIONS, MAX_JSON = 30, 10, 256 * 1024
WIDGETS = {"KPI_CARD", "TREND", "BAR", "STACKED_BAR", "STATUS_DISTRIBUTION", "TABLE", "ATTENTION_LIST"}
def fail(code, message): raise DashboardValidationError(code, message)
def validate(definition):
    if not isinstance(definition, dict): fail("INVALID_DASHBOARD_DEFINITION", "definition must be an object")
    if len(json.dumps(definition, separators=(",", ":")).encode()) > MAX_JSON: fail("DEFINITION_TOO_LARGE", "definition exceeds 256KB")
    if definition.get("semantic_version") != SEMANTIC_VERSION: fail("SEMANTIC_VERSION_UNSUPPORTED", "analytics semantic version is unsupported")
    if definition.get("dashboard_schema_version") not in (None, DASHBOARD_SCHEMA_VERSION): fail("DASHBOARD_SCHEMA_VERSION_UNSUPPORTED", "dashboard schema version is unsupported")
    widgets, sections = definition.get("widgets"), definition.get("sections")
    if not isinstance(widgets, list) or not widgets or len(widgets) > MAX_WIDGETS: fail("INVALID_WIDGETS", "select 1-30 widgets")
    if not isinstance(sections, list) or len(sections) > MAX_SECTIONS: fail("INVALID_SECTIONS", "select at most 10 sections")
    ids=set()
    for w in widgets:
        if not isinstance(w, dict) or w.get("widget_id") in ids or w.get("widget_type") not in WIDGETS: fail("INVALID_WIDGET", "widget shape is invalid")
        ids.add(w["widget_id"]); q=w.get("query", {}); metrics=q.get("metric_keys", []); dims=q.get("dimension_keys", [])
        if not isinstance(metrics,list) or not metrics: fail("INVALID_METRIC_SELECTION", "widget requires a metric")
        if len(str(w.get("title", ""))) > 120: fail("STRING_LIMIT", "widget title exceeds 120 characters")
        for m in metrics:
            d=METRICS.get(m)
            if not d: fail("UNKNOWN_METRIC", m)
            if d["readiness"] not in {READY, PARTIAL}: fail("METRIC_NOT_EXECUTABLE", m)
            if not set(dims).issubset(d["supported_dimensions"]): fail("INCOMPATIBLE_DIMENSION", m)
            for f in q.get("filters", []):
                if not isinstance(f,dict) or f.get("dimension") not in d["supported_filters"]: fail("INCOMPATIBLE_FILTER", m)
            if q.get("time_dimension") and q["time_dimension"] not in d["supported_time_dimensions"]: fail("UNSUPPORTED_TIME_ROLE", m)
            if q.get("time_grain") and ("TIME" not in dims or q["time_grain"] not in d["supported_time_grains"]): fail("UNSUPPORTED_TIME_GRAIN", m)
            if w.get("drilldown",{}).get("enabled") and not d["drilldown_supported"]: fail("DRILLDOWN_NOT_SUPPORTED",m)
        if any(x not in DIMENSIONS for x in dims): fail("UNKNOWN_DIMENSION", "unknown dimension")
        widget_type=w["widget_type"]
        if widget_type == "KPI_CARD" and (len(metrics) != 1 or dims): fail("INVALID_WIDGET_SHAPE", "KPI_CARD requires one metric and no dimensions")
        if widget_type == "TREND" and (len(metrics) != 1 or dims != ["TIME"] or not q.get("time_dimension") or not q.get("time_grain")): fail("INVALID_WIDGET_SHAPE", "TREND requires one metric and governed time configuration")
        if widget_type in {"BAR", "STATUS_DISTRIBUTION", "STACKED_BAR"} and (len(metrics) != 1 or len(dims) != 1 or dims[0] == "TIME"): fail("INVALID_WIDGET_SHAPE", "chart requires one metric and one categorical dimension")
        layout=w.get("layout",{})
        if layout.get("col_span") not in {1,2,3,4} or not isinstance(layout.get("order"),int): fail("INVALID_WIDGET_LAYOUT", "widget layout is invalid")
    referenced=[]
    for section in sections:
        if not isinstance(section,dict) or not isinstance(section.get("widget_ids"),list): fail("INVALID_SECTION", "section shape is invalid")
        referenced.extend(section["widget_ids"])
    if len(referenced) != len(set(referenced)) or set(referenced) != ids: fail("INVALID_SECTION_WIDGETS", "sections must reference every widget exactly once")
    for global_filter in definition.get("global_filters",[]):
        if not isinstance(global_filter,dict) or global_filter.get("dimension_key") not in {"TIME","CUSTOMER","PROJECT"}: fail("INVALID_GLOBAL_FILTER", "global filter is not governed")
        applicable=global_filter.get("applicable_widget_ids")
        if not isinstance(applicable,list) or not applicable or not set(applicable).issubset(ids): fail("INVALID_GLOBAL_FILTER", "global filter applicability is invalid")
    return definition
