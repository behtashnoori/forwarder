"""Controlled analytics query execution over authoritative operational projections."""
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy import select

from backend.analytics import SEMANTIC_VERSION
from backend.analytics.registry import COVERAGE, DIMENSIONS, METRICS, discovery, READY, PARTIAL
from backend.cargo_models import ShipmentCargoItem, ShipmentCargoTransportAllocation
from backend.extensions import db
from backend.mdpm_models import OperationalDocumentRequirement
from backend.models import Customer
from backend.operational_models import (Milestone, MilestoneEvent, OperationalCheckpoint, OperationalDelay,
    OperationalException, OperationalShipment, OperationalWorkItem, Project, RouteLeg, RoutePlan)
from backend.services import occurrence_projection_service as authority
from backend.services.operational_service import OperationalError, organization_for_user, require_permission
from backend.services.assigned_work_authorization import assigned_shipment_scope

MAX_METRICS, MAX_DIMENSIONS, MAX_FILTERS, MAX_LIMIT = 10, 4, 12, 200

def _error(code, message, status=422):
    raise OperationalError(code, message, status)

def semantic_registry(user):
    require_permission(user, "operational_shipment.read")
    return discovery()

def _check_request(payload):
    if not isinstance(payload, dict): _error("INVALID_ANALYTICS_QUERY", "Query must be an object.")
    metrics, dimensions, filters = payload.get("metrics"), payload.get("dimensions", []), payload.get("filters", [])
    if not isinstance(metrics, list) or not metrics or len(metrics) > MAX_METRICS: _error("INVALID_METRIC_SELECTION", "Select 1–10 metrics.")
    if not isinstance(dimensions, list) or len(dimensions) > MAX_DIMENSIONS: _error("INVALID_DIMENSION_SELECTION", "Select at most four dimensions.")
    if not isinstance(filters, list) or len(filters) > MAX_FILTERS: _error("INVALID_FILTER_SELECTION", "Select at most twelve filters.")
    for key in metrics:
        definition = METRICS.get(key)
        if not definition: _error("UNKNOWN_METRIC", f"Unknown metric: {key}")
        if definition["readiness"] not in {READY, PARTIAL}: _error("METRIC_NOT_EXECUTABLE", f"{key} is not executable until its business definition is governed.")
    for key in dimensions:
        if key not in DIMENSIONS: _error("UNKNOWN_DIMENSION", f"Unknown dimension: {key}")
    for item in filters:
        if not isinstance(item, dict) or item.get("dimension") not in DIMENSIONS: _error("INVALID_FILTER", "Filters require a known semantic dimension.")
        if not isinstance(item.get("value"), (str, int, float, bool, list, dict)): _error("INVALID_FILTER", "Filter value is invalid.")
    for key in metrics:
        unsupported = set(dimensions) - set(METRICS[key]["supported_dimensions"])
        if unsupported: _error("INCOMPATIBLE_DIMENSION", f"{key} cannot be combined with: {', '.join(sorted(unsupported))}.")
        invalid_filters = {f["dimension"] for f in filters} - set(METRICS[key]["supported_filters"])
        if invalid_filters: _error("INCOMPATIBLE_FILTER", f"{key} cannot be filtered by: {', '.join(sorted(invalid_filters))}.")
    time_grain = payload.get("time_grain")
    if time_grain not in {None, "day", "week", "month", "quarter", "year"}: _error("UNSUPPORTED_TIME_GRAIN", "Unsupported time grain.")
    explicit_time_dimension = payload.get("time_dimension")
    for key in metrics:
        if time_grain and ("TIME" not in dimensions or time_grain not in METRICS[key]["supported_time_grains"]): _error("UNSUPPORTED_TIME_GRAIN", f"{key} cannot be grouped by this time grain.")
        if explicit_time_dimension and explicit_time_dimension not in METRICS[key]["supported_time_dimensions"]: _error("UNSUPPORTED_TIME_GRAIN", f"{key} has no {explicit_time_dimension} time role.")
    try: limit = int(payload.get("limit", 100))
    except (TypeError, ValueError): _error("INVALID_LIMIT", "limit must be an integer.")
    if not 1 <= limit <= MAX_LIMIT: _error("LIMIT_EXCEEDED", "limit must be 1–200.")
    return metrics, dimensions, filters, limit, time_grain, explicit_time_dimension or (METRICS[metrics[0]]["supported_time_dimensions"][0])

