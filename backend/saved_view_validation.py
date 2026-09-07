"""Server authority for saved-view-definition-v1."""
from __future__ import annotations

from copy import deepcopy
import json

from backend.analytics import SEMANTIC_VERSION
from backend.analytics.registry import DIMENSIONS, METRICS, PARTIAL, READY
from backend.analytics.shipment_rowset import ROWSET_SEMANTIC_VERSION, SHIPMENT_COLUMNS, SHIPMENT_SORTS, normalize_rowset_query

SAVED_VIEW_SCHEMA_VERSION = "saved-view-definition-v1"
SAVED_VIEW_SCHEMA_VERSION_V2 = "saved-view-definition-v2"
SURFACE = "OPERATIONAL_SHIPMENTS"
MAX_JSON = 128 * 1024
MAX_FILTERS = 12
ALLOWED_COLUMNS = set(SHIPMENT_COLUMNS)
ALLOWED_SORT = SHIPMENT_SORTS


class SavedViewValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code, message):
    raise SavedViewValidationError(code, message)


def validate(definition):
    if not isinstance(definition, dict):
        _fail("INVALID_SAVED_VIEW_DEFINITION", "definition must be an object")
    if len(json.dumps(definition, separators=(",", ":")).encode()) > MAX_JSON:
        _fail("DEFINITION_TOO_LARGE", "definition exceeds 128KB")
    if set(definition) != {"schema_version", "semantic_version", "surface", "query_definition", "presentation"}:
        _fail("INVALID_SAVED_VIEW_DEFINITION", "definition fields are not supported")
    if definition.get("schema_version") == SAVED_VIEW_SCHEMA_VERSION_V2:
        return _validate_v2(definition)
    if definition.get("schema_version") != SAVED_VIEW_SCHEMA_VERSION:
        _fail("SAVED_VIEW_SCHEMA_VERSION_UNSUPPORTED", "saved view schema version is unsupported")
    if definition.get("semantic_version") != SEMANTIC_VERSION:
        _fail("SEMANTIC_VERSION_UNSUPPORTED", "analytics semantic version is unsupported")
    if definition.get("surface") != SURFACE:
        _fail("SAVED_VIEW_SURFACE_UNSUPPORTED", "saved view surface is unsupported")
    query = definition.get("query_definition")
    if not isinstance(query, dict) or set(query) - {"metric_keys", "dimension_keys", "filters", "time_dimension", "time_grain", "sort", "limit"}:
        _fail("INVALID_QUERY_DEFINITION", "query_definition is invalid")
    metrics, dimensions, filters = query.get("metric_keys"), query.get("dimension_keys"), query.get("filters", [])
    if metrics != ["SHIPMENT_COUNT"]:
        _fail("INVALID_METRIC_SELECTION", "operational shipment views require SHIPMENT_COUNT")
    if not isinstance(dimensions, list) or any(item not in DIMENSIONS for item in dimensions):
        _fail("UNKNOWN_DIMENSION", "dimension is not governed")
    metric = METRICS["SHIPMENT_COUNT"]
    if metric["readiness"] not in {READY, PARTIAL} or not set(dimensions).issubset(metric["supported_dimensions"]):
        _fail("INCOMPATIBLE_DIMENSION", "dimension is incompatible with shipment views")
    if not isinstance(filters, list) or len(filters) > MAX_FILTERS:
        _fail("INVALID_FILTER_SELECTION", "select at most twelve filters")
    for item in filters:
        if not isinstance(item, dict) or set(item) != {"dimension", "value"} or item["dimension"] not in metric["supported_filters"]:
            _fail("INCOMPATIBLE_FILTER", "filter is not governed for shipment views")
        if item["dimension"] not in {"SHIPMENT_STATUS", "CUSTOMER", "PROJECT", "TIME"}:
            _fail("INCOMPATIBLE_FILTER", "filter cannot be applied by this surface")
    time_dimension, time_grain = query.get("time_dimension"), query.get("time_grain")
    if time_dimension is not None and time_dimension not in metric["supported_time_dimensions"]:
        _fail("UNSUPPORTED_TIME_ROLE", "time role is unsupported")
    if time_grain is not None and time_grain not in metric["supported_time_grains"]:
        _fail("UNSUPPORTED_TIME_GRAIN", "time grain is unsupported")
    if query.get("sort") is not None:
        _fail("INVALID_QUERY_SORT", "presentation owns list sorting")
    limit = query.get("limit", 20)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        _fail("INVALID_LIMIT", "limit must be between 1 and 100")
    presentation = definition.get("presentation")
    if not isinstance(presentation, dict) or set(presentation) != {"columns", "sort", "display_type", "limit"}:
        _fail("INVALID_PRESENTATION", "presentation is invalid")
    columns = presentation.get("columns")
    if not isinstance(columns, list) or not columns or len(columns) != len(set(columns)) or any(item not in ALLOWED_COLUMNS for item in columns):
        _fail("INVALID_COLUMN", "columns must use the operational shipment allowlist")
    sort = presentation.get("sort")
    if not isinstance(sort, dict) or set(sort) != {"field", "direction"} or sort["field"] not in ALLOWED_SORT or sort["direction"] not in {"ASC", "DESC"}:
        _fail("INVALID_SORT", "sort is unsupported")
    if presentation.get("display_type") != "LIST":
        _fail("UNSUPPORTED_DISPLAY_TYPE", "only LIST is supported")
    if presentation.get("limit") != limit:
        _fail("INVALID_LIMIT", "query and presentation limits must match")
    normalized = deepcopy(definition)
    normalized["query_definition"]["filters"] = sorted(filters, key=lambda item: (item["dimension"], json.dumps(item["value"], sort_keys=True)))
    return normalized


