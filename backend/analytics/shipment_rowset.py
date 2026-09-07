"""Governed Shipment ROWSET vocabulary and projection.

This module is deliberately the only ROWSET-specific consumer of the frozen
Operational Shipment population authority.  It contains no tenant or business
access policy of its own.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from backend.extensions import db
from backend.models import Customer
from backend.operational_models import Milestone, OperationalShipment, OperationalWorkItem, Project, RouteLeg, RoutePlan
from backend.services.operational_service import OperationalError
from backend.services.shipment_population_service import OperationalWindow, operational_shipment_population, route_envelope_columns

ROWSET_SEMANTIC_VERSION = "analytics-semantic-v2"
ROWSET_POPULATION = "SHIPMENTS"
MAX_ROWSET_LIMIT = 100

# This is also imported by Saved View v1 so stable shipment presentation keys
# are owned by one registry, rather than two competing allowlists.
SHIPMENT_COLUMNS = {
    "CUSTOMER": {"business_name": "Customer", "data_type": "string", "sortable": False},
    "ROUTE": {"business_name": "Route", "data_type": "object", "sortable": False},
    "PLANNED_TIME": {"business_name": "Planned time", "data_type": "object", "sortable": True},
    "PROJECT": {"business_name": "Project", "data_type": "string", "sortable": False},
    "SOURCE": {"business_name": "Source", "data_type": "string", "sortable": False},
    "MILESTONE": {"business_name": "Milestone", "data_type": "string", "sortable": False},
    "OPEN_WORK_ITEMS": {"business_name": "Open work items", "data_type": "number", "sortable": False},
    "SHIPMENT_STATUS": {"business_name": "Status", "data_type": "string", "sortable": True},
}
SHIPMENT_SORTS = frozenset({"CREATED_AT", "PLANNED_DEPARTURE", "PLANNED_ARRIVAL", "SHIPMENT_STATUS"})


def _error(code, message):
    raise OperationalError(code, message, 422)


def _parse_time(value, field):
    if value is None:
        return None
    if not isinstance(value, str):
        _error("INVALID_OPERATIONAL_WINDOW", f"{field} must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _error("INVALID_OPERATIONAL_WINDOW", f"{field} must be an ISO-8601 timestamp.")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _error("OFFSET_AWARE_DATETIME_REQUIRED", f"{field} must include a UTC offset.")
    return parsed


def normalize_rowset_query(payload):
    if payload.get("semantic_version") not in (None, ROWSET_SEMANTIC_VERSION):
        _error("UNSUPPORTED_SEMANTIC_VERSION", "ROWSET requires analytics-semantic-v2.")
    if payload.get("population") != ROWSET_POPULATION:
        _error("UNSUPPORTED_ROWSET_POPULATION", "ROWSET population must be SHIPMENTS.")
    columns = payload.get("columns")
    if not isinstance(columns, list) or not columns or len(columns) != len(set(columns)):
        _error("INVALID_ROWSET_COLUMNS", "ROWSET columns must be a non-empty unique list.")
    unknown = set(columns) - set(SHIPMENT_COLUMNS)
    if unknown:
        _error("UNSUPPORTED_SEMANTIC_COLUMN", f"Unsupported Shipment column: {sorted(unknown)[0]}.")
    filters = payload.get("filters", [])
    if not isinstance(filters, list) or len(filters) > 12:
        _error("INVALID_FILTER_SELECTION", "Select at most twelve filters.")
    status = None
    for item in filters:
        if not isinstance(item, dict) or set(item) != {"dimension", "value"}:
            _error("INVALID_FILTER", "ROWSET filters require a governed dimension and value.")
        if item["dimension"] != "SHIPMENT_STATUS":
            _error("INCOMPATIBLE_FILTER", "ROWSET supports only SHIPMENT_STATUS filters in v1.")
        if item["value"] not in {"planned", "in_progress", "completed", "cancelled"}:
            _error("INVALID_SHIPMENT_STATUS", "Shipment status is unsupported.")
        if status is not None:
            _error("INVALID_FILTER", "Only one Shipment status filter is supported.")
        status = item["value"]
    window = payload.get("operational_window")
    if window is not None and (not isinstance(window, dict) or set(window) - {"from", "to"} or not window):
        _error("INVALID_OPERATIONAL_WINDOW", "operational_window requires from and/or to.")
    window = window or {}
    governed_window = OperationalWindow(_parse_time(window.get("from"), "operational_window.from"), _parse_time(window.get("to"), "operational_window.to"))
    sort = payload.get("sort")
    if sort is not None and (not isinstance(sort, dict) or set(sort) != {"field", "direction"} or sort["field"] not in SHIPMENT_SORTS or sort["direction"] not in {"ASC", "DESC"}):
        _error("UNSUPPORTED_ROWSET_SORT", "ROWSET sort is unsupported.")
    try:
        limit = int(payload.get("limit", 20))
    except (TypeError, ValueError):
        _error("INVALID_LIMIT", "limit must be an integer.")
    if isinstance(payload.get("limit", 20), bool) or not 1 <= limit <= MAX_ROWSET_LIMIT:
        _error("INVALID_LIMIT", "ROWSET limit must be between 1 and 100.")
    return {"query_kind": "ROWSET", "semantic_version": ROWSET_SEMANTIC_VERSION, "population": ROWSET_POPULATION, "columns": columns, "filters": filters, "status": status, "operational_window": {k: v.isoformat() for k, v in (("from", governed_window.from_), ("to", governed_window.to)) if v is not None}, "window": governed_window, "sort": sort, "limit": limit}


def _ordered(statement, sort):
    if not sort:
        return statement
    first, final = route_envelope_columns()
    field = {"CREATED_AT": OperationalShipment.created_at, "PLANNED_DEPARTURE": first, "PLANNED_ARRIVAL": final, "SHIPMENT_STATUS": OperationalShipment.lifecycle_status}[sort["field"]]
    direction = field.asc() if sort["direction"] == "ASC" else field.desc()
    return statement.order_by(None).order_by(direction, OperationalShipment.public_id.asc())


def _customer_name(customer):
    if not customer:
        return None
    return customer.company_name or " ".join(filter(None, [customer.first_name, customer.last_name])) or None


def execute_rowset(normalized, user):
    """Execute the one authorized Shipment population and project selected fields."""
    shipments = db.session.scalars(_ordered(operational_shipment_population(user, status=normalized["status"], window=normalized["window"]), normalized["sort"]).limit(normalized["limit"])).all()
    ids = [row.id for row in shipments]
    customers = {row.id: row for row in db.session.scalars(select(Customer).where(Customer.id.in_([x.customer_id for x in shipments if x.customer_id]))).all()}
    projects = {row.id: row.public_id for row in db.session.scalars(select(Project).where(Project.id.in_([x.project_id for x in shipments if x.project_id]))).all()}
    plans = {row.operational_shipment_id: row for row in db.session.scalars(select(RoutePlan).where(RoutePlan.operational_shipment_id.in_(ids), RoutePlan.is_active.is_(True))).all()}
    plan_ids = [row.id for row in plans.values()]
    legs = {}
    if plan_ids:
        for leg in db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id.in_(plan_ids)).order_by(RouteLeg.sequence_number.asc())).all():
            legs.setdefault(leg.route_plan_id, []).append(leg)
    milestones = {}
    if ids:
        for row in db.session.scalars(select(Milestone).where(Milestone.operational_shipment_id.in_(ids)).order_by(Milestone.planned_at.asc(), Milestone.id.asc())).all():
            milestones.setdefault(row.operational_shipment_id, row)
    work_counts = dict(db.session.execute(select(OperationalWorkItem.operational_shipment_id, func.count()).where(OperationalWorkItem.operational_shipment_id.in_(ids), OperationalWorkItem.status == "open").group_by(OperationalWorkItem.operational_shipment_id)).all()) if ids else {}
    rows = []
    for shipment in shipments:
        shipment_legs = legs.get(plans.get(shipment.id).id, []) if shipment.id in plans else []
        first, final = (shipment_legs[0], shipment_legs[-1]) if shipment_legs else (None, None)
        values = {"shipment_public_id": shipment.public_id}
        for key in normalized["columns"]:
            if key == "CUSTOMER": values[key] = _customer_name(customers.get(shipment.customer_id))
            elif key == "ROUTE": values[key] = {"origin": (first.origin_snapshot or {}).get("display_name") if first else None, "destination": (final.destination_snapshot or {}).get("display_name") if final else None}
            elif key == "PLANNED_TIME": values[key] = {"departure": first.planned_departure.isoformat() if first else None, "arrival": final.planned_arrival.isoformat() if final else None}
            elif key == "PROJECT": values[key] = projects.get(shipment.project_id)
            elif key == "SOURCE": values[key] = shipment.source_type
            elif key == "MILESTONE": values[key] = getattr(milestones.get(shipment.id), "milestone_type", None)
            elif key == "OPEN_WORK_ITEMS": values[key] = work_counts.get(shipment.id, 0)
            elif key == "SHIPMENT_STATUS": values[key] = shipment.lifecycle_status
        rows.append(values)
    return {"result_kind": "ROWSET", "semantic_version": ROWSET_SEMANTIC_VERSION, "normalized_query": {k: v for k, v in normalized.items() if k not in {"window", "status"}}, "query": {k: v for k, v in normalized.items() if k not in {"window", "status"}}, "columns": [{"key": key, **SHIPMENT_COLUMNS[key]} for key in normalized["columns"]], "rows": rows, "returned_row_count": len(rows), "coverage": [], "warnings": [], "pagination": {"limit": normalized["limit"], "next_cursor": None}, "execution": {"read_only": True, "organization_scoped": True, "business_access_scoped": True}}
