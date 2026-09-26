"""Authenticated application boundary for ADR-069's narrowly fenced command."""
from datetime import timezone
from uuid import uuid4
import json

from flask import current_app
from sqlalchemy import select, func, inspect, text, update
from sqlalchemy.exc import DBAPIError
from backend.extensions import db
from backend.census_context import ensure_census_context
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership as Membership, OperationalOrganization as Organization
from backend.operational_models import OperationalShipment as Shipment, OperationalWorkItem as Work, utcnow
from backend.owner_transfer_models import ShipmentOwnerTransfer as Transfer
from backend.services import operational_service as base

CAPABILITY = "TRANSFER_OWNER"
FUNCTION = "public.transfer_shipment_owner(bigint,bigint,bigint,bigint,bigint,integer,text,text,bigint,jsonb)"


def fail(code, message, status=422):
    raise base.OperationalError(code, message, status)


def _admin_org(user):
    """Bind trusted session identity to current exact Admin/tenant authority."""
    try:
        actor_id = int(user["id"])
    except (KeyError, TypeError, ValueError):
        fail("OWNER_TRANSFER_FORBIDDEN", "فقط مدیر فعال همین سازمان مجاز به انتقال مسئول است.", 403)
    actor = db.session.scalar(select(ExpertUser).where(ExpertUser.id == actor_id).execution_options(populate_existing=True))
    if not actor or not actor.is_active or actor.authority != "ORGANIZATION_ADMIN":
        fail("OWNER_TRANSFER_FORBIDDEN", "فقط مدیر فعال همین سازمان مجاز به انتقال مسئول است.", 403)
    memberships = db.session.execute(select(Membership, Organization).join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == actor_id, Membership.is_active.is_(True)).execution_options(populate_existing=True)).all()
    if len(memberships) != 1 or not memberships[0][1].is_active:
        fail("OWNER_TRANSFER_FORBIDDEN", "سازمان فعال و یکتای مدیر مشخص نیست.", 403)
    return int(memberships[0][0].organization_id)


def _can_transfer(user, shipment):
    try:
        return _admin_org(user) == shipment.organization_id
    except base.OperationalError:
        return False


def _sqlite_adapter_available():
    if db.engine.dialect.name != "sqlite" or not current_app.config.get("TESTING"):
        return False
    if inspect(db.session.connection()).has_table("alembic_version"):
        return False
    return db.session.execute(text("SELECT count(*) FROM sqlite_master WHERE type='trigger' AND name='trg_operational_shipment_fixed_owner'")).scalar() == 0


def database_ready():
    """No PostgreSQL TESTING bypass: unsafe/schema-owner runtime fails closed."""
    if db.engine.dialect.name != "postgresql":
        return _sqlite_adapter_available()
    return bool(db.session.execute(text("""SELECT EXISTS (
      SELECT 1 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_roles owner ON owner.oid=p.proowner
      JOIN pg_catalog.pg_roles runtime ON runtime.rolname=current_user
      WHERE p.oid=pg_catalog.to_regprocedure(:function) AND p.prosecdef
        AND owner.rolname='forwarder_owner_transfer_owner'
        AND NOT (owner.rolcanlogin OR owner.rolinherit OR owner.rolsuper OR owner.rolcreatedb OR owner.rolcreaterole OR owner.rolreplication OR owner.rolbypassrls)
        AND p.proconfig @> ARRAY['search_path=pg_catalog, pg_temp']::text[]
        AND NOT (runtime.rolsuper OR runtime.rolcreatedb OR runtime.rolcreaterole OR runtime.rolreplication OR runtime.rolbypassrls)
        AND pg_catalog.has_function_privilege(current_user,p.oid,'EXECUTE')
        AND NOT pg_catalog.pg_has_role(current_user,owner.oid,'MEMBER')
        AND NOT pg_catalog.has_schema_privilege(current_user,'public','CREATE')
        AND NOT pg_catalog.has_schema_privilege(owner.oid,'public','CREATE')
        AND NOT pg_catalog.has_table_privilege(current_user,'public.shipment_owner_transfer','TRUNCATE')
        AND NOT pg_catalog.has_table_privilege(current_user,'public.shipment_owner_transfer','TRIGGER')
        AND NOT pg_catalog.has_table_privilege(current_user,'public.operational_shipment','TRIGGER')
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles privileged
          WHERE (privileged.rolsuper OR privileged.rolcreaterole OR privileged.rolcreatedb OR privileged.rolbypassrls)
            AND pg_catalog.pg_has_role(current_user,privileged.oid,'MEMBER'))
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_auth_members m WHERE m.roleid=owner.oid OR m.member=owner.oid)
        AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_class c WHERE c.oid IN
          ('public.operational_shipment'::regclass,'public.shipment_owner_transfer'::regclass)
          AND pg_catalog.pg_has_role(current_user,c.relowner,'MEMBER'))
    )"""), {"function": FUNCTION}).scalar())