def _validate_v2(definition):
    if definition.get("semantic_version") != ROWSET_SEMANTIC_VERSION:
        _fail("SEMANTIC_VERSION_UNSUPPORTED", "v2 Saved Views require analytics-semantic-v2")
    if definition.get("surface") != SURFACE:
        _fail("SAVED_VIEW_SURFACE_UNSUPPORTED", "saved view surface is unsupported")
    if set(definition) != {"schema_version", "semantic_version", "surface", "query_definition", "presentation"}:
        _fail("INVALID_SAVED_VIEW_DEFINITION", "definition fields are not supported")
    try:
        query = normalize_rowset_query(definition.get("query_definition") or {})
    except Exception as exc:
        _fail(getattr(exc, "code", "INVALID_QUERY_DEFINITION"), str(exc))
    presentation = definition.get("presentation")
    if not isinstance(presentation, dict) or set(presentation) != {"display_type"} or presentation.get("display_type") != "LIST":
        _fail("UNSUPPORTED_DISPLAY_TYPE", "v2 Saved Views support LIST presentation only")
    normalized = deepcopy(definition)
    normalized["query_definition"] = {key: value for key, value in query.items() if key not in {"window", "status"}}
    return normalized


def align_v1_to_v2(definition):
    """Side-effect-free correction of v1 UI intent to the ROWSET contract.

    v1's `created` time label was an aggregate-era artifact; Operational
    Shipments date controls always represented the route-envelope window.
    """
    legacy = validate(definition)
    if legacy["schema_version"] != SAVED_VIEW_SCHEMA_VERSION:
        _fail("UNSUPPORTED_SCHEMA_VERSION", "Only saved-view-definition-v1 can be aligned")
    filters, window = [], None
    for item in legacy["query_definition"]["filters"]:
        if item["dimension"] == "SHIPMENT_STATUS": filters.append(item)
        elif item["dimension"] == "TIME": window = item["value"]
        else: _fail("INCOMPATIBLE_LEGACY_DEFINITION", f"Legacy filter {item['dimension']} cannot be aligned")
    return _validate_v2({"schema_version": SAVED_VIEW_SCHEMA_VERSION_V2, "semantic_version": ROWSET_SEMANTIC_VERSION, "surface": SURFACE, "query_definition": {"query_kind": "ROWSET", "semantic_version": ROWSET_SEMANTIC_VERSION, "population": "SHIPMENTS", "columns": legacy["presentation"]["columns"], "filters": filters, **({"operational_window": window} if window else {}), "sort": legacy["presentation"]["sort"], "limit": legacy["presentation"]["limit"]}, "presentation": {"display_type": "LIST"}})


def runtime_definition(definition):
    return align_v1_to_v2(definition) if definition.get("schema_version") == SAVED_VIEW_SCHEMA_VERSION else validate(definition)
