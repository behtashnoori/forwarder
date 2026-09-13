"""Machine-readable v1 analytics vocabulary; never client-editable."""
from backend.analytics import SEMANTIC_VERSION

READY, PARTIAL, NOT_READY, BUSINESS_DEFINITION_REQUIRED = "READY", "PARTIAL", "NOT_READY", "BUSINESS_DEFINITION_REQUIRED"

def _metric(key, grain, unit="count", readiness=READY, dimensions=(), coverage=(), drilldown="shipment_list", description="", time_dimensions=("created",), time_grains=("day", "week", "month", "quarter", "year")):
    return {"metric_key": key, "business_name": key.replace("_", " ").title(), "description": description,
            "grain": grain, "aggregation": "sum" if unit != "count" else "count_distinct",
            "unit": unit, "authoritative_source": "Step 3 operational projection", "null_policy": "NULL_UNKNOWN",
            "revision_policy": "ACTIVE_ROUTE_OR_LINEAGE_ROOT", "correction_policy": "EFFECTIVE_OCCURRENCE",
            "supported_dimensions": list(dimensions), "supported_filters": [d for d in dimensions if d in {"CUSTOMER", "PROJECT", "SHIPMENT_STATUS", "TRANSPORT_MODE", "LEG_STATUS", "ORIGIN_COUNTRY", "ORIGIN_PROVINCE", "ORIGIN_CITY", "DESTINATION_COUNTRY", "DESTINATION_PROVINCE", "DESTINATION_CITY", "ORIGIN_FACILITY", "DESTINATION_FACILITY"}] + ["TIME"],
            "supported_time_dimensions": list(time_dimensions), "supported_time_grains": list(time_grains),
            "drilldown_type": drilldown, "drilldown_supported": drilldown is not None, "readiness": readiness, "coverage_dependencies": list(coverage),
            "semantic_version": SEMANTIC_VERSION}

