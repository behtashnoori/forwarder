"""Versioned reference durations; no ETA, SLA or automatic plan rewrite."""
from datetime import datetime, timezone
from sqlalchemy import func, select
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalOrganization, RouteLeg, utcnow
from backend.route_time_models import OrganizationRouteTime as Reference, OrganizationRouteTimeVersion as Version, RouteLegTimeBasis as Basis
from backend.services import operational_service as base, route_orchestration_service as routes
from backend.services.admin_authorization_service import AdminAuthorizationError, organization_context_for_authenticated_user

VALUES = {"movement_min_minutes", "movement_max_minutes", "stop_min_minutes", "stop_max_minutes", "effective_from"}
KEYS = {"origin", "destination", "transport_mode"}
SOURCES = {"province", "city", "country", "international_city", "iran_port", "customs_office", "logistics_point"}


def fail(message, status=422, code="ROUTE_TIME_INVALID"):
    raise base.OperationalError(code, message, status)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def instant(value):
    try:
        if not isinstance(value, str): raise ValueError()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None: raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        fail("تاریخ شروع اعتبار باید همراه منطقه زمانی باشد.")


def context(user, *, manage=False):
    actor = db.session.get(ExpertUser, int(user["id"]), populate_existing=True)
    if not actor or not actor.is_active or actor.authority not in ({"ORGANIZATION_ADMIN"} if manage else {"EXPERT", "ORGANIZATION_ADMIN"}):
        fail("دسترسی به مرجع زمان سازمان مجاز نیست.", 403, "ROUTE_TIME_FORBIDDEN")
    try:
        return organization_context_for_authenticated_user(actor.id).organization_id
    except AdminAuthorizationError:
        fail("عضویت فعال در یک سازمان لازم است.", 403, "ROUTE_TIME_FORBIDDEN")


def _payload(value, allowed):
    if not isinstance(value, dict) or set(value) - allowed:
        fail("فیلدهای مرجع زمان معتبر نیست.")
    return value


def _fields(payload):
    result = {"effective_from": instant(payload.get("effective_from"))}
    for prefix, minimum in (("movement", 1), ("stop", 0)):
        lower, upper = (payload.get(f"{prefix}_{end}_minutes") for end in ("min", "max"))
        if (lower is None) != (upper is None): fail("حداقل و حداکثر هر بازه را با هم وارد کنید.")
        if lower is not None and (type(lower) is not int or type(upper) is not int or not minimum <= lower <= upper <= 525600):
            fail("ترتیب یا مقدار بازه زمان معتبر نیست.")
        result.update({f"{prefix}_min_minutes": lower, f"{prefix}_max_minutes": upper})
    if result["movement_min_minutes"] is None and result["stop_min_minutes"] is None:
        fail("حداقل یک بازه حرکت یا توقف لازم است؛ مقدار پیش‌فرض ساخته نمی‌شود.")
    return result


def _key(payload, org):
    if payload.get("transport_mode") not in routes.TRANSPORT_MODES: fail("روش حمل معتبر را انتخاب کنید.")
    result = {"transport_mode": payload["transport_mode"]}
    for side in ("origin", "destination"):
        value = payload.get(side)
        if not isinstance(value, dict) or value.get("source_type") not in SOURCES: fail("مکان مرجع معتبر را انتخاب کنید.")
        endpoint = base._endpoint(value, org)
        result[f"{side}_location_id"] = base._endpoint_location(endpoint).canonical_location.id
        result[f"{side}_point_id"] = endpoint.logistics_point.id if isinstance(endpoint, base.ResolvedFacilityEndpoint) else None
        result[f"{side}_snapshot"] = base._endpoint_snapshot(endpoint)
    if (result["origin_location_id"], result["origin_point_id"]) == (result["destination_location_id"], result["destination_point_id"]):
        fail("مبدأ و مقصد باید متفاوت باشند.")
    return result


def project_version(row, end=None):
    if row is None: return None
    if end is None:
        end = db.session.scalar(select(Version.effective_from).where(
            Version.reference_id == row.reference_id, Version.version > row.version
        ).order_by(Version.version).limit(1))
    actor = db.session.get(ExpertUser, row.actor_user_id)
    return {"public_id": row.public_id, "version": row.version,
        **{key: getattr(row, key) for key in VALUES - {"effective_from"}},
        "effective_from": aware(row.effective_from).isoformat(),
        "effective_until": aware(end).isoformat() if end else None,
        "recorded_at": aware(row.recorded_at).isoformat(), "actor_user_id": row.actor_user_id,
        "recorded_by": actor.full_name if actor else None}


