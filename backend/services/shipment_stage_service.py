"""Organization stage configuration and explicit Shipment stage execution."""
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID

from sqlalchemy import select

from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment, utcnow
from backend.shipment_stage_models import (
    CANONICAL_STAGE_CODES,
    OrganizationShipmentStageDefinition as Definition,
    OrganizationShipmentStageDefinitionVersion as DefinitionVersion,
    OrganizationShipmentStagePolicy as Policy,
    OrganizationShipmentStagePolicyVersion as PolicyVersion,
    ShipmentOperationalStageEvent as StageEvent,
    ShipmentOperationalStageInstance as StageInstance,
)
from backend.services import operational_service as base
from backend.services import route_orchestration_service as routes
from backend.services import route_time_service as times
from backend.services import closure_commands as closure_guard


CANONICAL_NAMES_FA = {
    "PREPARATION_LOADING": "آماده‌سازی / بارگیری",
    "ORIGIN_DEPARTURE": "خروج از مبدأ",
    "IN_TRANSIT": "در مسیر",
    "DESTINATION_ARRIVAL": "رسیدن به مقصد",
    "UNLOADING": "تخلیه",
}


def fail(message, status=422, code="SHIPMENT_STAGE_INVALID"):
    raise base.OperationalError(code, message, status)


def _uuid(value):
    try:
        if not isinstance(value, str):
            raise ValueError()
        return str(UUID(value))
    except ValueError:
        fail("شناسه مرحله معتبر نیست.")


def _instant(value):
    try:
        if not isinstance(value, str):
            raise ValueError()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        fail("زمان رخداد مرحله باید منطقه زمانی داشته باشد.")


def admin_context(user):
    try:
        return times.context(user, manage=True)
    except base.OperationalError:
        fail("تنها مدیر فعال همین سازمان می‌تواند مراحل سازمان را پیکربندی کند.", 403, "SHIPMENT_STAGE_ADMIN_FORBIDDEN")


def _actor_is_owner_expert(user, shipment):
    actor = db.session.get(ExpertUser, int(user["id"]), populate_existing=True)
    return bool(actor and actor.is_active and actor.authority == "EXPERT" and actor.id == shipment.primary_responsible_expert_id)


def _can_record(user, shipment):
    try:
        base.require_permission(user, "operational_shipment.create")
        return _actor_is_owner_expert(user, shipment)
    except base.OperationalError:
        return False


def applicable(organization_id, at=None):
    at = at or utcnow()
    return db.session.scalar(select(PolicyVersion).where(
        PolicyVersion.organization_id == organization_id,
        PolicyVersion.effective_from <= at,
    ).order_by(PolicyVersion.version.desc()).limit(1))


def _definitions(version, *, active_only=False):
    if version is None:
        return []
    query = select(DefinitionVersion, Definition).join(
        Definition,
        (Definition.id == DefinitionVersion.definition_id)
        & (Definition.organization_id == DefinitionVersion.organization_id),
    ).where(DefinitionVersion.policy_version_id == version.id)
    if active_only:
        query = query.where(DefinitionVersion.is_active.is_(True))
    return db.session.execute(query.order_by(DefinitionVersion.sequence)).all()


def _version_view(version):
    rows = _definitions(version)
    return {
        "public_id": version.public_id,
        "version": version.version,
        "effective_from": times.aware(version.effective_from).isoformat(),
        "recorded_at": times.aware(version.recorded_at).isoformat(),
        "stages": [
            {
                "public_id": definition.public_id,
                "configuration_public_id": item.public_id,
                "code": definition.code,
                "display_name_fa": item.display_name_fa,
                "sequence": item.sequence,
                "active": item.is_active,
                "required_for_completion": item.required_for_completion,
            }
            for item, definition in rows
        ],
    }


def configuration(user):
    organization_id = admin_context(user)
    versions = db.session.scalars(select(PolicyVersion).where(
        PolicyVersion.organization_id == organization_id,
    ).order_by(PolicyVersion.version.desc())).all()
    return {
        "canonical_stages": [
            {"code": code, "display_name_fa": CANONICAL_NAMES_FA[code]}
            for code in CANONICAL_STAGE_CODES
        ],
        "versions": [_version_view(version) for version in versions],
    }


