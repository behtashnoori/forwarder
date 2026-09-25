"""Typed P3-06 document context and exact-version visibility policy."""
from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select

from backend.extensions import db
from backend.document_context_models import (
    OperationalDocumentAudience,
    OperationalDocumentContext,
    OperationalDocumentContextEvent,
)
from backend.models import CaseDocumentFile, CustomerGamification
from backend.cargo_models import ShipmentCargoItem
from backend.delivery_models import CargoDelivery
from backend.operational_models import (
    ExecutionUnit, OperationalShipment, RouteLeg, RoutePlan, RouteStageExecution,
)
from backend.services.case_document_service import DocumentError
from backend.services.customer_entitlement_service import authorized_customer_ids
from backend.services.assigned_work_authorization import authorize_document_management


TARGET_COLUMNS = {
    "SHIPMENT": None,
    "CARGO": "cargo_item_id",
    "ROUTE_LEG": "route_leg_id",
    "EXECUTION_UNIT": "execution_unit_id",
    "DELIVERY": "delivery_id",
}
VISIBILITIES = frozenset({"INTERNAL", "CARGO_OWNER", "EXPLICIT_SHARED"})


def _target(shipment: OperationalShipment, context_type: str, public_id: str | None) -> tuple[int | None, str | None]:
    """Resolve a typed target from persisted tenant and Shipment lineage."""
    if context_type == "SHIPMENT":
        if public_id and public_id != shipment.public_id:
            raise DocumentError("زمینه سند متعلق به این محموله نیست", 404, "DOCUMENT_CONTEXT_NOT_FOUND")
        return None, shipment.public_id
    if not public_id or context_type not in TARGET_COLUMNS:
        raise DocumentError("زمینه سند معتبر نیست", 422, "DOCUMENT_CONTEXT_INVALID")
    if context_type == "CARGO":
        row = db.session.scalar(select(ShipmentCargoItem).where(
            ShipmentCargoItem.public_id == public_id,
            ShipmentCargoItem.operational_shipment_id == shipment.id,
        ))
    elif context_type == "DELIVERY":
        row = db.session.scalar(select(CargoDelivery).where(
            CargoDelivery.public_id == public_id,
            CargoDelivery.operational_shipment_id == shipment.id,
            CargoDelivery.organization_id == shipment.organization_id,
        ))
    elif context_type == "ROUTE_LEG":
        try:
            leg_id = int(public_id)
        except (TypeError, ValueError):
            raise DocumentError("مرحله مسیر یافت نشد", 404, "DOCUMENT_CONTEXT_NOT_FOUND") from None
        row = db.session.scalar(select(RouteLeg).join(
            RoutePlan, RoutePlan.id == RouteLeg.route_plan_id,
        ).where(RouteLeg.id == leg_id, RoutePlan.operational_shipment_id == shipment.id))
    else:
        row = db.session.scalar(select(ExecutionUnit).join(
            RouteStageExecution, RouteStageExecution.execution_unit_id == ExecutionUnit.id,
        ).join(
            RoutePlan, RoutePlan.id == RouteStageExecution.route_plan_id,
        ).where(
            ExecutionUnit.public_id == public_id,
            ExecutionUnit.organization_id == shipment.organization_id,
            RoutePlan.operational_shipment_id == shipment.id,
        ).limit(1))
    if row is None:
        raise DocumentError("زمینه سند یافت نشد", 404, "DOCUMENT_CONTEXT_NOT_FOUND")
    return row.id, str(row.id) if context_type == "ROUTE_LEG" else row.public_id