def _snapshot(snapshot, part):
    value = (snapshot or {}).get(part)
    return value.get("display_name") if isinstance(value, dict) else value

def _bucket(value, grain):
    if not value: return None
    value = authority.aware(value)
    if grain == "day": return value.date().isoformat()
    if grain == "week": return f"{value.isocalendar().year}-W{value.isocalendar().week:02d}"
    if grain == "month": return f"{value.year:04d}-{value.month:02d}"
    if grain == "quarter": return f"{value.year:04d}-Q{((value.month - 1) // 3) + 1}"
    if grain == "year": return str(value.year)
    return value.date().isoformat()

def _shipment_dimensions(shipment, dimensions, time_value=None, time_grain=None):
    project = db.session.get(Project, shipment.project_id) if shipment.project_id else None
    customer = db.session.get(Customer, shipment.customer_id) if shipment.customer_id else None
    result = {}
    for key in dimensions:
        if key == "PROJECT": result[key] = project.public_id if project else None
        elif key == "CUSTOMER": result[key] = f"customer:{customer.id}" if customer else None
        elif key == "SHIPMENT_STATUS": result[key] = shipment.lifecycle_status
        elif key == "TIME": result[key] = _bucket(time_value or shipment.created_at, time_grain)
    return result

def _leg_dimensions(leg, shipment, dimensions, time_value=None, time_grain=None):
    result = _shipment_dimensions(shipment, dimensions, time_value, time_grain)
    values = {"TRANSPORT_MODE": leg.transport_mode, "LEG_STATUS": leg.status, "CARRIER": leg.carrier_reference,
        "ORIGIN_COUNTRY": _snapshot(leg.origin_snapshot, "country"), "ORIGIN_PROVINCE": _snapshot(leg.origin_snapshot, "province"), "ORIGIN_CITY": _snapshot(leg.origin_snapshot, "city"),
        "DESTINATION_COUNTRY": _snapshot(leg.destination_snapshot, "country"), "DESTINATION_PROVINCE": _snapshot(leg.destination_snapshot, "province"), "DESTINATION_CITY": _snapshot(leg.destination_snapshot, "city")}
    for side, key in (("origin", "ORIGIN_FACILITY"), ("destination", "DESTINATION_FACILITY")):
        point = (getattr(leg, f"{side}_snapshot") or {}).get("facility")
        values[key] = point.get("public_id") if isinstance(point, dict) else None
    result.update({key: values.get(key) for key in dimensions if key in values})
    return result

def _key(values, dimensions): return tuple(values.get(d) for d in dimensions)
def _rows(groups, dimensions, metric, unknown=None):
    unknown = unknown or {}
    if not groups and not dimensions: return [{metric: {"state": "ZERO", "value": 0}}]
    return [{**{d: value for d, value in zip(dimensions, key)}, metric: {"state": "VALUE" if value is not None else "NULL_UNKNOWN", "value": value, **unknown.get(key, {})}} for key, value in groups.items()]

def _authorized_shipment_statement(org, user):
    """Apply tenancy and canonical business access before analytics computation."""
    return select(OperationalShipment).where(
        OperationalShipment.organization_id == org,
        assigned_shipment_scope(user),
    )

def _shipments(org, user):
    return db.session.scalars(_authorized_shipment_statement(org, user)).all()

def _active_legs(org, user):
    authorized_ids = _authorized_shipment_statement(org, user).with_only_columns(OperationalShipment.id)
    return db.session.execute(select(RouteLeg, OperationalShipment).join(RoutePlan, RouteLeg.route_plan_id == RoutePlan.id).join(OperationalShipment, RoutePlan.operational_shipment_id == OperationalShipment.id).where(OperationalShipment.organization_id == org, OperationalShipment.id.in_(authorized_ids), RoutePlan.is_active.is_(True), RouteLeg.status != "cancelled")).all()