def _page(value):
    try:
        result = int(value)
        if isinstance(value, bool) or result < 1 or result > 10000: raise ValueError()
        return result
    except (TypeError, ValueError):
        fail("OWNER_TRANSFER_INVALID", "شماره صفحه معتبر نیست.")


def _iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value.tzinfo is None else value.astimezone(timezone.utc).isoformat()


def _person(identity, label):
    return {"id": identity, "display_name": label}


def projection(row):
    return {"public_id": row.public_id, "sequence": row.sequence_number,
        "old_owner": _person(row.old_owner_id, row.old_owner_label),
        "new_owner": _person(row.new_owner_id, row.new_owner_label),
        "actor": _person(row.actor_user_id, row.actor_label), "reason": row.reason,
        "occurred_at": _iso(row.occurred_at), "recorded_at": _iso(row.recorded_at),
        "previous_shipment_version": row.previous_shipment_version, "next_shipment_version": row.next_shipment_version}


def _history(shipment):
    return select(Transfer).where(Transfer.operational_shipment_id == shipment.id, Transfer.organization_id == shipment.organization_id)


def read(shipment_id, user, page=1):
    shipment = base.scoped_shipment(shipment_id, user)
    expected = (shipment.primary_responsible_expert_id, shipment.version)
    page = _page(page)
    rows = db.session.scalars(_history(shipment).order_by(Transfer.sequence_number.desc()).offset((page-1)*20).limit(21)).all()
    first = db.session.scalar(_history(shipment).order_by(Transfer.sequence_number).limit(1))
    owner = db.session.scalar(select(ExpertUser).where(ExpertUser.id == shipment.primary_responsible_expert_id).execution_options(populate_existing=True))
    if owner is None:
        fail("OWNER_TRANSFER_PREDECESSOR_INVALID", "مسئول فعلی پرونده قابل تأیید نیست.", 409)
    can_transfer = _can_transfer(user, shipment)
    initial = _person(first.old_owner_id, first.old_owner_label) if first else _person(owner.id, owner.full_name)
    initial.update(provenance="FIRST_TRANSFER_PREDECESSOR" if first else "PERSISTED_OWNER_WITHOUT_TRANSFER", occurred_at=None)
    result = {"shipment_public_id": shipment.public_id, "shipment_version": shipment.version,
        "current_owner": _person(owner.id, owner.full_name), "initial_owner": initial,
        "transfers": [projection(row) for row in rows[:20]], "page": page, "has_more": len(rows)>20,
        "capabilities": {CAPABILITY: can_transfer}, "available": database_ready() if can_transfer else False,
        "old_owner_open_work_count": int(db.session.scalar(select(func.count(Work.id)).where(
            Work.organization_id == shipment.organization_id, Work.operational_shipment_id == shipment.id,
            Work.status == "open", Work.assignee_user_id == shipment.primary_responsible_expert_id)) or 0) if can_transfer else None}
    # A pure read can span a committed transfer. Do not combine its new history
    # with a stale owner authorization from the start of this request.
    current = base.scoped_shipment(shipment_id, user)
    if expected != (current.primary_responsible_expert_id, current.version):
        fail("OWNER_TRANSFER_STALE", "مسئول یا نسخه پرونده تغییر کرده است؛ دوباره بررسی کنید.", 409)
    return result


def _candidate_query(org):
    membership_count = select(func.count(Membership.id)).join(Organization, Organization.id == Membership.organization_id).where(
        Membership.user_id == ExpertUser.id, Membership.is_active.is_(True), Organization.is_active.is_(True)).correlate(ExpertUser).scalar_subquery()
    same_org = select(Membership.id).join(Organization, Organization.id == Membership.organization_id).where(
        Membership.user_id == ExpertUser.id, Membership.organization_id == org,
        Membership.is_active.is_(True), Organization.is_active.is_(True)).correlate(ExpertUser).exists()
    return select(ExpertUser.id, ExpertUser.full_name).where(ExpertUser.is_active.is_(True),
        func.upper(ExpertUser.authority) == "EXPERT", membership_count == 1, same_org)