def project(reference):
    versions = db.session.scalars(select(Version).where(Version.reference_id == reference.id).order_by(Version.version.desc())).all()
    values = [project_version(row, versions[index-1].effective_from if index else None) for index, row in enumerate(versions)]
    current = next((row for row in values if instant(row["effective_from"]) <= utcnow()), None)
    return {"public_id": reference.public_id, "origin_label": endpoint_label(reference.origin_snapshot),
        "destination_label": endpoint_label(reference.destination_snapshot), "transport_mode": reference.transport_mode,
        "latest_version": versions[0].version, "current": current, "versions": values}


def endpoint_label(snapshot):
    return (snapshot.get("facility") or snapshot)["display_name"]


def listing(user, page=1):
    org = context(user)
    try:
        page = int(page)
        if not 1 <= page <= 100000: raise ValueError()
    except (ValueError, TypeError): fail("شماره صفحه معتبر نیست.")
    query = select(Reference).where(Reference.organization_id == org)
    total = db.session.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.session.scalars(query.order_by(Reference.id.desc()).offset((page-1)*20).limit(20)).all()
    return {"items": [project(row) for row in rows], "page": page, "total": total, "has_next": page*20 < total}


def save(user, payload, key, reference_id=None):
    org = context(user, manage=True)
    _payload(payload, VALUES | ({"expected_version"} if reference_id else KEYS))
    # Organization lock also serializes creation of the same natural key.
    db.session.scalar(select(OperationalOrganization).where(OperationalOrganization.id == org).with_for_update())
    context(user, manage=True)
    reference = None
    if reference_id:
        reference = db.session.scalar(select(Reference).where(Reference.public_id == reference_id, Reference.organization_id == org).with_for_update())
        if reference is None: fail("مرجع زمان یافت نشد.", 404, "ROUTE_TIME_NOT_FOUND")
    resource = reference.id if reference else 0
    command, request_hash = routes._idempotency(org, "route_time.version", "RouteTime", resource, key, {"actor_id": user["id"], **payload})
    if command:
        previous = db.session.get(Version, command.result_resource_id)
        return previous, False
    fields = _fields(payload)
    if reference:
        last = db.session.scalar(select(Version).where(Version.reference_id == reference.id).order_by(Version.version.desc()).limit(1))
        if type(payload.get("expected_version")) is not int or payload["expected_version"] != last.version:
            fail("نسخه مرجع تغییر کرده است؛ دوباره بخوانید.", 409, "STALE_ROUTE_TIME")
        if fields["effective_from"] <= aware(last.effective_from) or fields["effective_from"] < utcnow():
            fail("شروع اعتبار نسخه تازه باید در آینده و بعد از نسخه قبلی باشد.")
        version = last.version + 1
    else:
        identity = _key(payload, org)
        existing = db.session.scalar(select(Reference.id).where(Reference.organization_id == org,
            *[getattr(Reference, field) == value for field, value in identity.items() if not field.endswith("_snapshot")]))
        if existing: fail("برای این مسیر و روش حمل مرجع وجود دارد؛ نسخه تازه ثبت کنید.", 409, "ROUTE_TIME_EXISTS")
        reference = Reference(organization_id=org, actor_user_id=user["id"], **identity)
        db.session.add(reference); db.session.flush()
        version = 1
    row = Version(organization_id=org, reference_id=reference.id, version=version, actor_user_id=user["id"], **fields)
    db.session.add(row); db.session.flush()
    routes._reserve_idempotency(org, "route_time.version", "RouteTime", resource, key, request_hash, row.id)
    base._audit(org, user["id"], "route_time.version.created", "OrganizationRouteTimeVersion", row.id)
    base._outbox(org, "route_time.version.created", "OrganizationRouteTimeVersion", row.id)
    return row, True


def fingerprint(leg):
    return {"origin_location_id": leg.origin_location_id, "destination_location_id": leg.destination_location_id,
        "origin_point_id": leg.origin_logistics_point_id, "destination_point_id": leg.destination_logistics_point_id,
        "transport_mode": leg.transport_mode, "planned_departure": aware(leg.planned_departure).isoformat() if leg.planned_departure else None}


def applicable(leg, org, at, *, lock=False):
    query = select(Reference).where(Reference.organization_id == org,
        Reference.origin_location_id == leg.origin_location_id, Reference.destination_location_id == leg.destination_location_id,
        Reference.origin_point_id == leg.origin_logistics_point_id, Reference.destination_point_id == leg.destination_logistics_point_id,
        Reference.transport_mode == leg.transport_mode)
    reference = db.session.scalar(query.with_for_update() if lock else query)
    return db.session.scalar(select(Version).where(Version.reference_id == reference.id,
        Version.effective_from <= at).order_by(Version.effective_from.desc()).limit(1)) if reference else None