def _audiences(shipment: OperationalShipment, visibility: str, context_type: str, public_ids: list[str]) -> list[CustomerGamification]:
    if visibility not in VISIBILITIES:
        raise DocumentError("سطح دسترسی سند معتبر نیست", 422, "DOCUMENT_VISIBILITY_INVALID")
    if visibility == "CARGO_OWNER" and context_type not in {"CARGO", "DELIVERY"}:
        raise DocumentError("نمایش مالک کالا فقط برای سند کالا مجاز است", 422, "DOCUMENT_VISIBILITY_INVALID")
    if visibility == "EXPLICIT_SHARED" and context_type in {"CARGO", "DELIVERY"}:
        raise DocumentError("سند خصوصی کالا برای اشتراک عمومی این مسیر نیست", 422, "DOCUMENT_VISIBILITY_INVALID")
    if visibility != "EXPLICIT_SHARED":
        if public_ids:
            raise DocumentError("فهرست مخاطب با سطح دسترسی همخوان نیست", 422, "DOCUMENT_AUDIENCE_INVALID")
        return []
    if not public_ids or len(public_ids) != len(set(public_ids)) or len(public_ids) > 50:
        raise DocumentError("مخاطبان انتخاب‌شده معتبر نیستند", 422, "DOCUMENT_AUDIENCE_INVALID")
    rows = db.session.scalars(select(CustomerGamification).where(
        CustomerGamification.public_id.in_(public_ids),
        CustomerGamification.operational_organization_id == shipment.organization_id,
        CustomerGamification.account_status == "ACTIVE",
    )).all()
    if len(rows) != len(public_ids):
        raise DocumentError("مخاطب انتخاب‌شده در دسترس نیست", 404, "DOCUMENT_AUDIENCE_NOT_FOUND")
    return rows


def prepare(shipment: OperationalShipment, context_type: str, target_public_id: str | None,
            visibility: str, audience_public_ids: list[str] | None) -> dict[str, Any]:
    context_type = str(context_type or "").upper()
    visibility = str(visibility or "").upper()
    target_id, resolved_public_id = _target(shipment, context_type, target_public_id)
    if audience_public_ids is None:
        audience_public_ids = []
    if not isinstance(audience_public_ids, list) or any(not isinstance(item, str) for item in audience_public_ids):
        raise DocumentError("فهرست مخاطبان معتبر نیست", 422, "DOCUMENT_AUDIENCE_INVALID")
    return {
        "type": context_type, "target_id": target_id, "target_public_id": resolved_public_id,
        "visibility": visibility, "audiences": _audiences(shipment, visibility, context_type, audience_public_ids),
    }


def _audience_rows(context: OperationalDocumentContext) -> list[OperationalDocumentAudience]:
    return db.session.scalars(select(OperationalDocumentAudience).where(
        OperationalDocumentAudience.context_id == context.id,
    ).order_by(OperationalDocumentAudience.id)).all()


def fact(context: OperationalDocumentContext) -> dict[str, Any]:
    target_id = getattr(context, TARGET_COLUMNS[context.context_type]) if TARGET_COLUMNS[context.context_type] else None
    return {
        "context_type": context.context_type, "target_id": target_id,
        "visibility": context.visibility,
        "audience_account_ids": [row.customer_portal_account_id for row in _audience_rows(context)],
        "version": context.version,
    }


def _event(context: OperationalDocumentContext, action: str, before: dict | None,
           actor_id: int, reason: str | None) -> None:
    db.session.add(OperationalDocumentContextEvent(
        organization_id=context.organization_id, context_id=context.id,
        document_file_id=context.document_file_id, action=action,
        before_fact=before, after_fact=fact(context), actor_user_id=actor_id,
        reason=reason,
    ))


def attach(shipment: OperationalShipment, document: CaseDocumentFile, actor_id: int,
           prepared: dict[str, Any], *, replacement_of: CaseDocumentFile | None = None) -> OperationalDocumentContext:
    """Attach in the caller's upload transaction; no second/orphan commit."""
    context = OperationalDocumentContext(
        organization_id=shipment.organization_id, operational_shipment_id=shipment.id,
        document_file_id=document.id, context_type=prepared["type"],
        visibility=prepared["visibility"], created_by_user_id=actor_id,
    )
    column = TARGET_COLUMNS[prepared["type"]]
    if column:
        setattr(context, column, prepared["target_id"])
    db.session.add(context)
    db.session.flush()
    for account in prepared["audiences"]:
        db.session.add(OperationalDocumentAudience(
            context_id=context.id, organization_id=shipment.organization_id,
            customer_portal_account_id=account.id, created_by_user_id=actor_id,
        ))
    db.session.flush()
    _event(context, "REPLACED" if replacement_of else "ATTACHED", None, actor_id, None)
    if context.delivery_id:
        from backend.services.delivery_service import attach_evidence
        attach_evidence(db.session.get(CargoDelivery, context.delivery_id), document, actor_id)
    return context


