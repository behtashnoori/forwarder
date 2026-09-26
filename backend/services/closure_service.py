"""Explicit organization policy, current assessment, and controlled closure."""
from collections import defaultdict
from decimal import Decimal
import hashlib
import json

from sqlalchemy import select
from backend.extensions import db
from backend.closure_models import ClosurePolicy as Policy, ClosurePolicyVersion as Version, ClosurePolicyCriterion as Criterion, ClosureDecision as Decision, CRITERIA, MODES
from backend.cargo_models import ShipmentCargoItem as Cargo
from backend.models import ExpertUser
from backend.operational_models import OperationalOrganization, OperationalMembership, OperationalShipment as Shipment, OperationalException, OperationalWorkItem, RoutePlan, RouteLeg, RouteStageExecution, utcnow
from backend.mdpm_models import OperationalDocumentRequirement as Requirement
from backend.services import operational_service as base, route_time_service as times, route_orchestration_service as routes
from backend.services import delivery_service as deliveries, document_readiness_service as documents
from backend.services.assigned_work_authorization import authorize_document_management

LABELS = {
    "ACTUAL_QUANTITY_KNOWN": "مقدار واقعی همه کالاها مشخص باشد",
    "ALL_CARGO_DELIVERED": "برای همه کالاها، تحویل ثبت‌شده حداقل برابر مقدار واقعی باشد",
    "REQUIRED_DOCUMENTS_READY": "مدارک الزامی جاری تأیید لازم را داشته باشند",
    "NO_OPEN_EXCEPTIONS": "هیچ مشکل عملیاتی بازی باقی نماند",
    "NO_OPEN_FOLLOW_UPS": "هیچ پیگیری بازی باقی نماند",
    "NO_OPEN_OPERATIONAL_WORK": "هیچ کار عملیاتی بازی باقی نماند",
}


def fail(message, status=422, code="CLOSURE_INVALID"):
    raise base.OperationalError(code, message, status)


def context(user):
    try:
        return times.context(user, manage=True)
    except base.OperationalError:
        fail("تنها مدیر فعال همین سازمان مجاز به این اقدام است.", 403, "CLOSURE_FORBIDDEN")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def policy_version(row):
    criteria = db.session.scalars(select(Criterion).where(Criterion.policy_version_id == row.id).order_by(Criterion.scope, Criterion.code)).all()
    end = db.session.scalar(select(Version.effective_from).where(Version.policy_id == row.policy_id, Version.version > row.version).order_by(Version.version).limit(1))
    return {"public_id": row.public_id, "version": row.version, "effective_from": times.aware(row.effective_from).isoformat(),
        "effective_until": times.aware(end).isoformat() if end else None, "recorded_at": times.aware(row.recorded_at).isoformat(),
        "criteria": [{"public_id": c.public_id, "scope": c.scope, "code": c.code, "mandatory": c.mandatory, "label": LABELS[c.code]} for c in criteria]}


def configuration(user):
    org = context(user)
    versions = db.session.scalars(select(Version).where(Version.organization_id == org).order_by(Version.version.desc())).all()
    return {"versions": [policy_version(row) for row in versions], "criteria": LABELS, "scopes": MODES}


