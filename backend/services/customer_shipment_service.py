"""Live, allowlisted Customer reads over the single operational Shipment SOR."""
import hashlib
import hmac
import json
from flask import current_app, session
from sqlalchemy import func, or_, select

from backend.extensions import db
from backend.cargo_models import ShipmentCargoItem as Cargo
from backend.delivery_models import CargoDelivery as Delivery
from backend.document_context_models import OperationalDocumentContext as Context
from backend.customer_entitlement_models import CustomerEntitlement
from backend.logistics_network_models import LogisticsPoint
from backend.models import (CaseDocumentFile, City, Country, CustomerGamification, CustomsOffice, InternationalCity,
                            IranPort, Province)
from backend.operational_models import CanonicalLocation, OperationalShipment as Shipment, RouteCargoDestination, RouteLeg, RoutePlan
from backend.services import delivery_service as deliveries, reported_fact_service as reports
from backend.services.case_document_service import customer_download_name
from backend.services.customer_entitlement_service import authorized_customer_ids
from backend.services.document_context_service import customer_context_predicate
from backend.services.legacy_datetime import serialize_legacy_utc_datetime as iso
from backend.services.operational_service import OperationalError

PAGE_SIZE = 20
MODES = {"road": "جاده‌ای", "rail": "ریلی", "sea": "دریایی", "air": "هوایی",
         "multimodal_transfer": "تغییر روش حمل", "customs_handling": "عملیات گمرکی"}
PUBLIC_GEOGRAPHY = {"province": Province, "city": City, "country": Country,
                    "international_city": InternationalCity, "iran_port": IranPort, "customs_office": CustomsOffice}


def authorization_revision(account):
    """Opaque comparison value, never an authorization grant or persisted model.

    Scalar columns bypass the ORM identity map. Grant UUIDs distinguish revoke /
    regrant even when the resulting set of CRM customers happens to be identical.
    """
    current = db.session.execute(select(CustomerGamification.public_id,
        CustomerGamification.session_generation, CustomerGamification.account_status,
        CustomerGamification.operational_organization_id).where(CustomerGamification.id == account.id)).one_or_none()
    if (not current or current.account_status != "ACTIVE"
            or current.session_generation != session.get("customer_portal_session_generation")
            or current.operational_organization_id != account.operational_organization_id):
        raise OperationalError("SESSION_REVOKED", "نشست پایان یافته است.", 401)
    grants = db.session.scalars(select(CustomerEntitlement.public_id).where(
        CustomerEntitlement.portal_account_id == account.id,
        CustomerEntitlement.organization_id == current.operational_organization_id,
        CustomerEntitlement.revoked_at.is_(None),
        CustomerEntitlement.customer_id.in_(authorized_customer_ids(account)))
        .order_by(CustomerEntitlement.public_id)).all()
    basis = json.dumps([current.public_id, current.session_generation,
        current.operational_organization_id, grants], separators=(",", ":")).encode()
    return hmac.new(current_app.secret_key.encode(), basis, hashlib.sha256).hexdigest()


def authorized_read(account, reader, *args, **kwargs):
    before = authorization_revision(account)
    value = reader(account, *args, **kwargs)
    if not hmac.compare_digest(before, authorization_revision(account)):
        raise OperationalError("CUSTOMER_SCOPE_CHANGED", "دسترسی تغییر کرده است؛ دوباره بخوانید.", 409)
    return {**value, "authorization_revision": before}


def page_number(value):
    try:
        if isinstance(value, bool): raise ValueError
        page = int(value)
        if not 1 <= page <= 100000: raise ValueError
        return page
    except (ValueError, TypeError):
        raise OperationalError("CUSTOMER_SHIPMENT_QUERY_INVALID", "شماره صفحه معتبر نیست.", 422) from None


def _cargo(account, shipment_id=None):
    query = select(Cargo).join(Shipment, Shipment.id == Cargo.operational_shipment_id).where(
        Shipment.organization_id == account.operational_organization_id,
        Cargo.cargo_owner_customer_id.in_(authorized_customer_ids(account)))
    return query.where(Cargo.operational_shipment_id == shipment_id) if shipment_id is not None else query


def _shipments(account):
    own = select(Cargo.id).where(Cargo.operational_shipment_id == Shipment.id,
        Cargo.cargo_owner_customer_id.in_(authorized_customer_ids(account))).exists()
    return select(Shipment).where(Shipment.organization_id == account.operational_organization_id, own)


def _identity(shipment):
    # The shared flag is the sole expressly permitted other-participant fact.
    owners = db.session.scalar(select(func.count(func.distinct(Cargo.cargo_owner_customer_id))).where(
        Cargo.operational_shipment_id == shipment.id)) or 0
    return {"public_id": shipment.public_id, "created_at": iso(shipment.created_at),
            "status": shipment.lifecycle_status, "shared_transport": owners > 1}


def listing(account, page=1, search=""):
    page = page_number(page)
    if not isinstance(search, str) or len(search) > 100:
        raise OperationalError("CUSTOMER_SHIPMENT_QUERY_INVALID", "جست‌وجو معتبر نیست.", 422)
    query = _shipments(account)
    term = search.strip().lower()
    if term:
        matching_own_cargo = select(Cargo.id).where(Cargo.operational_shipment_id == Shipment.id,
            Cargo.cargo_owner_customer_id.in_(authorized_customer_ids(account)),
            func.lower(Cargo.display_name_snapshot).contains(term, autoescape=True)).exists()
        query = query.where(or_(func.lower(Shipment.public_id).contains(term, autoescape=True), matching_own_cargo))
    total = db.session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.session.scalars(query.order_by(Shipment.created_at.desc(), Shipment.public_id).offset(
        (page - 1) * PAGE_SIZE).limit(PAGE_SIZE)).all()
    return {"items": [_identity(row) for row in rows], "pagination": {
        "page": page, "total": total, "has_prev": page > 1, "has_next": page * PAGE_SIZE < total}}