def get_for_document(shipment: OperationalShipment, document: CaseDocumentFile) -> OperationalDocumentContext | None:
    return db.session.scalar(select(OperationalDocumentContext).where(
        OperationalDocumentContext.document_file_id == document.id,
        OperationalDocumentContext.operational_shipment_id == shipment.id,
        OperationalDocumentContext.organization_id == shipment.organization_id,
    ))


def project(shipment: OperationalShipment, document: CaseDocumentFile) -> dict[str, Any] | None:
    context = get_for_document(shipment, document)
    if context is None:
        return None  # legacy: no guessed context or Customer visibility
    column = TARGET_COLUMNS[context.context_type]
    target_id = getattr(context, column) if column else shipment.id
    model = {"SHIPMENT": OperationalShipment, "CARGO": ShipmentCargoItem,
             "ROUTE_LEG": RouteLeg, "EXECUTION_UNIT": ExecutionUnit, "DELIVERY": CargoDelivery}[context.context_type]
    target = db.session.get(model, target_id)
    return {
        "public_id": context.public_id, "type": context.context_type,
        "target_public_id": (str(target.id) if context.context_type == "ROUTE_LEG" else target.public_id) if target else None,
        "visibility": context.visibility, "version": context.version,
        "audiences": [db.session.get(CustomerGamification, row.customer_portal_account_id).public_id
                      for row in _audience_rows(context)],
    }


def history(shipment: OperationalShipment, document: CaseDocumentFile) -> list[dict[str, Any]]:
    context = get_for_document(shipment, document)
    if context is None:
        return []
    rows = db.session.scalars(select(OperationalDocumentContextEvent).where(
        OperationalDocumentContextEvent.context_id == context.id,
    ).order_by(OperationalDocumentContextEvent.id)).all()
    return [{
        "action": row.action, "before": row.before_fact, "after": row.after_fact,
        "actor_user_id": row.actor_user_id, "recorded_at": row.recorded_at.isoformat(),
        "reason": row.reason,
    } for row in rows]


def revise(shipment: OperationalShipment, document: CaseDocumentFile, actor_id: int,
           *, context_type: str | None = None, target_public_id: str | None = None,
           visibility: str | None = None, audience_public_ids: list[str] | None = None,
           expected_version: int, reason: str | None = None) -> OperationalDocumentContext:
    # Match upload/replacement and Delivery commands: Shipment -> file -> context.
    # Reauthorize and refresh after waiting; the route's loaded file may be stale.
    shipment = db.session.scalar(select(OperationalShipment).where(
        OperationalShipment.id == shipment.id,
    ).with_for_update().execution_options(populate_existing=True))
    if shipment is None or not authorize_document_management({"id": actor_id}, shipment).allowed:
        raise DocumentError("مدیریت سند مجاز نیست", 403, "DOCUMENT_MUTATION_FORBIDDEN")
    document = db.session.scalar(select(CaseDocumentFile).where(
        CaseDocumentFile.id == document.id, CaseDocumentFile.owner_type == "SHIPMENT",
        CaseDocumentFile.operational_shipment_id == shipment.id,
        CaseDocumentFile.operational_organization_id == shipment.organization_id,
    ).with_for_update().execution_options(populate_existing=True))
    if document is None or document.status != "active":
        raise DocumentError("نسخه جاری سند در دسترس نیست", 404, "DOCUMENT_VERSION_NOT_FOUND")
    context = db.session.scalar(select(OperationalDocumentContext).where(
        OperationalDocumentContext.document_file_id == document.id,
        OperationalDocumentContext.operational_shipment_id == shipment.id,
        OperationalDocumentContext.organization_id == shipment.organization_id,
    ).with_for_update().execution_options(populate_existing=True))
    if context is None or document.status != "active":
        raise DocumentError("نسخه جاری سند در دسترس نیست", 404, "DOCUMENT_VERSION_NOT_FOUND")
    if expected_version != context.version:
        raise DocumentError("نسخه زمینه یا دسترسی تغییر کرده است", 409, "DOCUMENT_CONTEXT_VERSION_CONFLICT")
    previous = project(shipment, document)
    if previous is None:
        raise DocumentError("زمینه سند نامعلوم است", 409, "DOCUMENT_CONTEXT_UNKNOWN")
    changing_context = context_type is not None
    next_type = context_type or context.context_type
    next_target = target_public_id if changing_context else previous["target_public_id"]
    next_visibility = visibility or context.visibility
    next_audiences = audience_public_ids if audience_public_ids is not None else previous["audiences"]
    if next_visibility != "EXPLICIT_SHARED":
        next_audiences = []
    prepared = prepare(shipment, next_type, next_target, next_visibility, next_audiences)
    before = fact(context)
    context_changed = (before["context_type"] != prepared["type"] or
                       before["target_id"] != prepared["target_id"])
    visibility_changed = (before["visibility"] != prepared["visibility"] or
                          sorted(before["audience_account_ids"]) !=
                          sorted(account.id for account in prepared["audiences"]))
    if not context_changed and not visibility_changed:
        raise DocumentError("تغییری برای ثبت وجود ندارد", 422, "DOCUMENT_CONTEXT_UNCHANGED")
    context.context_type = prepared["type"]
    context.cargo_item_id = context.route_leg_id = context.execution_unit_id = context.delivery_id = None
    column = TARGET_COLUMNS[prepared["type"]]
    if column:
        setattr(context, column, prepared["target_id"])
    context.visibility = prepared["visibility"]
    context.version += 1
    for audience in _audience_rows(context):
        db.session.delete(audience)
    db.session.flush()
    for account in prepared["audiences"]:
        db.session.add(OperationalDocumentAudience(
            context_id=context.id, organization_id=shipment.organization_id,
            customer_portal_account_id=account.id, created_by_user_id=actor_id,
        ))
    db.session.flush()
    action = ("CONTEXT_VISIBILITY" if context_changed and visibility_changed else
              "CONTEXT_CHANGED" if context_changed else "VISIBILITY_CHANGED")
    _event(context, action, before, actor_id, reason)
    if context.delivery_id:
        from backend.services.delivery_service import attach_evidence
        attach_evidence(db.session.get(CargoDelivery, context.delivery_id), document, actor_id)
    return context