def save_policy(user, payload, key):
    org = context(user)
    if not isinstance(payload, dict) or set(payload) != {"expected_version", "effective_from", "criteria"}:
        fail("فیلدهای قواعد بستن معتبر نیست.")
    if type(payload["expected_version"]) is not int or payload["expected_version"] < 0:
        fail("نسخه قواعد لازم است.")
    values = payload["criteria"]
    if not isinstance(values, list) or not 1 <= len(values) <= len(CRITERIA) * len(MODES):
        fail("حداقل یک معیار روشن انتخاب کنید.")
    seen = set()
    for value in values:
        if not isinstance(value, dict) or set(value) != {"scope", "code", "mandatory"} or value["scope"] not in MODES or value["code"] not in CRITERIA or type(value["mandatory"]) is not bool:
            fail("معیار، روش حمل یا الزام معتبر نیست.")
        identity = (value["scope"], value["code"])
        if identity in seen: fail("معیار تکراری در یک دامنه مجاز نیست.")
        seen.add(identity)
    effective = times.instant(payload["effective_from"])
    db.session.scalar(select(OperationalOrganization).where(OperationalOrganization.id == org).with_for_update())
    db.session.scalar(select(ExpertUser).where(ExpertUser.id == user["id"]).with_for_update().execution_options(populate_existing=True))
    db.session.scalars(select(OperationalMembership).where(OperationalMembership.user_id == user["id"]).order_by(OperationalMembership.id).with_for_update()).all()
    db.session.expire_all()
    context(user)
    command, request_hash = routes._idempotency(org, "closure.policy", "ClosurePolicy", org, key, {"actor": user["id"], **payload})
    if command: return db.session.get(Version, command.result_resource_id), False
    policy = db.session.scalar(select(Policy).where(Policy.organization_id == org))
    latest = db.session.scalar(select(Version).where(Version.organization_id == org).order_by(Version.version.desc()).limit(1))
    if payload["expected_version"] != (latest.version if latest else 0):
        fail("قواعد تغییر کرده است؛ دوباره بخوانید.", 409, "STALE_CLOSURE_POLICY")
    if latest and (effective <= times.aware(latest.effective_from) or effective < utcnow()):
        fail("نسخه جدید باید در آینده و بعد از نسخه قبلی معتبر شود.")
    if policy is None:
        policy = Policy(organization_id=org); db.session.add(policy); db.session.flush()
    row = Version(organization_id=org, policy_id=policy.id, version=latest.version + 1 if latest else 1,
                  effective_from=effective, actor_user_id=user["id"])
    db.session.add(row); db.session.flush()
    db.session.add_all(Criterion(organization_id=org, policy_version_id=row.id, **value) for value in values)
    db.session.flush()
    routes._reserve_idempotency(org, "closure.policy", "ClosurePolicy", org, key, request_hash, row.id)
    base._audit(org, user["id"], "closure.policy.created", "ClosurePolicyVersion", row.id)
    return row, True


def applicable(shipment, at):
    return db.session.scalar(select(Version).where(Version.organization_id == shipment.organization_id,
        Version.effective_from <= at).order_by(Version.version.desc()).limit(1))


def _facts(shipment):
    cargo = db.session.scalars(select(Cargo).where(Cargo.operational_shipment_id == shipment.id).order_by(Cargo.id)).all()
    totals = deliveries.summaries(shipment, cargo)
    delivery_rows = db.session.scalars(select(deliveries.Delivery).where(deliveries.Delivery.operational_shipment_id == shipment.id, deliveries.current_predicate()).order_by(deliveries.Delivery.id)).all()
    reqs = db.session.scalars(select(Requirement).where(Requirement.operational_shipment_id == shipment.id, Requirement.is_active.is_(True)).order_by(Requirement.id)).all()
    projections = [documents._requirement_projection(row) for row in reqs]
    required = [r for r in projections if r["requirement_level"] != "OPTIONAL"]
    exceptions = db.session.scalars(select(OperationalException).where(OperationalException.operational_shipment_id == shipment.id, OperationalException.resolved_at.is_(None)).order_by(OperationalException.id)).all()
    work = db.session.scalars(select(OperationalWorkItem).where(OperationalWorkItem.operational_shipment_id == shipment.id, OperationalWorkItem.status == "open").order_by(OperationalWorkItem.id)).all()
    known = bool(cargo) and all(c.actual_quantity is not None for c in cargo)
    delivered = known and all(t["has_delivery"] and Decimal(t["remaining"]) == 0 for t in totals)
    states = {
        "ACTUAL_QUANTITY_KNOWN": "PASS" if known else "UNKNOWN",
        "ALL_CARGO_DELIVERED": "UNKNOWN" if not known else "PASS" if delivered else "FAIL",
        "REQUIRED_DOCUMENTS_READY": "UNKNOWN" if not reqs or any(r["readiness_status"] == "UNRESOLVED" for r in required) else "PASS" if all(r["readiness_status"] in {"SATISFIED", "NOT_APPLICABLE"} for r in required) else "FAIL",
        "NO_OPEN_EXCEPTIONS": "FAIL" if any(e.resolved_at is None for e in exceptions) else "PASS",
        "NO_OPEN_FOLLOW_UPS": "FAIL" if any(w.status == "open" and w.work_type == "FOLLOW_UP" for w in work) else "PASS",
        "NO_OPEN_OPERATIONAL_WORK": "FAIL" if any(w.status == "open" and w.work_type != "FOLLOW_UP" for w in work) else "PASS",
    }
    facts = {"cargo": [[c.id, c.version, str(c.actual_quantity)] for c in cargo],
        "deliveries": [[d.id, d.revision, str(d.quantity), d.supersedes_delivery_id] for d in delivery_rows],
        "documents": projections, "exceptions": [[e.id, e.version, str(e.resolved_at)] for e in exceptions],
        "work": [[w.id, w.version, w.status, w.work_type] for w in work]}
    return states, facts