def _basis(row):
    return {"public_id": row.public_id, "selection_revision": row.selection_revision,
        "reference_at": aware(row.reference_at).isoformat(), "recorded_at": aware(row.recorded_at).isoformat(),
        "actor_user_id": row.actor_user_id, "reference": project_version(db.session.get(Version, row.reference_version_id))}


def plan_read(shipment_id, plan_id, user):
    org = context(user)
    shipment, plan = routes._plan(shipment_id, plan_id, user, routes.PLAN_PERMISSIONS["read"])
    can_select = plan.status == "draft" and shipment.primary_responsible_expert_id == int(user["id"])
    try: base.require_permission(user, "route_leg.manage")
    except base.OperationalError: can_select = False
    result = []
    for leg in db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id == plan.id).order_by(RouteLeg.sequence_number)).all():
        at = aware(leg.planned_departure) if leg.planned_departure else utcnow()
        history = db.session.scalars(select(Basis).where(Basis.route_leg_id == leg.id).order_by(Basis.selection_revision.desc())).all()
        selected = history[0] if history else None
        result.append({"leg_id": leg.id, "leg_version": leg.version, "sequence_number": leg.sequence_number,
            "origin_label": endpoint_label(leg.origin_snapshot), "destination_label": endpoint_label(leg.destination_snapshot),
            "transport_mode": leg.transport_mode, "reference_at": at.isoformat(),
            "time_basis": "PLANNED_DEPARTURE" if leg.planned_departure else "SELECTION_TIME",
            "applicable": project_version(applicable(leg, org, at)), "selected": _basis(selected) if selected else None,
            "selection_matches_leg": bool(selected and selected.leg_basis == fingerprint(leg)),
            "history": [_basis(row) for row in history], "can_select": can_select})
    return {"plan_id": plan.id, "plan_revision": plan.revision_number, "plan_status": plan.status, "items": result}


def select_basis(shipment_id, plan_id, leg_id, user, payload, key):
    org = context(user)
    _payload(payload, {"expected_version", "expected_selection_revision", "reference_version_public_id"})
    shipment, plan = routes._plan(shipment_id, plan_id, user, "route_leg.manage", True)
    from backend.services.closure_commands import deny_new
    deny_new(shipment)
    leg = db.session.scalar(select(RouteLeg).where(RouteLeg.id == leg_id, RouteLeg.route_plan_id == plan.id).with_for_update().execution_options(populate_existing=True))
    if leg is None: fail("بخش مسیر یافت نشد.", 404, "ROUTE_TIME_NOT_FOUND")
    command, request_hash = routes._idempotency(org, "route_time.select", "RouteLeg", leg.id, key, {"actor_id": user["id"], **payload})
    if command: return db.session.get(Basis, command.result_resource_id), False
    if plan.status != "draft": fail("مبنای برنامه منتشرشده قابل تغییر نیست.", 409, "ROUTE_PLAN_NOT_DRAFT")
    context(user)
    current = db.session.scalar(select(func.max(Basis.selection_revision)).where(Basis.route_leg_id == leg.id)) or 0
    if type(payload.get("expected_version")) is not int or payload["expected_version"] != leg.version or type(payload.get("expected_selection_revision")) is not int or payload["expected_selection_revision"] != current:
        fail("برنامه یا مبنای آن تغییر کرده است؛ دوباره بخوانید.", 409, "STALE_ROUTE_TIME")
    at = aware(leg.planned_departure) if leg.planned_departure else utcnow()
    reference = applicable(leg, org, at, lock=True)
    if reference is None: fail("زمان مرجع تعریف نشده است.", 409, "ROUTE_TIME_UNDEFINED")
    if reference.public_id != payload.get("reference_version_public_id"):
        fail("نسخه قابل استفاده تغییر کرده است؛ دوباره بخوانید.", 409, "STALE_ROUTE_TIME")
    row = Basis(organization_id=org, operational_shipment_id=shipment.id, route_plan_id=plan.id,
        route_leg_id=leg.id, reference_version_id=reference.id, selection_revision=current+1,
        leg_basis=fingerprint(leg), reference_at=at, actor_user_id=user["id"])
    db.session.add(row); db.session.flush()
    routes._reserve_idempotency(org, "route_time.select", "RouteLeg", leg.id, key, request_hash, row.id)
    base._audit(org, user["id"], "route_time.basis.selected", "RouteLegTimeBasis", row.id)
    base._outbox(org, "route_time.basis.selected", "RouteLegTimeBasis", row.id)
    return row, True