def candidates(shipment_id, user, search="", page=1):
    org = _admin_org(user)
    shipment = base.scoped_shipment(shipment_id, user)
    if shipment.organization_id != org:
        fail("OWNER_TRANSFER_FORBIDDEN", "انتقال مسئول در این سازمان مجاز نیست.", 403)
    page = _page(page)
    if not isinstance(search, str) or len(search) > 100:
        fail("OWNER_TRANSFER_INVALID", "عبارت جست‌وجو معتبر نیست.")
    query = _candidate_query(org).where(ExpertUser.id != shipment.primary_responsible_expert_id)
    if search.strip():
        query = query.where(ExpertUser.full_name.icontains(search.strip(), autoescape=True))
    rows = db.session.execute(query.order_by(ExpertUser.full_name, ExpertUser.id).offset((page-1)*50).limit(51)).all()
    return {"candidates": [_person(row.id, row.full_name) for row in rows[:50]], "page": page, "has_more": len(rows)>50}


def _command(payload, key):
    fields = {"expected_owner_id", "target_owner_id", "expected_version", "reason"}
    if not isinstance(payload, dict) or set(payload) != fields:
        fail("OWNER_TRANSFER_INVALID", "فیلدهای انتقال مسئول معتبر نیست.")
    if any(type(payload[name]) is not int or payload[name] < 1 for name in fields-{"reason"}):
        fail("OWNER_TRANSFER_INVALID", "مسئول فعلی، مسئول جدید و نسخه پرونده لازم است.")
    reason = payload["reason"]
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 1000:
        fail("OWNER_TRANSFER_INVALID", "دلیل انتقال، حداکثر ۱۰۰۰ نویسه، لازم است.")
    if not isinstance(key, str) or not key.strip() or len(key.strip()) > 100:
        fail("OWNER_TRANSFER_INVALID", "شناسه یکتای اقدام لازم است.")
    return {**payload, "reason": reason.strip()}, key.strip()


def _sqlite_transfer(shipment, user, payload, key):
    """Only unmigrated create_all unit fixtures; never a production/PG fallback."""
    if not _sqlite_adapter_available():
        fail("OWNER_TRANSFER_UNAVAILABLE", "انتقال مسئول در این محیط آماده نیست.", 503)
    org, actor_id, target_id = shipment.organization_id, int(user["id"]), payload["target_owner_id"]
    db.session.scalar(select(Organization).where(Organization.id == org).with_for_update().execution_options(populate_existing=True))
    shipment = db.session.scalar(select(Shipment).where(Shipment.id == shipment.id).with_for_update().execution_options(populate_existing=True))
    db.session.scalars(select(ExpertUser).where(ExpertUser.id.in_([actor_id,target_id])).order_by(ExpertUser.id).with_for_update().execution_options(populate_existing=True)).all()
    db.session.scalars(select(Membership).where(Membership.user_id.in_([actor_id,target_id])).order_by(Membership.id).with_for_update().execution_options(populate_existing=True)).all()
    if _admin_org(user) != org:
        fail("OWNER_TRANSFER_FORBIDDEN", "مجوز مدیر تغییر کرده است.", 403)
    retained = db.session.scalar(_history(shipment).where(Transfer.idempotency_key == key))
    if retained:
        if (retained.actor_user_id,retained.old_owner_id,retained.new_owner_id,retained.previous_shipment_version,retained.reason) != (
            actor_id,payload["expected_owner_id"],target_id,payload["expected_version"],payload["reason"]):
            fail("OWNER_TRANSFER_KEY_CONFLICT", "شناسه این اقدام قبلاً برای درخواست دیگری استفاده شده است.", 409)
        return retained, False
    target = db.session.execute(_candidate_query(org).where(ExpertUser.id == target_id)).one_or_none()
    if target is None:
        fail("OWNER_TRANSFER_TARGET_INVALID", "مسئول جدید باید کارشناس حمل فعال همین سازمان باشد.")
    if target_id == payload["expected_owner_id"]:
        fail("OWNER_TRANSFER_UNCHANGED", "مسئول جدید باید با مسئول فعلی متفاوت باشد.")
    if (shipment.primary_responsible_expert_id, shipment.version) != (payload["expected_owner_id"],payload["expected_version"]):
        fail("OWNER_TRANSFER_STALE", "مسئول یا نسخه پرونده تغییر کرده است؛ دوباره بررسی کنید.", 409)
    previous = db.session.scalar(_history(shipment).order_by(Transfer.sequence_number.desc()).limit(1))
    if previous and (previous.new_owner_id != shipment.primary_responsible_expert_id or previous.next_shipment_version > shipment.version):
        fail("OWNER_TRANSFER_CHAIN_INVALID", "سابقه مسئولیت با وضعیت فعلی سازگار نیست.", 409)
    old = db.session.get(ExpertUser,shipment.primary_responsible_expert_id)
    actor = db.session.get(ExpertUser,actor_id)
    now = utcnow()
    values = {"public_id":str(uuid4()), "organization_id":org, "operational_shipment_id":shipment.id,
        "old_owner_id":old.id, "new_owner_id":target.id, "actor_user_id":actor_id,
        "old_owner_label":old.full_name, "new_owner_label":target.full_name, "actor_label":actor.full_name,
        "reason":payload["reason"], "occurred_at":now, "recorded_at":now,
        "sequence_number":previous.sequence_number+1 if previous else 1,
        "previous_shipment_version":shipment.version, "next_shipment_version":shipment.version+1,
        "previous_transfer_id":previous.id if previous else None, "idempotency_key":key}
    identity = db.session.execute(Transfer.__table__.insert().values(**values)).inserted_primary_key[0]
    db.session.execute(update(Shipment).where(Shipment.id == shipment.id).values(
        primary_responsible_expert_id=target.id, version=values["next_shipment_version"],updated_at=now).execution_options(synchronize_session=False))
    metadata = {"transfer_public_id":values["public_id"], "old_owner_id":old.id, "new_owner_id":target.id,
        "previous_version":values["previous_shipment_version"],"next_version":values["next_shipment_version"],"sequence":values["sequence_number"]}
    base._audit(org,actor_id,"shipment.owner_transferred","OperationalShipment",shipment.id,metadata)
    base._outbox(org,"shipment.owner_transferred","OperationalShipment",shipment.id,metadata)
    db.session.flush()
    db.session.expire(shipment)
    return db.session.get(Transfer,identity), True