def assess(shipment, at=None, *, include_sources=False):
    at = at or utcnow()
    version = applicable(shipment, at)
    plans = db.session.scalars(select(RoutePlan).where(RoutePlan.operational_shipment_id == shipment.id, RoutePlan.is_active.is_(True))).all()
    plan_ids = [p.id for p in plans]
    legs = db.session.scalars(select(RouteLeg).where(RouteLeg.route_plan_id.in_(plan_ids), RouteLeg.status != "cancelled").order_by(RouteLeg.id)).all()
    # Existing stage execution derives its mode from the governed route leg.
    executed_legs = db.session.scalars(select(RouteLeg).where(RouteLeg.id.in_(select(RouteStageExecution.route_leg_id)
        .where(RouteStageExecution.operational_shipment_id == shipment.id)))).all()
    relevant = {leg.id: leg for leg in [*legs, *executed_legs]}
    modes = sorted({leg.transport_mode for leg in relevant.values() if leg.transport_mode in MODES})
    gap = not relevant or any(leg.transport_mode not in MODES[1:] for leg in relevant.values())
    items, facts = [], {}
    if version:
        states, facts = _facts(shipment)
        grouped = defaultdict(list)
        for row in db.session.scalars(select(Criterion).where(Criterion.policy_version_id == version.id,
                Criterion.scope.in_(["GENERAL", *modes])).order_by(Criterion.code, Criterion.scope)).all():
            grouped[row.code].append(row)
        for code, rows in grouped.items():
            items.append({"code": code, "label": LABELS[code], "mandatory": any(r.mandatory for r in rows), "state": states[code],
                "criteria": [{"public_id": r.public_id, "scope": r.scope, "code": r.code, "mandatory": r.mandatory} for r in rows]})
    missing = [i for i in items if i["state"] != "PASS"]
    if gap: missing.append({"code": "MODE_UNDEFINED", "label": "روش حمل همه بخش‌های قابل اعمال مشخص نیست", "mandatory": True, "state": "UNKNOWN", "criteria": []})
    if version and not items: missing.append({"code": "NO_APPLICABLE_CRITERIA", "label": "معیاری برای این حمل تعریف نشده است", "mandatory": True, "state": "UNKNOWN", "criteria": []})
    basis = {"policy": version.id if version else None, "shipment": [shipment.id, shipment.version, shipment.lifecycle_status],
        "modes": modes, "route": [[r.id, r.version, r.transport_mode] for r in sorted(relevant.values(), key=lambda r: r.id)], "facts": facts, "items": items, "missing": missing}
    result = {"policy": policy_version(version) if version else None, "shipment_version": shipment.version,
        "lifecycle_status": shipment.lifecycle_status, "assessed_at": times.aware(at).isoformat(), "modes": modes,
        "items": items, "missing": missing, "normal_ready": bool(version and items and not any(i["mandatory"] for i in missing) and shipment.lifecycle_status == "completed"),
        "message": None if version else "قواعد بستن پرونده تعریف نشده است", "fingerprint": fingerprint(basis)}
    if include_sources:
        result["source_facts"] = facts
    return result


def project_decision(row):
    return {"public_id": row.public_id, "kind": row.kind, "reason": row.reason, "actor": row.actor_label,
        "occurred_at": times.aware(row.occurred_at).isoformat(), "recorded_at": times.aware(row.recorded_at).isoformat(),
        "shipment_version": row.shipment_version, "assessment": {key: value for key, value in row.assessment.items() if key != "source_facts"}, "missing_items": row.missing_items}


def read(shipment_id, user):
    shipment = base.scoped_shipment(shipment_id, user)
    row = db.session.scalar(select(Decision).where(Decision.operational_shipment_id == shipment.id))
    actor = db.session.get(ExpertUser, user["id"], populate_existing=True)
    return {"assessment": assess(shipment), "decision": project_decision(row) if row else None,
        "can_close": authorize_document_management(user, shipment).allowed,
        "can_close_exceptionally": bool(actor and actor.is_active and actor.authority == "ORGANIZATION_ADMIN")}