_shipment_dims = ("TIME", "CUSTOMER", "PROJECT", "SHIPMENT_STATUS")
_leg_dims = ("TIME", "CUSTOMER", "PROJECT", "TRANSPORT_MODE", "LEG_STATUS", "ORIGIN_COUNTRY", "ORIGIN_PROVINCE", "ORIGIN_CITY", "DESTINATION_COUNTRY", "DESTINATION_PROVINCE", "DESTINATION_CITY", "ORIGIN_FACILITY", "DESTINATION_FACILITY", "CARRIER")
METRICS = {
    "SHIPMENT_COUNT": _metric("SHIPMENT_COUNT", "FACT_SHIPMENT", dimensions=_shipment_dims),
    "ACTIVE_SHIPMENT_COUNT": _metric("ACTIVE_SHIPMENT_COUNT", "FACT_SHIPMENT", dimensions=_shipment_dims),
    "PLANNED_SHIPMENT_COUNT": _metric("PLANNED_SHIPMENT_COUNT", "FACT_SHIPMENT", dimensions=_shipment_dims),
    "IN_PROGRESS_SHIPMENT_COUNT": _metric("IN_PROGRESS_SHIPMENT_COUNT", "FACT_SHIPMENT", dimensions=_shipment_dims),
    "COMPLETED_SHIPMENT_COUNT": _metric("COMPLETED_SHIPMENT_COUNT", "FACT_SHIPMENT", dimensions=_shipment_dims),
    "CANCELLED_SHIPMENT_COUNT": _metric("CANCELLED_SHIPMENT_COUNT", "FACT_SHIPMENT", dimensions=_shipment_dims),
    "ROUTE_LEG_COUNT": _metric("ROUTE_LEG_COUNT", "FACT_ROUTE_LEG_CURRENT", dimensions=_leg_dims, coverage=("LEGS_WITH_ORIGIN_FACILITY_COVERAGE", "LEGS_WITH_DESTINATION_FACILITY_COVERAGE"), drilldown="route_leg_list"),
    "COMPLETED_LEG_COUNT": _metric("COMPLETED_LEG_COUNT", "FACT_ROUTE_LEG_CURRENT", dimensions=_leg_dims, drilldown="route_leg_list"),
    "RAW_EVENT_COUNT": _metric("RAW_EVENT_COUNT", "FACT_MILESTONE_EVENT", dimensions=("TIME", "CUSTOMER", "PROJECT", "OPERATOR"), drilldown="occurrence_history", time_dimensions=("recorded", "effective_occurrence")),
    "EFFECTIVE_BUSINESS_OCCURRENCE_COUNT": _metric("EFFECTIVE_BUSINESS_OCCURRENCE_COUNT", "FACT_OPERATIONAL_OCCURRENCE", dimensions=("TIME", "CUSTOMER", "PROJECT", "OPERATOR"), drilldown="occurrence_history", time_dimensions=("effective_occurrence",)),
    "LEG_TRANSIT_TIME": _metric("LEG_TRANSIT_TIME", "FACT_ROUTE_LEG_CURRENT", "seconds", dimensions=_leg_dims, coverage=("COMPLETED_LEGS_WITH_ACTUAL_TIMES_COVERAGE",), drilldown="route_leg_list"),
    "DWELL_TIME": _metric("DWELL_TIME", "FACT_CHECKPOINT", "seconds", dimensions=("TIME", "CUSTOMER", "PROJECT", "ORIGIN_COUNTRY", "DESTINATION_COUNTRY"), drilldown="route_leg_list"),
    "REPORTED_DELAY_DURATION": _metric("REPORTED_DELAY_DURATION", "FACT_OPERATIONAL_DELAY", "seconds", dimensions=("TIME", "CUSTOMER", "PROJECT", "OPERATOR"), drilldown="delay_list", time_dimensions=("started",)),
    "DELAY_CASE_COUNT": _metric("DELAY_CASE_COUNT", "FACT_OPERATIONAL_DELAY", dimensions=("TIME", "CUSTOMER", "PROJECT", "OPERATOR"), drilldown="delay_list", time_dimensions=("started",)),
    "EXCEPTION_COUNT": _metric("EXCEPTION_COUNT", "FACT_OPERATIONAL_EXCEPTION", dimensions=("TIME", "CUSTOMER", "PROJECT", "OPERATOR"), drilldown="exception_list", time_dimensions=("occurred",)),
    "OPEN_EXCEPTION_COUNT": _metric("OPEN_EXCEPTION_COUNT", "FACT_OPERATIONAL_EXCEPTION", dimensions=("TIME", "CUSTOMER", "PROJECT"), drilldown="exception_list", time_dimensions=("occurred",)),
    "OPEN_WORK_ITEM_COUNT": _metric("OPEN_WORK_ITEM_COUNT", "FACT_WORK_ITEM", dimensions=("TIME", "CUSTOMER", "PROJECT", "OPERATOR"), drilldown="work_item_list", time_dimensions=("detected",)),
    "REPLAN_COUNT": _metric("REPLAN_COUNT", "FACT_ROUTE_PLAN_REVISION", dimensions=("TIME", "CUSTOMER", "PROJECT"), drilldown="shipment_list"),
    "DOCUMENT_REQUIREMENT_COUNT": _metric("DOCUMENT_REQUIREMENT_COUNT", "FACT_DOCUMENT_READINESS", dimensions=("TIME", "CUSTOMER", "PROJECT", "DOCUMENT_TYPE"), readiness=PARTIAL, coverage=("DOCUMENT_READINESS_SCOPE_COVERAGE",), drilldown="document_requirement_list"),
    "DOCUMENT_READINESS_COVERAGE": _metric("DOCUMENT_READINESS_COVERAGE", "FACT_DOCUMENT_READINESS", "percent", dimensions=("TIME", "CUSTOMER", "PROJECT"), readiness=PARTIAL, coverage=("DOCUMENT_READINESS_SCOPE_COVERAGE",), drilldown="document_requirement_list"),
}
for key in ("LEAD_TIME", "SHIPMENT_TRANSIT_TIME", "ON_TIME_SHIPMENT_PERCENT", "ON_TIME_LEG_PERCENT", "ON_TIME_CHECKPOINT_PERCENT", "SCHEDULE_DELAY_DURATION", "STALE_SHIPMENT_COUNT", "CURRENT_STAGE_AGE", "NEEDS_ATTENTION_COUNT"):
    METRICS[key] = _metric(key, "UNDEFINED", readiness=BUSINESS_DEFINITION_REQUIRED, description="Business definition is not governed; this metric cannot execute.")

