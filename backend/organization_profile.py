"""Explicit plan/apply for FORWARDER_STANDARD_ORG_PROFILE_V1."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import ExpertUser, TransportMethod
from backend.operational_models import OperationalAudit, OperationalOrganization
from backend.reference_data_catalog import Catalog, load_catalog
from backend.services.admin_authorization_service import (
    has_organization_admin_capability,
    organization_context_for_authenticated_user,
)
from backend.services.organization_reference_catalog_service import RESOURCES

PROFILE_PATH = Path(__file__).with_name("reference_data") / "forwarder-standard-org-profile-v1.json"
APPROVED_PROFILE_CHECKSUM = "sha256:38795e90a723eb25c1073a6a92278508e9d89c908105074ff767069d4a8bfce8"
PROFILE_RESOURCES = {
    "cargo_types": "cargo-types",
    "units_of_measure": "units-of-measure",
    "packaging_types": "packaging-types",
    "transport_means_types": "transport-means-types",
    "transport_equipment_types": "transport-equipment-types",
}
TOP_LEVEL_KEYS = {
    "schema_version", "profile_version", "profile_name", "catalog_name",
    "catalog_version", "catalog_checksum", "checksum", "activations",
    "required_global_transport_methods", "excluded_organization_configuration",
}


class ProfileValidationError(ValueError):
    pass


class ProfileApplyError(RuntimeError):
    pass


@dataclass(frozen=True)
class OrganizationProfile:
    schema_version: str
    profile_version: str
    profile_name: str
    catalog_name: str
    catalog_version: str
    catalog_checksum: str
    checksum: str
    activations: dict[str, tuple[str, ...]]
    required_global_transport_methods: tuple[str, ...]
    excluded_organization_configuration: tuple[str, ...]

    @property
    def planned_count(self) -> int:
        return sum(len(codes) for codes in self.activations.values())


@dataclass
class OrganizationProfilePlan:
    profile_name: str
    profile_version: str
    checksum: str
    catalog_checksum: str
    organization_public_id: str
    planned_count: int
    created_count: int = 0
    reactivation_count: int = 0
    unchanged_count: int = 0
    conflict_count: int = 0
    rejected_count: int = 0
    verified_global_transport_methods: int = 0
    conflicts: list[dict[str, str]] = field(default_factory=list)
    reactivations: list[dict[str, str]] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "profile_version": self.profile_version,
            "checksum": self.checksum,
            "catalog_checksum": self.catalog_checksum,
            "organization_public_id": self.organization_public_id,
            "planned_count": self.planned_count,
            "created_count": self.created_count,
            "reactivation_count": self.reactivation_count,
            "unchanged_count": self.unchanged_count,
            "conflict_count": self.conflict_count,
            "rejected_count": self.rejected_count,
            "verified_global_transport_methods": self.verified_global_transport_methods,
            "conflicts": self.conflicts,
            "reactivations": self.reactivations,
            "rejected": self.rejected,
        }


def _checksum(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "checksum"}
    encoded = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def load_profile(path: Path = PROFILE_PATH, *, catalog: Catalog | None = None) -> OrganizationProfile:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileValidationError("organization profile is not readable strict UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != TOP_LEVEL_KEYS:
        raise ProfileValidationError("organization profile top-level schema is invalid")
    if payload.get("checksum") != _checksum(payload):
        raise ProfileValidationError("organization profile checksum does not match content")
    if path == PROFILE_PATH and payload["checksum"] != APPROVED_PROFILE_CHECKSUM:
        raise ProfileValidationError("organization profile checksum is not approved")
    if payload.get("schema_version") != "1" or payload.get("profile_version") != "1":
        raise ProfileValidationError("organization profile version is unsupported")
    if payload.get("profile_name") != "FORWARDER_STANDARD_ORG_PROFILE_V1":
        raise ProfileValidationError("organization profile name is not approved")
    selected_catalog = catalog or load_catalog()
    if (
        payload.get("catalog_name") != selected_catalog.catalog_name
        or payload.get("catalog_version") != selected_catalog.catalog_version
        or payload.get("catalog_checksum") != selected_catalog.checksum
    ):
        raise ProfileValidationError("organization profile does not pin the approved catalog")
    activations = payload.get("activations")
    if not isinstance(activations, dict) or set(activations) != set(PROFILE_RESOURCES):
        raise ProfileValidationError("organization profile activation families are invalid")
    catalog_codes = {
        resource: {row["code"] for row in selected_catalog.resources[resource]}
        for resource in PROFILE_RESOURCES
    }
    validated: dict[str, tuple[str, ...]] = {}
    for resource, codes in activations.items():
        if not isinstance(codes, list) or not codes or len(codes) != len(set(codes)):
            raise ProfileValidationError(f"{resource} activation codes are invalid")
        unknown = set(codes) - catalog_codes[resource]
        if unknown:
            raise ProfileValidationError(f"{resource} contains codes outside the pinned catalog")
        validated[resource] = tuple(codes)
    methods = payload.get("required_global_transport_methods")
    exclusions = payload.get("excluded_organization_configuration")
    if not isinstance(methods, list) or not methods or len(methods) != len(set(methods)):
        raise ProfileValidationError("required transport methods are invalid")
    if not isinstance(exclusions, list) or not exclusions:
        raise ProfileValidationError("profile exclusions are required")
    return OrganizationProfile(
        schema_version=payload["schema_version"],
        profile_version=payload["profile_version"],
        profile_name=payload["profile_name"],
        catalog_name=payload["catalog_name"],
        catalog_version=payload["catalog_version"],
        catalog_checksum=payload["catalog_checksum"],
        checksum=payload["checksum"],
        activations=validated,
        required_global_transport_methods=tuple(methods),
        excluded_organization_configuration=tuple(exclusions),
    )


def _authorized_target(organization_public_id: str, actor_username: str):
    organization = OperationalOrganization.query.filter_by(
        public_id=organization_public_id, is_active=True
    ).one_or_none()
    actor = ExpertUser.query.filter_by(username=actor_username, is_active=True).one_or_none()
    if organization is None or actor is None or not has_organization_admin_capability(actor):
        raise ProfileApplyError("active target organization and same-tenant Organization Admin are required")
    context = organization_context_for_authenticated_user(actor.id)
    if context.organization_id != organization.id:
        raise ProfileApplyError("same-tenant actor membership does not match the target organization")
    return organization, actor


def plan_profile(
    profile: OrganizationProfile,
    *,
    organization_public_id: str,
    actor_username: str,
) -> OrganizationProfilePlan:
    organization, _actor = _authorized_target(organization_public_id, actor_username)
    plan = OrganizationProfilePlan(
        profile_name=profile.profile_name,
        profile_version=profile.profile_version,
        checksum=profile.checksum,
        catalog_checksum=profile.catalog_checksum,
        organization_public_id=organization.public_id,
        planned_count=profile.planned_count,
    )
    for profile_resource, codes in profile.activations.items():
        spec = RESOURCES[PROFILE_RESOURCES[profile_resource]]
        definitions = {
            row.immutable_code: row
            for row in spec.definition_model.query.filter(
                spec.definition_model.immutable_code.in_(codes)
            ).all()
        }
        for code in codes:
            definition = definitions.get(code)
            if definition is None:
                plan.conflicts.append({"resource": profile_resource, "code": code, "reason": "catalog definition is missing"})
                continue
            if not definition.is_active:
                plan.conflicts.append({"resource": profile_resource, "code": code, "reason": "catalog definition is inactive"})
                continue
            activation = db.session.scalar(select(spec.activation_model).where(
                spec.activation_model.organization_id == organization.id,
                getattr(spec.activation_model, spec.definition_fk) == definition.id,
            ))
            if activation is None:
                plan.created_count += 1
            elif activation.status == "ACTIVE":
                plan.unchanged_count += 1
            else:
                plan.reactivation_count += 1
                plan.reactivations.append({
                    "resource": profile_resource,
                    "code": code,
                    "reason": "explicit governed reactivation confirmation is required",
                })
    methods = {row.name: row for row in TransportMethod.query.filter(TransportMethod.name.in_(profile.required_global_transport_methods)).all()}
    for code in profile.required_global_transport_methods:
        row = methods.get(code)
        if row is None or not row.is_active:
            plan.conflicts.append({"resource": "request_transport_methods", "code": code, "reason": "required global transport method is missing or inactive"})
        else:
            plan.verified_global_transport_methods += 1
    plan.conflict_count = len(plan.conflicts)
    return plan


def apply_profile(
    profile: OrganizationProfile,
    *,
    organization_public_id: str,
    actor_username: str,
    operator: str,
    approval_reference: str,
    expected_checksum: str,
    confirm_reactivation: bool = False,
) -> OrganizationProfilePlan:
    if expected_checksum != profile.checksum:
        raise ProfileApplyError("expected checksum does not match approved organization profile")
    if not operator.strip() or len(operator.strip()) > 160 or not approval_reference.strip() or len(approval_reference.strip()) > 200:
        raise ProfileApplyError("bounded named operator and approval reference are required")
    organization, actor = _authorized_target(organization_public_id, actor_username)
    plan = plan_profile(
        profile,
        organization_public_id=organization_public_id,
        actor_username=actor_username,
    )
    if plan.conflict_count or plan.rejected_count:
        return plan
    if plan.reactivation_count and not confirm_reactivation:
        raise ProfileApplyError(
            "profile includes intentionally inactive definitions; rerun only after review with explicit reactivation confirmation"
        )
    try:
        for profile_resource, codes in profile.activations.items():
            spec = RESOURCES[PROFILE_RESOURCES[profile_resource]]
            definitions = {
                row.immutable_code: row
                for row in spec.definition_model.query.filter(
                    spec.definition_model.immutable_code.in_(codes)
                ).all()
            }
            for code in codes:
                definition = definitions[code]
                activation = db.session.scalar(select(spec.activation_model).where(
                    spec.activation_model.organization_id == organization.id,
                    getattr(spec.activation_model, spec.definition_fk) == definition.id,
                ))
                if activation is not None and activation.status == "ACTIVE":
                    continue
                previous_state = None
                if activation is None:
                    activation = spec.activation_model(
                        organization_id=organization.id,
                        status="ACTIVE",
                        created_by=actor.id,
                        updated_by=actor.id,
                    )
                    setattr(activation, spec.definition_fk, definition.id)
                    db.session.add(activation)
                    db.session.flush()
                else:
                    previous_state = activation.status
                    activation.status = "ACTIVE"
                    activation.version += 1
                    activation.updated_by = actor.id
                db.session.add(OperationalAudit(
                    organization_id=organization.id,
                    actor_user_id=actor.id,
                    action="ORGANIZATION_REFERENCE_ACTIVE",
                    entity_type=type(activation).__name__,
                    entity_id=activation.id,
                    metadata_json={
                        "profile_name": profile.profile_name,
                        "profile_version": profile.profile_version,
                        "profile_checksum": profile.checksum,
                        "resource": profile_resource,
                        "definition_code": code,
                        "previous_state": previous_state,
                        "current_state": "ACTIVE",
                        "activation_version": activation.version,
                        "operator": operator.strip(),
                        "approval_reference": approval_reference.strip(),
                    },
                ))
        db.session.commit()
        return plan
    except IntegrityError as exc:
        db.session.rollback()
        raise ProfileApplyError("organization profile apply conflicted; all profile writes were rolled back") from exc