def _scope_shipment_ids(org, user, filters):
    rows = _shipments(org, user)
    for item in filters:
        key, value = item["dimension"], item["value"]
        if key == "PROJECT":
            project = db.session.scalar(select(Project).where(Project.public_id == str(value)))
            if not project or project.organization_id != org: _error("TENANT_SCOPE_VIOLATION", "Project is outside the analytics tenant.", 403)
            rows = [row for row in rows if row.project_id == project.id]
        elif key == "CUSTOMER":
            customer_id = str(value).removeprefix("customer:")
            customer = db.session.scalar(select(Customer).where(Customer.id == int(customer_id))) if customer_id.isdigit() else None
            if not customer or customer.operational_organization_id != org: _error("OUT_OF_SCOPE", "Customer is outside the analytics tenant.", 403)
            rows = [row for row in rows if row.customer_id == customer.id]
        elif key == "SHIPMENT_STATUS":
            if value not in {"planned", "in_progress", "completed", "cancelled"}: _error("INVALID_FILTER", "Invalid shipment status.")
            rows = [row for row in rows if row.lifecycle_status == value]
        elif key == "TIME":
            if not isinstance(value, dict) or not (value.get("from") or value.get("to")): _error("INVALID_FILTER", "TIME requires from and/or to ISO timestamps.")
            def in_range(row):
                stamp = authority.aware(row.created_at)
                start = datetime.fromisoformat(value["from"].replace("Z", "+00:00")) if value.get("from") else None
                end = datetime.fromisoformat(value["to"].replace("Z", "+00:00")) if value.get("to") else None
                return (not start or stamp >= authority.aware(start)) and (not end or stamp <= authority.aware(end))
            rows = [row for row in rows if in_range(row)]
        elif key in {"TRANSPORT_MODE", "LEG_STATUS", "ORIGIN_COUNTRY", "ORIGIN_PROVINCE", "ORIGIN_CITY", "DESTINATION_COUNTRY", "DESTINATION_PROVINCE", "DESTINATION_CITY", "ORIGIN_FACILITY", "DESTINATION_FACILITY"}:
            # Applied in the route-leg population; shipment scope deliberately remains tenant-safe.
            continue
        else: _error("INCOMPATIBLE_FILTER", f"{key} filters are not executable for this fact family.")
    return {row.id for row in rows}

def _matches_leg_filters(leg, filters):
    values = _leg_dimensions(leg, type("S", (), {"project_id": None, "customer_id": None, "lifecycle_status": None, "created_at": leg.created_at})(), [f["dimension"] for f in filters])
    return all(f["dimension"] not in values or values[f["dimension"]] == f["value"] for f in filters)