def _dimension(key, entity, identity, history, readiness=READY, nullable=True, coverage=None, metrics=()):
    return {"dimension_key": key, "business_name": key.replace("_", " ").title(), "entity_grain": entity,
            "identity_source": identity, "history_policy": history, "filter_type": "enum" if key.endswith("STATUS") else "identity",
            "nullable": nullable, "coverage_metric": coverage, "readiness": readiness, "allowed_metrics": list(metrics), "semantic_version": SEMANTIC_VERSION}

DIMENSIONS = {
    "TIME": _dimension("TIME", "role_playing", "UTC calendar role", "transaction timestamp", False),
    "CUSTOMER": _dimension("CUSTOMER", "FACT_SHIPMENT", "customer tenant identity", "CURRENT_MASTER", True),
    "PROJECT": _dimension("PROJECT", "FACT_SHIPMENT", "Project.public_id", "CURRENT_MASTER", True, "SHIPMENTS_WITH_PROJECT_COVERAGE"),
    "COMMODITY": _dimension("COMMODITY", "FACT_SHIPMENT_CARGO", "CargoCatalogItem.public_id", "SHIPMENT_LINE_SNAPSHOT", True, "CARGO_CATALOG_LINK_COVERAGE"),
    "CARGO_TYPE": _dimension("CARGO_TYPE", "FACT_SHIPMENT_CARGO", "ShipmentCargoItem snapshot", "SHIPMENT_LINE_SNAPSHOT", False),
    "ORIGIN_COUNTRY": _dimension("ORIGIN_COUNTRY", "FACT_ROUTE_LEG_CURRENT", "RouteLeg origin snapshot", "ROUTE_ENDPOINT_SNAPSHOT"),
    "ORIGIN_PROVINCE": _dimension("ORIGIN_PROVINCE", "FACT_ROUTE_LEG_CURRENT", "RouteLeg origin snapshot", "ROUTE_ENDPOINT_SNAPSHOT"),
    "ORIGIN_CITY": _dimension("ORIGIN_CITY", "FACT_ROUTE_LEG_CURRENT", "RouteLeg origin snapshot", "ROUTE_ENDPOINT_SNAPSHOT"),
    "DESTINATION_COUNTRY": _dimension("DESTINATION_COUNTRY", "FACT_ROUTE_LEG_CURRENT", "RouteLeg destination snapshot", "ROUTE_ENDPOINT_SNAPSHOT"),
    "DESTINATION_PROVINCE": _dimension("DESTINATION_PROVINCE", "FACT_ROUTE_LEG_CURRENT", "RouteLeg destination snapshot", "ROUTE_ENDPOINT_SNAPSHOT"),
    "DESTINATION_CITY": _dimension("DESTINATION_CITY", "FACT_ROUTE_LEG_CURRENT", "RouteLeg destination snapshot", "ROUTE_ENDPOINT_SNAPSHOT"),
    "ORIGIN_FACILITY": _dimension("ORIGIN_FACILITY", "FACT_ROUTE_LEG_CURRENT", "LogisticsPoint.public_id", "ROUTE_ENDPOINT_SNAPSHOT", True, "LEGS_WITH_ORIGIN_FACILITY_COVERAGE"),
    "DESTINATION_FACILITY": _dimension("DESTINATION_FACILITY", "FACT_ROUTE_LEG_CURRENT", "LogisticsPoint.public_id", "ROUTE_ENDPOINT_SNAPSHOT", True, "LEGS_WITH_DESTINATION_FACILITY_COVERAGE"),
    "TRANSPORT_MODE": _dimension("TRANSPORT_MODE", "FACT_ROUTE_LEG_CURRENT", "RouteLeg.transport_mode", "TRANSACTION_VALUE", False),
    "SHIPMENT_STATUS": _dimension("SHIPMENT_STATUS", "FACT_SHIPMENT", "OperationalShipment.lifecycle_status", "OFFICIAL_PROJECTION", False),
    "LEG_STATUS": _dimension("LEG_STATUS", "FACT_ROUTE_LEG_CURRENT", "RouteLeg.status", "OFFICIAL_PROJECTION", False),
    "OPERATOR": _dimension("OPERATOR", "event/case", "actor user identity", "CURRENT_MASTER", True),
    "DOCUMENT_TYPE": _dimension("DOCUMENT_TYPE", "FACT_DOCUMENT_READINESS", "DocumentDefinition.public_id", "CURRENT_MASTER", False),
    "CARRIER": _dimension("CARRIER", "FACT_ROUTE_LEG_CURRENT", "carrier_reference descriptive text", "TRANSACTION_VALUE", PARTIAL, True, "LEGS_WITH_CARRIER_REFERENCE_COVERAGE"),
    "EQUIPMENT": _dimension("EQUIPMENT", "FACT_CARGO_TRANSPORT_ALLOCATION", "ShipmentTransportUnit", "CURRENT_ROW", PARTIAL),
    "SERVICE": _dimension("SERVICE", "unavailable", "none", "NOT_AVAILABLE", NOT_READY),
}