def customer_context_predicate(account: CustomerGamification):
    """One authorization predicate for lists, pagination and direct downloads."""
    explicit = select(OperationalDocumentAudience.id).where(
        OperationalDocumentAudience.context_id == OperationalDocumentContext.id,
        OperationalDocumentAudience.customer_portal_account_id == account.id,
        OperationalDocumentAudience.organization_id == account.operational_organization_id,
    ).exists()
    own_cargo = select(ShipmentCargoItem.id).join(
        OperationalShipment, OperationalShipment.id == ShipmentCargoItem.operational_shipment_id,
    ).where(
        ShipmentCargoItem.id == OperationalDocumentContext.cargo_item_id,
        ShipmentCargoItem.operational_shipment_id == OperationalDocumentContext.operational_shipment_id,
        OperationalShipment.organization_id == account.operational_organization_id,
        ShipmentCargoItem.cargo_owner_customer_id.in_(authorized_customer_ids(account)),
    ).exists()
    own_delivery = select(CargoDelivery.id).join(
        ShipmentCargoItem, ShipmentCargoItem.id == CargoDelivery.cargo_item_id,
    ).where(
        CargoDelivery.id == OperationalDocumentContext.delivery_id,
        CargoDelivery.operational_shipment_id == OperationalDocumentContext.operational_shipment_id,
        CargoDelivery.organization_id == account.operational_organization_id,
        ShipmentCargoItem.cargo_owner_customer_id.in_(authorized_customer_ids(account)),
    ).exists()
    return and_(
        OperationalDocumentContext.organization_id == account.operational_organization_id,
        or_(and_(OperationalDocumentContext.visibility == "EXPLICIT_SHARED",
                 OperationalDocumentContext.context_type.not_in(["CARGO", "DELIVERY"]), explicit),
            and_(OperationalDocumentContext.visibility == "CARGO_OWNER",
                 or_(and_(OperationalDocumentContext.context_type == "CARGO", own_cargo),
                     and_(OperationalDocumentContext.context_type == "DELIVERY", own_delivery)))),
    )


def authorized_customer_context(account: CustomerGamification, context: OperationalDocumentContext) -> bool:
    if account.account_status != "ACTIVE" or account.operational_organization_id != context.organization_id:
        return False
    return db.session.scalar(select(OperationalDocumentContext.id).where(
        OperationalDocumentContext.id == context.id, customer_context_predicate(account),
    )) is not None