def _metric(metric, org, user, dimensions, scoped_shipments, filters=(), time_grain=None, time_dimension="created"):
    groups = defaultdict(lambda: 0)
    shipment_metrics = {"SHIPMENT_COUNT", "ACTIVE_SHIPMENT_COUNT", "PLANNED_SHIPMENT_COUNT", "IN_PROGRESS_SHIPMENT_COUNT", "COMPLETED_SHIPMENT_COUNT", "CANCELLED_SHIPMENT_COUNT", "REPLAN_COUNT"}
    if metric in shipment_metrics:
        status = {"ACTIVE_SHIPMENT_COUNT": {"planned", "in_progress"}, "PLANNED_SHIPMENT_COUNT": {"planned"}, "IN_PROGRESS_SHIPMENT_COUNT": {"in_progress"}, "COMPLETED_SHIPMENT_COUNT": {"completed"}, "CANCELLED_SHIPMENT_COUNT": {"cancelled"}}.get(metric)
        for shipment in _shipments(org, user):
            if shipment.id not in scoped_shipments: continue
            if status and shipment.lifecycle_status not in status: continue
            value = max((db.session.scalar(select(RoutePlan.revision_number).where(RoutePlan.operational_shipment_id == shipment.id).order_by(RoutePlan.revision_number.desc())) or 1) - 1, 0) if metric == "REPLAN_COUNT" else 1
            groups[_key(_shipment_dimensions(shipment, dimensions, shipment.created_at, time_grain), dimensions)] += value
    elif metric in {"ROUTE_LEG_COUNT", "COMPLETED_LEG_COUNT", "LEG_TRANSIT_TIME"}:
        for leg, shipment in _active_legs(org, user):
            if shipment.id not in scoped_shipments: continue
            if not _matches_leg_filters(leg, filters): continue
            if metric == "COMPLETED_LEG_COUNT" and leg.status != "completed": continue
            if metric == "LEG_TRANSIT_TIME":
                if not leg.actual_departure or not leg.actual_arrival:
                    key = _key(_leg_dimensions(leg, shipment, dimensions, leg.actual_departure or leg.actual_arrival or leg.created_at, time_grain), dimensions)
                    groups.setdefault(key, None)
                    continue
                value = (authority.aware(leg.actual_arrival) - authority.aware(leg.actual_departure)).total_seconds()
            else: value = 1
            groups[_key(_leg_dimensions(leg, shipment, dimensions, (leg.actual_arrival if time_dimension == "actual" else leg.created_at), time_grain), dimensions)] += value
    elif metric in {"RAW_EVENT_COUNT", "EFFECTIVE_BUSINESS_OCCURRENCE_COUNT"}:
        seen = set()
        rows = db.session.execute(select(MilestoneEvent, Milestone, OperationalShipment).join(Milestone, MilestoneEvent.milestone_id == Milestone.id).join(OperationalShipment, Milestone.operational_shipment_id == OperationalShipment.id).where(OperationalShipment.organization_id == org, MilestoneEvent.organization_id == org)).all()
        for event, milestone, shipment in rows:
            if shipment.id not in scoped_shipments: continue
            if metric == "RAW_EVENT_COUNT":
                pass
            else:
                if event.event_type not in authority.OCCURRENCES: continue
                effective = authority.effective_occurrence(milestone)
                if not effective or effective.id != event.id: continue
                root = event
                while root.supersedes_event_id: root = db.session.get(MilestoneEvent, root.supersedes_event_id)
                if root.id in seen: continue
                seen.add(root.id)
            dims = _shipment_dimensions(shipment, dimensions, event.occurred_at, time_grain); dims["OPERATOR"] = f"user:{event.actor_user_id}"
            groups[_key(dims, dimensions)] += 1
    elif metric == "DWELL_TIME":
        rows = db.session.execute(select(OperationalCheckpoint, RoutePlan, OperationalShipment).join(RoutePlan, OperationalCheckpoint.route_plan_id == RoutePlan.id).join(OperationalShipment, RoutePlan.operational_shipment_id == OperationalShipment.id).where(OperationalShipment.organization_id == org, RoutePlan.is_active.is_(True))).all()
        for checkpoint, _plan, shipment in rows:
            if shipment.id not in scoped_shipments: continue
            if checkpoint.actual_arrival_at and checkpoint.actual_departure_at:
                groups[_key(_shipment_dimensions(shipment, dimensions, checkpoint.actual_arrival_at, time_grain), dimensions)] += (authority.aware(checkpoint.actual_departure_at)-authority.aware(checkpoint.actual_arrival_at)).total_seconds()
    elif metric == "DOCUMENT_READINESS_COVERAGE":
        document = next(row for row in coverage(org, user) if row["coverage_key"] == "DOCUMENT_READINESS_SCOPE_COVERAGE")
        return _rows({tuple(): document["coverage_percent"]}, dimensions, metric)
    else:
        model, time_attr, open_only = ({"DELAY_CASE_COUNT": (OperationalDelay, "started_at", False), "REPORTED_DELAY_DURATION": (OperationalDelay, "started_at", False), "EXCEPTION_COUNT": (OperationalException, "occurred_at", False), "OPEN_EXCEPTION_COUNT": (OperationalException, "occurred_at", True), "OPEN_WORK_ITEM_COUNT": (OperationalWorkItem, "detected_at", True), "DOCUMENT_REQUIREMENT_COUNT": (OperationalDocumentRequirement, "created_at", False)}).get(metric, (None, None, None))
        if model is None: _error("METRIC_NOT_IMPLEMENTED", metric)
        statement = select(model).where(model.organization_id == org)
        if metric == "DOCUMENT_REQUIREMENT_COUNT":
            statement = statement.where(model.is_active.is_(True), model.applicability_state == "APPLICABLE")
        rows = db.session.scalars(statement).all()
        for row in rows:
            if open_only and ((getattr(row, "resolved_at", None) is not None) if hasattr(row, "resolved_at") else (getattr(row, "status", None) != "open")):
                continue
            shipment = db.session.get(OperationalShipment, row.operational_shipment_id)
            if not shipment or shipment.id not in scoped_shipments: continue
            value = 1
            if metric == "REPORTED_DELAY_DURATION":
                key = _key(_shipment_dimensions(shipment, dimensions, getattr(row, time_attr, None), time_grain), dimensions)
                if not row.resolved_at:
                    groups.setdefault(key, None)
                    continue
                value = (authority.aware(row.resolved_at) - authority.aware(row.started_at)).total_seconds()
            groups[_key(_shipment_dimensions(shipment, dimensions, getattr(row, time_attr, None), time_grain), dimensions)] += value
    return _rows(groups, dimensions, metric)