COVERAGE = {
 "SHIPMENTS_WITH_PROJECT_COVERAGE": "shipments with project_id / all shipments", "SHIPMENTS_WITH_CARGO_COVERAGE": "shipments with at least one cargo line / all shipments",
 "CARGO_CATALOG_LINK_COVERAGE": "cargo lines with catalog_item_id / all cargo lines", "LEGS_WITH_ORIGIN_FACILITY_COVERAGE": "active legs with origin LogisticsPoint / active legs",
 "LEGS_WITH_DESTINATION_FACILITY_COVERAGE": "active legs with destination LogisticsPoint / active legs", "LEGS_WITH_CARRIER_REFERENCE_COVERAGE": "active legs with non-empty carrier reference / active legs",
 "COMPLETED_LEGS_WITH_ACTUAL_TIMES_COVERAGE": "completed active legs with actual departure and arrival / completed active legs", "DOCUMENT_READINESS_SCOPE_COVERAGE": "shipments with active document readiness requirements / all shipments",
 "CARGO_TRANSPORT_ALLOCATION_COVERAGE": "cargo lines allocated to a transport unit / all cargo lines"}

RELATIONSHIPS = [{"from": "SHIPMENT", "to": "ROUTE_PLAN", "cardinality": "ONE_TO_MANY"}, {"from": "ROUTE_LEG", "to": "ROUTE_LEG", "cardinality": "OPTIONAL_LINEAGE"}, {"from": "SHIPMENT", "to": "CARGO", "cardinality": "ONE_TO_MANY"}, {"from": "CARGO", "to": "TRANSPORT_UNIT", "cardinality": "MANY_TO_MANY"}, {"from": "ROUTE_LEG", "to": "COMMODITY", "cardinality": "NOT_SUPPORTED"}]

def discovery():
    return {"semantic_version": SEMANTIC_VERSION, "metrics": list(METRICS.values()), "dimensions": list(DIMENSIONS.values()), "relationships": RELATIONSHIPS, "coverage": COVERAGE,
            "null_semantics": ["VALUE", "ZERO", "NULL_UNKNOWN", "NOT_APPLICABLE", "NOT_READY", "OUT_OF_SCOPE"],
            "compatibility": {m: {"dimensions": v["supported_dimensions"], "filters": v["supported_filters"], "time_dimensions": v["supported_time_dimensions"], "time_grains": v["supported_time_grains"]} for m, v in METRICS.items()}}