def _validated_configuration(payload):
    if not isinstance(payload, dict) or set(payload) != {"expected_version", "effective_from", "stages"}:
        fail("فیلدهای پیکربندی مراحل معتبر نیست.")
    expected = payload["expected_version"]
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
        fail("نسخه مورد انتظار پیکربندی لازم است.")
    stages = payload["stages"]
    if not isinstance(stages, list) or len(stages) != len(CANONICAL_STAGE_CODES):
        fail("پیکربندی باید هر پنج مرحله استاندارد را دقیقاً یک‌بار مشخص کند.")
    seen_codes, seen_sequences, normalized = set(), set(), []
    for stage in stages:
        fields = {"code", "display_name_fa", "sequence", "active", "required_for_completion"}
        if not isinstance(stage, dict) or set(stage) != fields:
            fail("تعریف مرحله معتبر نیست.")
        code = stage["code"]
        name = stage["display_name_fa"]
        sequence = stage["sequence"]
        active = stage["active"]
        required = stage["required_for_completion"]
        if code not in CANONICAL_STAGE_CODES or code in seen_codes:
            fail("کد مرحله استاندارد یا یکتا نیست.")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 160:
            fail("نام فارسی مرحله معتبر نیست.")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or sequence in seen_sequences:
            fail("ترتیب مراحل باید مثبت و یکتا باشد.")
        if type(active) is not bool or type(required) is not bool or (required and not active):
            fail("فعال‌بودن و الزام مرحله معتبر نیست.")
        seen_codes.add(code); seen_sequences.add(sequence)
        normalized.append({"code": code, "display_name_fa": name.strip(), "sequence": sequence,
                           "is_active": active, "required_for_completion": required})
    if seen_codes != set(CANONICAL_STAGE_CODES) or seen_sequences != set(range(1, len(CANONICAL_STAGE_CODES) + 1)):
        fail("پنج مرحله استاندارد باید ترتیب پیوسته ۱ تا ۵ داشته باشند.")
    return expected, _instant(payload["effective_from"]), normalized


def save_configuration(user, payload, key):
    organization_id = admin_context(user)
    expected, effective, values = _validated_configuration(payload)
    db.session.scalar(select(OperationalOrganization).where(
        OperationalOrganization.id == organization_id,
    ).with_for_update())
    db.session.scalar(select(ExpertUser).where(
        ExpertUser.id == user["id"],
    ).with_for_update().execution_options(populate_existing=True))
    db.session.scalars(select(OperationalMembership).where(
        OperationalMembership.user_id == user["id"],
    ).order_by(OperationalMembership.id).with_for_update()).all()
    db.session.expire_all()
    admin_context(user)
    command, request_hash = routes._idempotency(
        organization_id, "shipment.stage.configuration", "OrganizationShipmentStagePolicy",
        organization_id, key, {"actor": user["id"], **payload},
    )
    if command:
        return db.session.get(PolicyVersion, command.result_resource_id), False
    policy = db.session.scalar(select(Policy).where(Policy.organization_id == organization_id))
    latest = db.session.scalar(select(PolicyVersion).where(
        PolicyVersion.organization_id == organization_id,
    ).order_by(PolicyVersion.version.desc()).limit(1))
    if expected != (latest.version if latest else 0):
        fail("پیکربندی مراحل تغییر کرده است؛ دوباره بخوانید.", 409, "STALE_SHIPMENT_STAGE_CONFIGURATION")
    now = utcnow()
    if effective > now and not latest:
        pass
    elif latest and (effective <= times.aware(latest.effective_from) or effective < now):
        fail("نسخه بعدی باید در آینده و پس از نسخه قبلی فعال شود.")
    if policy is None:
        policy = Policy(organization_id=organization_id)
        db.session.add(policy); db.session.flush()
    row = PolicyVersion(
        organization_id=organization_id,
        policy_id=policy.id,
        version=(latest.version + 1 if latest else 1),
        effective_from=effective,
        actor_user_id=int(user["id"]),
    )
    db.session.add(row); db.session.flush()
    existing = {definition.code: definition for definition in db.session.scalars(select(Definition).where(
        Definition.organization_id == organization_id,
    )).all()}
    for value in values:
        definition = existing.get(value["code"])
        if definition is None:
            definition = Definition(organization_id=organization_id, code=value["code"])
            db.session.add(definition); db.session.flush()
            existing[value["code"]] = definition
        db.session.add(DefinitionVersion(
            organization_id=organization_id,
            policy_version_id=row.id,
            definition_id=definition.id,
            display_name_fa=value["display_name_fa"],
            sequence=value["sequence"],
            is_active=value["is_active"],
            required_for_completion=value["required_for_completion"],
        ))
    db.session.flush()
    routes._reserve_idempotency(
        organization_id, "shipment.stage.configuration", "OrganizationShipmentStagePolicy",
        organization_id, key, request_hash, row.id,
    )
    base._audit(organization_id, int(user["id"]), "shipment_stage.configuration.published", "OrganizationShipmentStagePolicyVersion", row.id)
    return row, True