def coverage(org, user):
    shipments = _shipments(org, user); shipment_ids = [row.id for row in shipments]; legs = _active_legs(org, user); cargo = db.session.scalars(select(ShipmentCargoItem).join(OperationalShipment).where(OperationalShipment.organization_id == org, OperationalShipment.id.in_(shipment_ids))).all()
    def item(key, eligible, covered): return {"coverage_key": key, "definition": COVERAGE[key], "eligible_count": eligible, "covered_count": covered, "coverage_percent": (covered / eligible * 100) if eligible else None, "state": "VALUE" if eligible else "NOT_APPLICABLE"}
    return [item("SHIPMENTS_WITH_PROJECT_COVERAGE", len(shipments), sum(bool(x.project_id) for x in shipments)), item("SHIPMENTS_WITH_CARGO_COVERAGE", len(shipments), len({x.operational_shipment_id for x in cargo})), item("CARGO_CATALOG_LINK_COVERAGE", len(cargo), sum(bool(x.catalog_item_id) for x in cargo)), item("LEGS_WITH_ORIGIN_FACILITY_COVERAGE", len(legs), sum(bool(l.origin_logistics_point_id) for l, _s in legs)), item("LEGS_WITH_DESTINATION_FACILITY_COVERAGE", len(legs), sum(bool(l.destination_logistics_point_id) for l, _s in legs)), item("LEGS_WITH_CARRIER_REFERENCE_COVERAGE", len(legs), sum(bool(l.carrier_reference) for l, _s in legs)), item("COMPLETED_LEGS_WITH_ACTUAL_TIMES_COVERAGE", sum(l.status == "completed" for l, _s in legs), sum(l.status == "completed" and l.actual_departure and l.actual_arrival for l, _s in legs)), item("DOCUMENT_READINESS_SCOPE_COVERAGE", len(shipments), len({x.operational_shipment_id for x in db.session.scalars(select(OperationalDocumentRequirement).where(OperationalDocumentRequirement.organization_id == org, OperationalDocumentRequirement.operational_shipment_id.in_(shipment_ids), OperationalDocumentRequirement.is_active.is_(True))).all()})), item("CARGO_TRANSPORT_ALLOCATION_COVERAGE", len(cargo), len({x.shipment_cargo_item_id for x in db.session.scalars(select(ShipmentCargoTransportAllocation).where(ShipmentCargoTransportAllocation.operational_shipment_id.in_(shipment_ids))).all()}))]