def close(shipment_id, user, payload, key):
    shipment = base.scoped_shipment(shipment_id, user)
    fields = {"kind", "reason", "expected_shipment_version", "policy_version_public_id", "assessment_fingerprint"}
    if not isinstance(payload, dict) or set(payload) != fields or not isinstance(payload["kind"], str) or payload["kind"] not in {"NORMAL", "EXCEPTIONAL"}:
        fail("اطلاعات فرمان بستن معتبر نیست.")
    def authorize():
        if payload["kind"] == "EXCEPTIONAL":
            if context(user) != shipment.organization_id: fail("دسترسی مجاز نیست.", 403)
        elif not authorize_document_management(user, shipment).allowed:
            fail("فقط کارشناس مسئول می‌تواند پرونده را ببندد.", 403, "CLOSURE_FORBIDDEN")
    authorize()
    reason = payload["reason"]
    if reason is not None and (not isinstance(reason, str) or len(reason.strip()) > 1000): fail("دلیل معتبر نیست.")
    if payload["kind"] == "EXCEPTIONAL" and not (reason or "").strip(): fail("دلیل بستن با استثنا الزامی است.")
    db.session.scalar(select(OperationalOrganization).where(OperationalOrganization.id == shipment.organization_id).with_for_update())
    shipment = db.session.scalar(select(Shipment).where(Shipment.id == shipment.id).with_for_update().execution_options(populate_existing=True))
    db.session.scalar(select(ExpertUser).where(ExpertUser.id == user["id"]).with_for_update().execution_options(populate_existing=True))
    db.session.scalars(select(OperationalMembership).where(OperationalMembership.user_id == user["id"]).order_by(OperationalMembership.id).with_for_update()).all()
    # Re-read every source after a competing writer releases the parent fence.
    db.session.expire_all()
    authorize()
    command, request_hash = routes._idempotency(shipment.organization_id, "shipment.close", "OperationalShipment", shipment.id, key, {"actor": user["id"], **payload})
    if command: return db.session.get(Decision, command.result_resource_id), False
    if shipment.lifecycle_status != "completed": fail("فقط پرونده تکمیل‌شده می‌تواند بسته شود.", 409, "CLOSURE_PREDECESSOR")
    current = assess(shipment, include_sources=True)
    if current["policy"] is None: fail("قواعد بستن پرونده تعریف نشده است", 409, "CLOSURE_POLICY_UNDEFINED")
    if type(payload["expected_shipment_version"]) is not int or payload["expected_shipment_version"] != shipment.version or payload["policy_version_public_id"] != current["policy"]["public_id"] or payload["assessment_fingerprint"] != current["fingerprint"]:
        fail("پرونده، قواعد یا الزامات تغییر کرده است؛ دوباره بررسی کنید.", 409, "STALE_CLOSURE_ASSESSMENT")
    if payload["kind"] == "NORMAL" and not current["normal_ready"]:
        fail("الزامات اجباری هنوز کامل نیست.", 409, "CLOSURE_REQUIREMENTS_MISSING")
    actor = db.session.get(ExpertUser, user["id"], populate_existing=True)
    now = times.instant(current["assessed_at"])
    row = Decision(organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
        policy_version_id=applicable(shipment, times.instant(current["assessed_at"])).id, kind=payload["kind"], actor_user_id=actor.id,
        actor_label=actor.full_name, reason=(reason or "").strip() or None, shipment_version=shipment.version + 1,
        assessment_fingerprint=current["fingerprint"], assessment=current, missing_items=current["missing"], occurred_at=now, recorded_at=now)
    db.session.add(row); db.session.flush()
    shipment.lifecycle_status = "closed"; shipment.version += 1
    db.session.flush()
    routes._reserve_idempotency(shipment.organization_id, "shipment.close", "OperationalShipment", shipment.id, key, request_hash, row.id)
    base._audit(shipment.organization_id, actor.id, "shipment.closed", "ClosureDecision", row.id)
    base._outbox(shipment.organization_id, "shipment.closed", "OperationalShipment", shipment.id)
    return row, True