def _instance_and_version(shipment):
    instance = db.session.scalar(select(StageInstance).where(
        StageInstance.operational_shipment_id == shipment.id,
        StageInstance.organization_id == shipment.organization_id,
    ))
    version = db.session.get(PolicyVersion, instance.policy_version_id) if instance else applicable(shipment.organization_id)
    return instance, version


def _event_rows(instance):
    if instance is None:
        return []
    return db.session.scalars(select(StageEvent).where(
        StageEvent.instance_id == instance.id,
        StageEvent.organization_id == instance.organization_id,
    ).order_by(StageEvent.occurred_at, StageEvent.recorded_at, StageEvent.id)).all()


def _projection(shipment, user=None):
    instance, version = _instance_and_version(shipment)
    events = _event_rows(instance)
    by_definition = {}
    for event in events:
        by_definition.setdefault(event.definition_version_id, {})[event.event_type] = event
    stages = []
    for item, definition in _definitions(version, active_only=True):
        values = by_definition.get(item.id, {})
        started = values.get("STARTED")
        completed = values.get("COMPLETED")
        stages.append({
            "public_id": definition.public_id,
            "configuration_public_id": item.public_id,
            "code": definition.code,
            "display_name_fa": item.display_name_fa,
            "sequence": item.sequence,
            "active": item.is_active,
            "required_for_completion": item.required_for_completion,
            "status": "COMPLETED" if completed else "STARTED" if started else "NOT_STARTED",
            "started_at": times.aware(started.occurred_at).isoformat() if started else None,
            "completed_at": times.aware(completed.occurred_at).isoformat() if completed else None,
        })
    return {
        "configuration": _version_view(version) if version else None,
        "pinned": instance is not None,
        "instance_public_id": instance.public_id if instance else None,
        "stages": stages,
        "can_record": bool(user is not None and _can_record(user, shipment) and shipment.lifecycle_status != "closed"),
        "project_required": False,
    }, instance, version, events


def read(shipment_public_id, user):
    shipment = base.scoped_shipment(shipment_public_id, user)
    return _projection(shipment, user)[0]


def completion_state(shipment):
    projection, instance, version, events = _projection(shipment)
    if version is None:
        return "UNKNOWN", {"policy_version": None, "instance": None, "required": [], "events": []}
    required = [stage for stage in projection["stages"] if stage["required_for_completion"]]
    state = "PASS" if all(stage["status"] == "COMPLETED" for stage in required) else "FAIL"
    facts = {
        "policy_version": [version.id, version.version, times.aware(version.effective_from).isoformat()],
        "instance": [instance.id, instance.public_id] if instance else None,
        "required": [[stage["configuration_public_id"], stage["code"], stage["sequence"], stage["status"]] for stage in required],
        "events": [[event.id, event.event_type, times.aware(event.occurred_at).isoformat()] for event in events],
    }
    return state, facts