def query(payload, user):
    require_permission(user, "operational_shipment.read")
    metrics, dimensions, filters, limit, time_grain, time_dimension = _check_request(payload)
    org = organization_for_user(int(user["id"]))
    scoped_shipments = _scope_shipment_ids(org, user, filters)
    rows = []
    for metric in metrics: rows.extend(_metric(metric, org, user, dimensions, scoped_shipments, filters, time_grain, time_dimension))
    warnings = []
    if "CARRIER" in dimensions: warnings.append("CARRIER_NOT_GOVERNED")
    if any(METRICS[m]["readiness"] == PARTIAL for m in metrics): warnings.append("PARTIAL_DIMENSION_COVERAGE")
    columns = [{"key": d, "business_name": DIMENSIONS[d]["business_name"], "kind": "dimension", "data_type": "string"} for d in dimensions]
    columns += [{"key": m, "business_name": METRICS[m]["business_name"], "kind": "metric", "data_type": "number", "unit": METRICS[m]["unit"], "null_semantics": METRICS[m]["null_policy"]} for m in metrics]
    normalized = {"metrics": metrics, "dimensions": dimensions, "filters": filters, "time_grain": time_grain, "time_dimension": time_dimension}
    return {"semantic_version": SEMANTIC_VERSION, "normalized_query": normalized, "query": normalized, "columns": columns, "rows": rows[:limit], "coverage": coverage(org, user), "warnings": warnings, "pagination": {"limit": limit, "next_cursor": None}, "execution": {"read_only": True, "organization_scoped": True, "business_access_scoped": True}}

def _drilldown_context(metric, payload):
    """Validate a drilldown as the original semantic query plus one segment.

    The segment is intentionally not a free-form database predicate.  It must
    be a dimension supported by the metric and is converted to the same
    governed filter vocabulary used by aggregate queries.
    """
    payload = dict(payload or {})
    cursor = payload.pop("cursor", None)
    if cursor is not None and (not isinstance(cursor, str) or not cursor.isdigit()):
        _error("INVALID_CURSOR", "cursor must be an opaque numeric continuation token.")
    segment = payload.pop("segment", None)
    supplied_metrics = payload.get("metrics")
    if supplied_metrics is not None and supplied_metrics != [metric]:
        _error("METRIC_CONTEXT_MISMATCH", "Drilldown context must name exactly the path metric.")
    payload["metrics"] = [metric]
    filters = list(payload.get("filters") or [])
    if segment is not None:
        if not isinstance(segment, dict) or set(segment) != {"dimension", "value"}:
            _error("INVALID_SEGMENT", "segment requires a semantic dimension and value.")
        dimension, value = segment["dimension"], segment["value"]
        if dimension not in METRICS[metric]["supported_dimensions"]:
            _error("INCOMPATIBLE_DIMENSION", f"{metric} cannot be segmented by {dimension}.")
        if dimension not in METRICS[metric]["supported_filters"]:
            _error("INCOMPATIBLE_FILTER", f"{metric} cannot be filtered by {dimension}.")
        if any(item.get("dimension") == dimension and item.get("value") != value for item in filters if isinstance(item, dict)):
            _error("FILTER_SEGMENT_CONFLICT", "The selected segment conflicts with the normalized query.")
        if not any(item.get("dimension") == dimension for item in filters if isinstance(item, dict)):
            filters.append({"dimension": dimension, "value": value})
    payload["filters"] = filters
    _metrics, dimensions, filters, requested_limit, time_grain, time_dimension = _check_request(payload)
    return dimensions, filters, requested_limit, time_grain, time_dimension, segment, int(cursor or 0)

def _page(items, limit, offset):
    page = items[offset:offset + limit]
    next_offset = offset + len(page)
    return page, str(next_offset) if next_offset < len(items) else None