def _geography(location_id, point_id, organization_id):
    if point_id:
        point = db.session.get(LogisticsPoint, point_id)
        if not point or point.organization_id != organization_id: return None
        # Never serialize private facility names, addresses or raw route snapshots.
        for model, identity in ((City, point.city_id), (Province, point.province_id), (Country, point.country_id)):
            row = db.session.get(model, identity) if identity else None
            if row: return row.name_fa
        return None
    canonical = db.session.get(CanonicalLocation, location_id)
    model = PUBLIC_GEOGRAPHY.get(canonical.source_type) if canonical else None
    row = db.session.get(model, canonical.source_id) if model else None
    return row.name_fa if row else None


def _routes(shipment, cargo):
    plan = db.session.scalar(select(RoutePlan).where(RoutePlan.operational_shipment_id == shipment.id,
        RoutePlan.is_active.is_(True), RoutePlan.status == "active"))
    result = []
    for item in cargo:
        mapping = db.session.scalar(select(RouteCargoDestination).where(
            RouteCargoDestination.operational_shipment_id == shipment.id,
            RouteCargoDestination.route_plan_id == plan.id,
            RouteCargoDestination.shipment_cargo_item_id == item.id)) if plan else None
        leg_id, seen, legs = (mapping.destination_route_leg_id if mapping else None), set(), []
        while leg_id and leg_id not in seen:
            seen.add(leg_id)
            leg = db.session.scalar(select(RouteLeg).where(RouteLeg.id == leg_id, RouteLeg.route_plan_id == plan.id))
            if not leg: break
            legs.append({"origin": _geography(leg.origin_location_id, leg.origin_logistics_point_id, shipment.organization_id),
                "destination": _geography(leg.destination_location_id, leg.destination_logistics_point_id, shipment.organization_id),
                "mode": MODES.get(leg.transport_mode)})
            leg_id = leg.parent_route_leg_id
        result.append({"cargo_public_id": item.public_id, "legs": list(reversed(legs))})
    return result


def _page(items, page):
    return {"items": items[:PAGE_SIZE], "page": page, "has_prev": page > 1, "has_next": len(items) > PAGE_SIZE}


def detail(account, shipment_id, *, documents_page=1, deliveries_page=1, timeline_page=1):
    shipment = db.session.scalar(_shipments(account).where(Shipment.public_id == shipment_id))
    if shipment is None:
        raise OperationalError("CUSTOMER_SHIPMENT_NOT_FOUND", "پرونده حمل در دسترس نیست.", 404)
    pages = {name: page_number(value) for name, value in (
        ("documents", documents_page), ("deliveries", deliveries_page), ("timeline", timeline_page))}
    own = _cargo(account, shipment.id)
    cargo = db.session.scalars(own.order_by(Cargo.line_number, Cargo.public_id)).all()
    summaries = {row["public_id"]: row for row in deliveries.summaries(shipment, cargo)}
    safe_cargo = []
    for item in cargo:
        summary = summaries[item.public_id]
        safe_cargo.append({key: summary[key] for key in (
            "public_id", "label", "customer_label", "uom_symbol", "known_actual", "delivered", "remaining", "excess", "has_delivery")})
        safe_cargo[-1].update(type_label=item.cargo_type_fa_snapshot,
            requested=str(item.requested_quantity) if item.requested_quantity is not None else None,
            planned=str(item.planned_quantity) if item.planned_quantity is not None else None)
    document_rows = db.session.execute(select(Context, CaseDocumentFile).join(
        CaseDocumentFile, CaseDocumentFile.id == Context.document_file_id).where(
            Context.operational_shipment_id == shipment.id, customer_context_predicate(account),
            CaseDocumentFile.operational_shipment_id == shipment.id,
            CaseDocumentFile.operational_organization_id == shipment.organization_id, CaseDocumentFile.status == "active")
        .order_by(CaseDocumentFile.uploaded_at.desc(), CaseDocumentFile.id.desc())
        .offset((pages["documents"] - 1) * PAGE_SIZE).limit(PAGE_SIZE + 1)).all()
    documents = [{"public_id": row.public_id, "filename": customer_download_name(row),
                  "version": row.version_number, "context_type": context.context_type} for context, row in document_rows]
    delivery_rows = db.session.scalars(select(Delivery).where(Delivery.organization_id == shipment.organization_id,
        Delivery.operational_shipment_id == shipment.id, Delivery.cargo_item_id.in_(own.with_only_columns(Cargo.id)))
        .order_by(Delivery.occurred_at.desc(), Delivery.recorded_at.desc(), Delivery.id.desc())
        .offset((pages["deliveries"] - 1) * PAGE_SIZE).limit(PAGE_SIZE + 1)).all()
    superseded = set(db.session.scalars(select(Delivery.supersedes_delivery_id).where(
        Delivery.operational_shipment_id == shipment.id, Delivery.organization_id == shipment.organization_id,
        Delivery.supersedes_delivery_id.in_([row.id for row in delivery_rows]))).all())
    timeline = reports.customer_timeline(shipment, account, limit=PAGE_SIZE + 1,
        offset=(pages["timeline"] - 1) * PAGE_SIZE)
    return {**_identity(shipment), "cargo": safe_cargo, "routes": _routes(shipment, cargo),
        "documents": _page(documents, pages["documents"]),
        "deliveries": _page([deliveries.project(row, superseded, account=account) for row in delivery_rows], pages["deliveries"]),
        "timeline": _page(timeline, pages["timeline"]),
        "reported_locations": reports.customer_timeline(shipment, account, limit=100, latest_locations=True)}