def record_event(shipment_public_id, definition_public_id, user, payload, key):
    shipment = base.scoped_shipment(shipment_public_id, user)
    if not _can_record(user, shipment):
        fail("فقط کارشناس مسئول محموله می‌تواند پیشرفت مرحله را ثبت کند.", 403, "SHIPMENT_STAGE_EVENT_FORBIDDEN")
    fields = {"event_type", "occurred_at", "expected_policy_version_public_id"}
    if not isinstance(payload, dict) or set(payload) != fields or payload["event_type"] not in {"STARTED", "COMPLETED"}:
        fail("فرمان مرحله معتبر نیست.")
    occurred_at = _instant(payload["occurred_at"])
    if occurred_at > utcnow():
        fail("زمان رخداد مرحله نمی‌تواند در آینده باشد.")
    definition_identity = _uuid(definition_public_id)
    shipment = db.session.scalar(select(OperationalShipment).where(
        OperationalShipment.id == shipment.id,
    ).with_for_update().execution_options(populate_existing=True))
    if not _can_record(user, shipment):
        fail("اختیار ثبت مرحله تغییر کرده است.", 403, "SHIPMENT_STAGE_EVENT_FORBIDDEN")
    if occurred_at < times.aware(shipment.created_at):
        fail("زمان رخداد مرحله نمی‌تواند پیش از ایجاد محموله باشد.")
    closure_guard.deny_new(shipment)
    command, request_hash = routes._idempotency(
        shipment.organization_id, "shipment.stage.event", "OperationalShipment",
        shipment.id, key, {"actor": user["id"], "definition": definition_identity, **payload},
    )
    if command:
        return db.session.get(StageEvent, command.result_resource_id), False
    instance, version = _instance_and_version(shipment)
    if version is None:
        fail("هنوز پیکربندی فعال مراحل برای سازمان وجود ندارد.", 409, "SHIPMENT_STAGE_CONFIGURATION_MISSING")
    if payload["expected_policy_version_public_id"] != version.public_id:
        fail("پیکربندی مراحل تغییر کرده است؛ دوباره بخوانید.", 409, "STALE_SHIPMENT_STAGE_CONFIGURATION")
    if instance is None:
        instance = StageInstance(
            organization_id=shipment.organization_id,
            operational_shipment_id=shipment.id,
            policy_version_id=version.id,
            pinned_by_user_id=int(user["id"]),
        )
        db.session.add(instance); db.session.flush()
    definition = db.session.scalar(select(Definition).where(
        Definition.public_id == definition_identity,
        Definition.organization_id == shipment.organization_id,
    ))
    item = db.session.scalar(select(DefinitionVersion).where(
        DefinitionVersion.policy_version_id == version.id,
        DefinitionVersion.definition_id == definition.id if definition is not None else False,
        DefinitionVersion.is_active.is_(True),
    ))
    if item is None:
        fail("مرحله فعال در نسخه جاری یافت نشد.", 404, "SHIPMENT_STAGE_NOT_FOUND")
    rows = _definitions(version, active_only=True)
    previous = [candidate for candidate, _ in rows if candidate.sequence < item.sequence]
    events = _event_rows(instance)
    by_definition = {}
    for event in events:
        by_definition.setdefault(event.definition_version_id, {})[event.event_type] = event
    if any("COMPLETED" not in by_definition.get(candidate.id, {}) for candidate in previous):
        fail("مرحله‌های قبلی باید ابتدا کامل شوند.", 409, "SHIPMENT_STAGE_ORDER_VIOLATION")
    previous_completed = [by_definition[candidate.id]["COMPLETED"] for candidate in previous]
    if previous_completed and occurred_at < max(times.aware(event.occurred_at) for event in previous_completed):
        fail("زمان مرحله نمی‌تواند پیش از تکمیل مرحله قبلی باشد.")
    existing = by_definition.get(item.id, {})
    if payload["event_type"] == "STARTED":
        if existing:
            fail("این مرحله قبلاً شروع شده است.", 409, "SHIPMENT_STAGE_TRANSITION_CONFLICT")
    else:
        started = existing.get("STARTED")
        if started is None or "COMPLETED" in existing:
            fail("فقط مرحله شروع‌شده و ناتمام قابل تکمیل است.", 409, "SHIPMENT_STAGE_TRANSITION_CONFLICT")
        if occurred_at < times.aware(started.occurred_at):
            fail("زمان تکمیل نمی‌تواند پیش از زمان شروع باشد.")
    row = StageEvent(
        organization_id=shipment.organization_id,
        operational_shipment_id=shipment.id,
        instance_id=instance.id,
        policy_version_id=version.id,
        definition_version_id=item.id,
        event_type=payload["event_type"],
        actor_user_id=int(user["id"]),
        occurred_at=occurred_at,
        idempotency_key=key.strip() if isinstance(key, str) else key,
        request_hash=request_hash,
    )
    db.session.add(row); db.session.flush()
    routes._reserve_idempotency(
        shipment.organization_id, "shipment.stage.event", "OperationalShipment",
        shipment.id, key, request_hash, row.id,
    )
    base._audit(shipment.organization_id, int(user["id"]), f"shipment_stage.{payload['event_type'].lower()}", "ShipmentOperationalStageEvent", row.id)
    base._outbox(shipment.organization_id, f"shipment_stage.{payload['event_type'].lower()}", "OperationalShipment", shipment.id)
    return row, True

