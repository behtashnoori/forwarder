"""Cargo delivery commands, immutable history and scoped read projections."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID
import hashlib
import json

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import aliased
from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem
from backend.delivery_models import CargoDelivery as Delivery, CargoDeliveryEvidence as Evidence
from backend.document_context_models import OperationalDocumentContext as Context
from backend.models import CaseDocumentFile, Customer, ExpertUser, UnitOfMeasure
from backend.operational_models import OperationalIdempotency, OperationalShipment
from backend.services.assigned_work_authorization import authorize_document_management
from backend.services.customer_entitlement_service import authorized_customer_ids
from backend.services.legacy_datetime import serialize_legacy_utc_datetime as iso
from backend.services.operational_service import OperationalError, require_permission, scoped_shipment

FIELDS = {"cargo_public_id", "quantity", "uom_public_id", "destination_text", "occurred_at",
          "expected_version", "corrects_public_id", "reason", "evidence_document_public_ids"}


from backend.services import closure_commands as closure_guard


def fail(message, status=422, code="DELIVERY_INVALID"):
    raise OperationalError(code, message, status)


def _text(value, limit, required=False):
    if value is None and not required:
        return None
    if not isinstance(value, str) or len(value.strip()) > limit or (required and not value.strip()):
        fail("متن تحویل معتبر نیست.")
    return value.strip() or None


def _identity(value):
    try:
        if not isinstance(value, str): raise ValueError()
        return str(UUID(value))
    except ValueError:
        fail("شناسه تحویل یا کالا معتبر نیست.")


def _instant(value):
    try:
        if not isinstance(value, str): raise ValueError()
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None: raise ValueError()
        return result.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        fail("زمان وقوع تحویل با منطقه زمانی لازم است.")


def _quantity(value):
    try:
        if isinstance(value, bool): raise InvalidOperation()
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        fail("مقدار تحویل باید عدد مثبت باشد.")
    if not result.is_finite() or result <= 0 or result.as_tuple().exponent < -6 or result > Decimal("999999999999.999999"):
        fail("مقدار یا دقت تحویل معتبر نیست.")
    return result


def _can_manage(user, shipment):
    try:
        require_permission(user, "operational_shipment.create")
        return authorize_document_management(user, shipment).allowed
    except OperationalError:
        return False


def _owner(cargo, shipment):
    owner = db.session.get(Customer, cargo.cargo_owner_customer_id) if cargo.cargo_owner_customer_id else None
    return owner if owner and owner.ownership_scope == "TENANT" and owner.operational_organization_id == shipment.organization_id else None


def current_predicate():
    successor = aliased(Delivery)
    return ~select(successor.id).where(successor.supersedes_delivery_id == Delivery.id).correlate(Delivery).exists()


def attach_evidence(delivery, document, actor_id):
    """Called only inside authorized Delivery or existing document transactions."""
    from backend.services.case_document_service import DocumentError
    if (delivery is None or document.status != "active" or document.owner_type != "SHIPMENT"
            or document.operational_shipment_id != delivery.operational_shipment_id
            or document.operational_organization_id != delivery.organization_id):
        raise DocumentError("مدرک متعلق به این تحویل نیست", 404, "DELIVERY_EVIDENCE_NOT_FOUND")
    existing = db.session.get(Evidence, (delivery.id, document.id))
    if existing is None:
        db.session.add(Evidence(delivery_id=delivery.id, document_file_id=document.id,
            operational_shipment_id=delivery.operational_shipment_id, organization_id=delivery.organization_id,
            actor_user_id=actor_id))
        db.session.flush()


def _evidence_selection(shipment, cargo, identities):
    if not isinstance(identities, list) or len(identities) > 20 or any(not isinstance(x, str) for x in identities) or len(set(identities)) != len(identities):
        fail("فهرست مدارک تحویل معتبر نیست.")
    identities = [_identity(x) for x in identities]
    linked_delivery = select(Delivery.id).where(Delivery.id == Context.delivery_id,
        Delivery.cargo_item_id == cargo.id, Delivery.organization_id == shipment.organization_id).exists()
    rows = db.session.scalars(select(CaseDocumentFile).join(Context, Context.document_file_id == CaseDocumentFile.id).where(
        CaseDocumentFile.public_id.in_(identities), CaseDocumentFile.status == "active",
        CaseDocumentFile.owner_type == "SHIPMENT", CaseDocumentFile.operational_shipment_id == shipment.id,
        CaseDocumentFile.operational_organization_id == shipment.organization_id,
        Context.operational_shipment_id == shipment.id, Context.organization_id == shipment.organization_id,
        or_(and_(Context.context_type == "CARGO", Context.cargo_item_id == cargo.id),
            and_(Context.context_type == "DELIVERY", linked_delivery))).with_for_update()).all() if identities else []
    if len(rows) != len(identities):
        fail("مدرک جاری برای این کالا یافت نشد.", 404, "DELIVERY_EVIDENCE_NOT_FOUND")
    return rows


def create(shipment_public_id, user, payload, key):
    shipment = scoped_shipment(shipment_public_id, user)
    if not _can_manage(user, shipment):
        fail("فقط کارشناس مسئول می‌تواند تحویل را ثبت یا اصلاح کند.", 403, "DELIVERY_FORBIDDEN")
    shipment = db.session.scalar(select(OperationalShipment).where(OperationalShipment.id == shipment.id)
        .with_for_update().execution_options(populate_existing=True))
    if not _can_manage(user, shipment):
        fail("اختیار ثبت تحویل تغییر کرده است.", 403, "DELIVERY_FORBIDDEN")
    if not isinstance(payload, dict) or set(payload) - FIELDS:
        fail("اطلاعات تحویل معتبر نیست.")
    if not isinstance(key, str) or not key.strip() or len(key.strip()) > 100:
        fail("شناسه امن درخواست لازم است.")
    key = key.strip()
    fingerprint = hashlib.sha256(json.dumps({"actor": int(user["id"]), "payload": payload}, sort_keys=True).encode()).hexdigest()
    replay = db.session.scalar(select(OperationalIdempotency).where(
        OperationalIdempotency.organization_id == shipment.organization_id,
        OperationalIdempotency.operation == "record_cargo_delivery", OperationalIdempotency.resource_type == "shipment",
        OperationalIdempotency.command_resource_id == shipment.id, OperationalIdempotency.idempotency_key == key))
    if replay:
        if replay.request_hash != fingerprint:
            fail("شناسه درخواست برای تحویل دیگری استفاده شده است.", 409, "DELIVERY_REPLAY_CONFLICT")
        return db.session.get(Delivery, replay.result_resource_id), False
    cargo = db.session.scalar(select(ShipmentCargoItem).where(
        ShipmentCargoItem.public_id == _identity(payload.get("cargo_public_id")),
        ShipmentCargoItem.operational_shipment_id == shipment.id).with_for_update().execution_options(populate_existing=True))
    if cargo is None:
        fail("کالا یافت نشد.", 404, "DELIVERY_CARGO_NOT_FOUND")
    if _owner(cargo, shipment) is None:
        fail("ابتدا مشتری واقعی کالا را در اطلاعات کالا مشخص کنید.", 422, "DELIVERY_CUSTOMER_UNKNOWN")
    uom = db.session.get(UnitOfMeasure, cargo.uom_id)
    if not uom or payload.get("uom_public_id") != uom.public_id:
        fail("واحد تحویل باید همان واحد کالای ثبت‌شده باشد.", 422, "DELIVERY_UOM_MISMATCH")
    expected = payload.get("expected_version")
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
        fail("نسخه تحویل لازم است.")
    previous = None
    if payload.get("corrects_public_id") is not None:
        previous = db.session.scalar(select(Delivery).where(
            Delivery.public_id == _identity(payload["corrects_public_id"]), Delivery.cargo_item_id == cargo.id,
            Delivery.operational_shipment_id == shipment.id, Delivery.organization_id == shipment.organization_id))
        if previous is None:
            fail("تحویل قبلی یافت نشد.", 404, "DELIVERY_NOT_FOUND")
        if expected != previous.revision or db.session.scalar(select(Delivery.id).where(Delivery.supersedes_delivery_id == previous.id).limit(1)):
            fail("تحویل قبلاً اصلاح شده است؛ نسخه جاری را دوباره بخوانید.", 409, "DELIVERY_VERSION_CONFLICT")
    elif expected != 0:
        fail("نسخه تحویل تازه معتبر نیست.", 409, "DELIVERY_VERSION_CONFLICT")
    documents = _evidence_selection(shipment, cargo, payload.get("evidence_document_public_ids", []))
    closure_guard.prior_fact(shipment, _instant(payload.get("occurred_at")))
    row = Delivery(organization_id=shipment.organization_id, operational_shipment_id=shipment.id, cargo_item_id=cargo.id,
        quantity=_quantity(payload.get("quantity")), uom_id=cargo.uom_id, uom_code_snapshot=cargo.uom_code_snapshot,
        uom_symbol_snapshot=cargo.uom_symbol_snapshot, destination_text=_text(payload.get("destination_text"), 255, True),
        occurred_at=_instant(payload.get("occurred_at")), actor_user_id=int(user["id"]),
        supersedes_delivery_id=previous.id if previous else None, revision=previous.revision + 1 if previous else 1,
        reason=_text(payload.get("reason"), 500))
    db.session.add(row); db.session.flush()
    for document in documents: attach_evidence(row, document, int(user["id"]))
    db.session.add(OperationalIdempotency(organization_id=shipment.organization_id, operation="record_cargo_delivery",
        resource_type="shipment", command_resource_id=shipment.id, idempotency_key=key,
        request_hash=fingerprint, result_resource_id=row.id))
    db.session.flush()
    return row, True


def summaries(shipment, cargo):
    ids = [c.id for c in cargo]
    totals = dict(db.session.execute(select(Delivery.cargo_item_id, func.sum(Delivery.quantity)).where(
        Delivery.operational_shipment_id == shipment.id, Delivery.organization_id == shipment.organization_id,
        Delivery.cargo_item_id.in_(ids), current_predicate()).group_by(Delivery.cargo_item_id)).all())
    result = []
    for row in cargo:
        total = totals.get(row.id, Decimal("0")); actual = row.actual_quantity
        remaining = max(actual - total, Decimal("0")) if actual is not None else None
        excess = max(total - actual, Decimal("0")) if actual is not None else None
        owner = _owner(row, shipment); uom = db.session.get(UnitOfMeasure, row.uom_id)
        result.append({"public_id": row.public_id, "label": row.display_name_snapshot,
            "customer_label": (owner.company_name or owner.first_name or "مشتری") if owner else "مشتری نامشخص",
            "uom_public_id": uom.public_id, "uom_symbol": row.uom_symbol_snapshot,
            "known_actual": str(actual) if actual is not None else None, "delivered": str(total),
            "remaining": str(remaining) if remaining is not None else None,
            "excess": str(excess) if excess is not None else None, "has_delivery": row.id in totals,
            "can_record": owner is not None})
    return result


def evidence_projection(delivery, account=None):
    from backend.services.case_document_service import customer_download_name
    query = select(CaseDocumentFile).join(Evidence, Evidence.document_file_id == CaseDocumentFile.id).where(
        Evidence.delivery_id == delivery.id, Evidence.organization_id == delivery.organization_id,
        CaseDocumentFile.operational_shipment_id == delivery.operational_shipment_id,
        CaseDocumentFile.operational_organization_id == delivery.organization_id)
    if account is not None:
        from backend.services.document_context_service import customer_context_predicate
        query = query.join(Context, Context.document_file_id == CaseDocumentFile.id).where(
            CaseDocumentFile.status == "active", customer_context_predicate(account))
    return [{"public_id": d.public_id, "filename": customer_download_name(d) if account is not None else d.original_filename, "version": d.version_number,
             "status": d.status} for d in db.session.scalars(query.order_by(CaseDocumentFile.id)).all()]


def project(row, superseded, *, account=None):
    result = {"public_id": row.public_id, "cargo_public_id": db.session.get(ShipmentCargoItem, row.cargo_item_id).public_id,
        "quantity": str(row.quantity), "uom_symbol": row.uom_symbol_snapshot, "destination_text": row.destination_text,
        "occurred_at": iso(row.occurred_at), "recorded_at": iso(row.recorded_at), "revision": row.revision,
        "status": "SUPERSEDED" if row.id in superseded else "CURRENT",
        "is_correction": row.supersedes_delivery_id is not None, "evidence": evidence_projection(row, account)}
    if account is None:
        actor = db.session.get(ExpertUser, row.actor_user_id)
        result.update(actor_label=(actor.full_name or actor.username) if actor else "کارشناس", reason=row.reason,
            corrects_public_id=db.session.get(Delivery, row.supersedes_delivery_id).public_id if row.supersedes_delivery_id else None)
    return result


def listing(shipment_public_id, user, page=1):
    shipment = scoped_shipment(shipment_public_id, user)
    try: page = max(1, int(page))
    except (ValueError, TypeError): fail("شماره صفحه معتبر نیست.")
    base = select(Delivery).where(Delivery.operational_shipment_id == shipment.id, Delivery.organization_id == shipment.organization_id)
    total = db.session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.session.scalars(base.order_by(Delivery.occurred_at.desc(), Delivery.recorded_at.desc(), Delivery.id.desc()).offset((page-1)*20).limit(20)).all()
    superseded = set(db.session.scalars(select(Delivery.supersedes_delivery_id).where(Delivery.supersedes_delivery_id.in_([r.id for r in rows]))).all())
    cargo = db.session.scalars(select(ShipmentCargoItem).where(ShipmentCargoItem.operational_shipment_id == shipment.id).order_by(ShipmentCargoItem.line_number)).all()
    return {"cargo": summaries(shipment, cargo), "items": [project(row, superseded) for row in rows],
            "page": page, "total": total, "can_manage": _can_manage(user, shipment)}


def customer_data(shipment, account, limit=50):
    """Capability support only; P3-09 owns the authenticated Customer surface."""
    if account.operational_organization_id != shipment.organization_id: return {"cargo": [], "items": []}
    allowed = select(ShipmentCargoItem).where(ShipmentCargoItem.operational_shipment_id == shipment.id,
        ShipmentCargoItem.cargo_owner_customer_id.in_(authorized_customer_ids(account)))
    cargo = db.session.scalars(allowed.order_by(ShipmentCargoItem.line_number)).all()
    rows = db.session.scalars(select(Delivery).where(Delivery.organization_id == shipment.organization_id,
        Delivery.operational_shipment_id == shipment.id, Delivery.cargo_item_id.in_(allowed.with_only_columns(ShipmentCargoItem.id)))
        .order_by(Delivery.occurred_at.desc(), Delivery.recorded_at.desc(), Delivery.id.desc()).limit(min(max(limit, 1), 100))).all()
    superseded = set(db.session.scalars(select(Delivery.supersedes_delivery_id).where(Delivery.supersedes_delivery_id.in_([r.id for r in rows]))).all())
    safe_cargo = [{k: v for k, v in row.items() if k not in {"can_record", "uom_public_id"}} for row in summaries(shipment, cargo)]
    return {"cargo": safe_cargo, "items": [project(row, superseded, account=account) for row in rows]}
