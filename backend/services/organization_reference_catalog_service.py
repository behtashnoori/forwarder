"""Tenant-safe activation of platform-governed reference definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from backend.extensions import db
from backend.models import (
    CargoType,
    PackagingType,
    TransportEquipmentType,
    TransportMeansType,
    UnitOfMeasure,
)
from backend.operational_models import OperationalAudit
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationPackagingTypeActivation,
    OrganizationTransportEquipmentTypeActivation,
    OrganizationTransportMeansTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from backend.services.operational_service import OperationalError


@dataclass(frozen=True)
class ResourceSpec:
    definition_model: type
    activation_model: type
    definition_fk: str


RESOURCES = {
    "cargo-types": ResourceSpec(
        CargoType, OrganizationCargoTypeActivation, "cargo_type_id"
    ),
    "units-of-measure": ResourceSpec(
        UnitOfMeasure,
        OrganizationUnitOfMeasureActivation,
        "unit_of_measure_id",
    ),
    "packaging-types": ResourceSpec(
        PackagingType, OrganizationPackagingTypeActivation, "packaging_type_id"
    ),
    "transport-means-types": ResourceSpec(
        TransportMeansType,
        OrganizationTransportMeansTypeActivation,
        "transport_means_type_id",
    ),
    "transport-equipment-types": ResourceSpec(
        TransportEquipmentType,
        OrganizationTransportEquipmentTypeActivation,
        "transport_equipment_type_id",
    ),
}


def _fail(code: str, message: str, status: int = 400):
    raise OperationalError(code, message, status)


def resource_spec(resource: str) -> ResourceSpec:
    spec = RESOURCES.get(resource)
    if spec is None:
        _fail("REFERENCE_RESOURCE_NOT_FOUND", "خانوادهٔ مرجع یافت نشد.", 404)
    return spec


def _uuid(value, message="تعریف مرجع یافت نشد.") -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        _fail("REFERENCE_DEFINITION_NOT_FOUND", message, 404)


def _boolean_arg(value, name):
    if value in (None, "all"):
        return None
    if value not in {"true", "false"}:
        _fail("VALIDATION_FAILED", f"{name} باید true، false یا all باشد.")
    return value == "true"


def _pagination(args):
    try:
        page = int(args.get("page", 1))
        per_page = int(args.get("per_page", 20))
    except (TypeError, ValueError):
        _fail("VALIDATION_FAILED", "مقادیر صفحه‌بندی نامعتبر است.")
    if page < 1 or not 1 <= per_page <= 100:
        _fail("VALIDATION_FAILED", "مقادیر صفحه‌بندی نامعتبر است.")
    return page, per_page


def _iso(value):
    return value.isoformat() if value else None


def projection(definition, activation):
    organization_active = bool(activation and activation.status == "ACTIVE")
    return {
        "public_id": definition.public_id,
        "code": definition.immutable_code,
        "fa_name": definition.fa_name,
        "en_name": definition.en_name,
        "description": definition.description,
        "display_order": definition.display_order,
        "central_active": definition.is_active,
        "organization_active": organization_active,
        "selectable": bool(definition.is_active and organization_active),
        "activation_public_id": activation.public_id if activation else None,
        "activation_version": activation.version if activation else None,
        "origin": "CENTRAL_SYSTEM",
        "created_at": _iso(definition.created_at),
        "updated_at": _iso(definition.updated_at),
        "activation_created_at": _iso(activation.created_at) if activation else None,
        "activation_updated_at": _iso(activation.updated_at) if activation else None,
    }


def list_rows(resource: str, organization_id: int, args):
    spec = resource_spec(resource)
    definition = spec.definition_model
    activation = spec.activation_model
    fk = getattr(activation, spec.definition_fk)
    join_on = (fk == definition.id) & (
        activation.organization_id == organization_id
    )
    query = select(definition, activation).outerjoin(activation, join_on)

    term = str(args.get("q") or "").strip()
    if len(term) > 160:
        _fail("VALIDATION_FAILED", "عبارت جستجو بیش از حد طولانی است.")
    if term:
        pattern = f"%{term}%"
        query = query.where(
            or_(
                definition.immutable_code.ilike(pattern),
                definition.fa_name.ilike(pattern),
                definition.en_name.ilike(pattern),
            )
        )

    central_active = _boolean_arg(args.get("central_active"), "central_active")
    organization_active = _boolean_arg(
        args.get("organization_active"), "organization_active"
    )
    selectable = _boolean_arg(args.get("selectable"), "selectable")
    if central_active is not None:
        query = query.where(definition.is_active.is_(central_active))
    if organization_active is True:
        query = query.where(activation.status == "ACTIVE")
    elif organization_active is False:
        query = query.where(
            or_(activation.id.is_(None), activation.status == "INACTIVE")
        )
    if selectable is True:
        query = query.where(
            definition.is_active.is_(True), activation.status == "ACTIVE"
        )
    elif selectable is False:
        query = query.where(
            or_(
                definition.is_active.is_(False),
                activation.id.is_(None),
                activation.status == "INACTIVE",
            )
        )

    page, per_page = _pagination(args)
    total = db.session.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    ) or 0
    rows = db.session.execute(
        query.order_by(
            definition.display_order,
            definition.immutable_code,
            definition.id,
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return {
        "items": [projection(row, activation_row) for row, activation_row in rows],
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
    }


def _definition(spec: ResourceSpec, public_id: str):
    row = db.session.scalar(
        select(spec.definition_model).where(
            spec.definition_model.public_id == _uuid(public_id)
        )
    )
    if row is None:
        _fail("REFERENCE_DEFINITION_NOT_FOUND", "تعریف مرجع یافت نشد.", 404)
    return row


def _activation(spec: ResourceSpec, definition_id: int, organization_id: int):
    return db.session.scalar(
        select(spec.activation_model).where(
            spec.activation_model.organization_id == organization_id,
            getattr(spec.activation_model, spec.definition_fk) == definition_id,
        )
    )


def _payload(payload):
    if not isinstance(payload, dict):
        _fail("VALIDATION_FAILED", "بدنهٔ درخواست باید یک شیء JSON باشد.")
    if set(payload) - {"version"}:
        _fail("UNKNOWN_FIELDS", "فیلد ناشناخته در درخواست مجاز نیست.")
    return payload


def _expected_version(row, payload):
    version = payload.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        _fail("VERSION_REQUIRED", "نسخهٔ فعلی برای تغییر وضعیت الزامی است.")
    if version != row.version:
        _fail("VERSION_CONFLICT", "نسخهٔ وضعیت سازمان قدیمی است.", 409)


def _audit(
    *, resource, organization_id, actor_id, definition, activation, previous, current
):
    db.session.add(
        OperationalAudit(
            organization_id=organization_id,
            actor_user_id=actor_id,
            action=f"ORGANIZATION_REFERENCE_{current}",
            entity_type=type(activation).__name__,
            entity_id=activation.id,
            metadata_json={
                "resource": resource,
                "activation_public_id": activation.public_id,
                "definition_public_id": definition.public_id,
                "definition_code": definition.immutable_code,
                "previous_state": previous,
                "current_state": current,
                "version": activation.version,
                "origin": "CENTRAL_SYSTEM",
            },
        )
    )


def transition(
    resource: str,
    definition_public_id: str,
    target: str,
    payload,
    organization_id: int,
    actor_id: int,
):
    if target not in {"ACTIVE", "INACTIVE"}:
        _fail("REFERENCE_ACTION_NOT_FOUND", "عملیات مرجع یافت نشد.", 404)
    payload = _payload(payload)
    spec = resource_spec(resource)
    definition = _definition(spec, definition_public_id)
    row = _activation(spec, definition.id, organization_id)

    if target == "ACTIVE" and not definition.is_active:
        _fail(
            "CENTRAL_REFERENCE_INACTIVE",
            "تعریف مرکزی غیرفعال است و برای سازمان قابل فعال‌سازی نیست.",
            409,
        )
    if row is None:
        if target == "INACTIVE":
            _fail(
                "ORGANIZATION_REFERENCE_NOT_ACTIVE",
                "این تعریف برای سازمان فعال نیست.",
                409,
            )
        row = spec.activation_model(
            organization_id=organization_id,
            status="ACTIVE",
            created_by=actor_id,
            updated_by=actor_id,
        )
        setattr(row, spec.definition_fk, definition.id)
        db.session.add(row)
        previous = None
        created = True
    else:
        if row.status == target:
            _fail(
                "REFERENCE_STATE_UNCHANGED",
                "تعریف از قبل در همین وضعیت سازمانی قرار دارد.",
                409,
            )
        _expected_version(row, payload)
        previous = row.status
        row.status = target
        row.version += 1
        row.updated_by = actor_id
        row.updated_at = datetime.now(timezone.utc)
        created = False

    try:
        db.session.flush()
        _audit(
            resource=resource,
            organization_id=organization_id,
            actor_id=actor_id,
            definition=definition,
            activation=row,
            previous=previous,
            current=target,
        )
        db.session.commit()
    except StaleDataError as exc:
        db.session.rollback()
        _fail("VERSION_CONFLICT", "نسخهٔ وضعیت سازمان قدیمی است.", 409)
    except IntegrityError as exc:
        db.session.rollback()
        raise OperationalError(
            "REFERENCE_ACTIVATION_CONFLICT",
            "وضعیت این تعریف هم‌زمان تغییر کرده است.",
            409,
        ) from exc
    return projection(definition, row), created


def is_definition_active_for_organization(
    activation_model, definition_fk: str, definition_id: int, organization_id: int
) -> bool:
    return bool(
        db.session.scalar(
            select(activation_model.id).where(
                activation_model.organization_id == organization_id,
                getattr(activation_model, definition_fk) == definition_id,
                activation_model.status == "ACTIVE",
            )
        )
    )