def drilldown(metric, user, payload=None, limit=None):
    require_permission(user, "operational_shipment.read")
    if metric not in METRICS or METRICS[metric]["readiness"] not in {READY, PARTIAL}: _error("METRIC_NOT_READY", "Metric is not drillable.")
    if not METRICS[metric]["drilldown_supported"]: _error("INCOMPATIBLE_DIMENSION", "This metric has no safe drilldown.")
    payload = dict(payload or {})
    if limit is not None: payload["limit"] = limit
    dimensions, filters, requested_limit, time_grain, time_dimension, segment, cursor = _drilldown_context(metric, payload)
    org = organization_for_user(int(user["id"])); scoped = _scope_shipment_ids(org, user, filters)
    items = []
    if metric in {"ROUTE_LEG_COUNT", "COMPLETED_LEG_COUNT", "LEG_TRANSIT_TIME"}:
        for leg, shipment in _active_legs(org, user):
            if shipment.id in scoped and _matches_leg_filters(leg, filters) and (metric != "COMPLETED_LEG_COUNT" or leg.status == "completed"):
                items.append({"route_leg_id": leg.id, "shipment_public_id": shipment.public_id})
    elif metric in {"RAW_EVENT_COUNT", "EFFECTIVE_BUSINESS_OCCURRENCE_COUNT"}:
        rows = db.session.execute(select(MilestoneEvent, Milestone, OperationalShipment).join(Milestone, MilestoneEvent.milestone_id == Milestone.id).join(OperationalShipment, Milestone.operational_shipment_id == OperationalShipment.id).where(OperationalShipment.organization_id == org)).all()
        for event, milestone, shipment in rows:
            if shipment.id not in scoped: continue
            if metric == "EFFECTIVE_BUSINESS_OCCURRENCE_COUNT" and (event.event_type not in authority.OCCURRENCES or authority.effective_occurrence(milestone).id != event.id): continue
            items.append({"event_public_id": event.public_id, "shipment_public_id": shipment.public_id})
    elif metric in {"DELAY_CASE_COUNT", "REPORTED_DELAY_DURATION"}:
        for row in db.session.scalars(select(OperationalDelay).where(OperationalDelay.organization_id == org)).all():
            if row.operational_shipment_id in scoped and (metric != "REPORTED_DELAY_DURATION" or row.resolved_at):
                items.append({"delay_public_id": row.public_id, "shipment_public_id": db.session.get(OperationalShipment, row.operational_shipment_id).public_id})
    elif metric in {"EXCEPTION_COUNT", "OPEN_EXCEPTION_COUNT"}:
        for row in db.session.scalars(select(OperationalException).where(OperationalException.organization_id == org)).all():
            if row.operational_shipment_id in scoped and (metric != "OPEN_EXCEPTION_COUNT" or row.resolved_at is None):
                items.append({"exception_public_id": row.public_id, "shipment_public_id": db.session.get(OperationalShipment, row.operational_shipment_id).public_id})
    elif metric in {"DOCUMENT_REQUIREMENT_COUNT", "DOCUMENT_READINESS_COVERAGE"}:
        # Coverage is defined over the governed, applicable document scope.  A
        # coverage drilldown returns that eligible shipment population with its
        # readiness flag rather than substituting a generic shipment list.
        if metric == "DOCUMENT_READINESS_COVERAGE":
            ready = {row.operational_shipment_id for row in db.session.scalars(select(OperationalDocumentRequirement).where(OperationalDocumentRequirement.organization_id == org, OperationalDocumentRequirement.is_active.is_(True))).all()}
            for shipment in _shipments(org, user):
                if shipment.id in scoped:
                    items.append({"shipment_public_id": shipment.public_id, "document_readiness": shipment.id in ready})
        else:
            for row in db.session.scalars(select(OperationalDocumentRequirement).where(OperationalDocumentRequirement.organization_id == org, OperationalDocumentRequirement.is_active.is_(True), OperationalDocumentRequirement.applicability_state == "APPLICABLE")).all():
                if row.operational_shipment_id in scoped:
                    items.append({"document_requirement_public_id": row.public_id, "shipment_public_id": db.session.get(OperationalShipment, row.operational_shipment_id).public_id})
    else:
        # Shipment-facing metrics are represented by the authorized population, never a tenant-wide fallback.
        for shipment in _shipments(org, user):
            status = {"ACTIVE_SHIPMENT_COUNT": {"planned", "in_progress"}, "PLANNED_SHIPMENT_COUNT": {"planned"}, "IN_PROGRESS_SHIPMENT_COUNT": {"in_progress"}, "COMPLETED_SHIPMENT_COUNT": {"completed"}, "CANCELLED_SHIPMENT_COUNT": {"cancelled"}}.get(metric)
            if shipment.id in scoped and (not status or shipment.lifecycle_status in status): items.append({"shipment_public_id": shipment.public_id})
    page, next_cursor = _page(items, requested_limit, cursor)
    return {"semantic_version": SEMANTIC_VERSION, "metric": metric, "drilldown_type": METRICS[metric]["drilldown_type"], "normalized_query": {"metrics": [metric], "filters": filters, "dimensions": dimensions, "time_grain": time_grain, "time_dimension": time_dimension}, "segment": segment, "items": page, "pagination": {"limit": requested_limit, "next_cursor": next_cursor}}