def transfer(shipment_id, user, payload, key):
    org = _admin_org(user)
    shipment = base.scoped_shipment(shipment_id, user)
    if org != shipment.organization_id:
        fail("OWNER_TRANSFER_FORBIDDEN", "انتقال مسئول در این سازمان مجاز نیست.", 403)
    payload,key = _command(payload,key)
    if not database_ready():
        fail("OWNER_TRANSFER_UNAVAILABLE", "انتقال مسئول در این محیط آماده نیست.", 503)
    census = ensure_census_context(db.session)
    if db.engine.dialect.name == "sqlite":
        return _sqlite_transfer(shipment,user,payload,key)
    previous = db.session.scalar(_history(shipment).order_by(Transfer.sequence_number.desc()).limit(1))
    try:
        result = db.session.execute(text("""SELECT * FROM public.transfer_shipment_owner(
            :org,:shipment,:actor,:target,:owner,:version,:reason,:key,:previous,CAST(:census AS jsonb))"""),
            {"org":org,"shipment":shipment.id,"actor":int(user["id"]),"target":payload["target_owner_id"],
             "owner":payload["expected_owner_id"],"version":payload["expected_version"],"reason":payload["reason"],"key":key,
             "previous":previous.id if previous else None,
             "census":json.dumps({"census_id":census.census_id,"cache_version":census.cache_version,"cache_token":census.cache_token})}).one()
    except DBAPIError as exc:
        code = getattr(getattr(exc.orig,"diag",None),"message_primary","")
        state = getattr(exc.orig,"sqlstate",getattr(exc.orig,"pgcode",None))
        known = {"OWNER_TRANSFER_INVALID","OWNER_TRANSFER_TENANT_INVALID","OWNER_TRANSFER_SHIPMENT_INVALID",
            "OWNER_TRANSFER_ACTOR_INVALID","OWNER_TRANSFER_KEY_CONFLICT","OWNER_TRANSFER_TARGET_INVALID",
            "OWNER_TRANSFER_UNCHANGED","OWNER_TRANSFER_STALE","OWNER_TRANSFER_CHAIN_INVALID","OWNER_TRANSFER_PREDECESSOR_INVALID"}
        if state == "P0001" and code in known:
            status = 403 if code == "OWNER_TRANSFER_ACTOR_INVALID" else 404 if code in {"OWNER_TRANSFER_TENANT_INVALID","OWNER_TRANSFER_SHIPMENT_INVALID"} else 422 if code in {"OWNER_TRANSFER_INVALID","OWNER_TRANSFER_TARGET_INVALID","OWNER_TRANSFER_UNCHANGED"} else 409
            fail(code,"انتقال انجام نشد؛ مجوز، مسئول انتخاب‌شده و وضعیت فعلی پرونده را دوباره بررسی کنید.",status)
        if state in {"40001","40P01","23505","23514"}:
            fail("OWNER_TRANSFER_CONFLICT","اطلاعات هم‌زمان تغییر کرد؛ دوباره بررسی کنید.",409)
        raise
    db.session.expire(shipment)
    return db.session.get(Transfer,result.transfer_id), bool(result.created)
