"""Tenant-owned document policy and deterministic effective-policy resolution."""
from __future__ import annotations

from sqlalchemy import select
from backend.extensions import db
from backend.models import DocumentDefinition, OrganizationDocumentRequirement

LEVELS = frozenset({"REQUIRED", "OPTIONAL", "CONDITIONAL", "DISABLED"})


class PolicyError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def serialize(policy, definition: DocumentDefinition) -> dict:
    return {"document_definition_public_id": definition.public_id, "code": definition.code,
            "title": definition.title, "description": definition.description,
            "global_is_active": definition.is_active, "global_default_required": definition.is_required,
            "applicability_scope": definition.applicability_scope,
            "policy_public_id": policy.public_id if policy else None,
            "requirement_level": policy.requirement_level if policy else None,
            "is_active": policy.is_active if policy else None,
            "version": policy.version if policy else None}


def list_policy(organization_id: int) -> dict:
    definitions = db.session.scalars(select(DocumentDefinition).order_by(DocumentDefinition.sort_order, DocumentDefinition.id)).all()
    policies = db.session.scalars(select(OrganizationDocumentRequirement).where(
        OrganizationDocumentRequirement.operational_organization_id == organization_id)).all()
    by_definition = {row.document_definition_id: row for row in policies}
    return {"mode": "EXPLICIT" if policies else "COMPATIBILITY_FALLBACK",
            "items": [serialize(by_definition.get(definition.id), definition) for definition in definitions]}


def upsert(organization_id: int, definition_public_id: str, payload: dict, actor_id: int):
    if "organization_id" in payload or "operational_organization_id" in payload:
        raise PolicyError("Organization is derived from the authenticated membership.")
    definition = db.session.scalar(select(DocumentDefinition).where(
        DocumentDefinition.public_id == definition_public_id, DocumentDefinition.is_active.is_(True)))
    if not definition:
        raise PolicyError("Active document definition not found.", 404)
    level = str(payload.get("requirement_level", "")).upper()
    if level not in LEVELS:
        raise PolicyError("requirement_level is invalid.")
    active = payload.get("is_active", True)
    if not isinstance(active, bool):
        raise PolicyError("is_active must be boolean.")
    row = db.session.scalar(select(OrganizationDocumentRequirement).where(
        OrganizationDocumentRequirement.operational_organization_id == organization_id,
        OrganizationDocumentRequirement.document_definition_id == definition.id).with_for_update())
    if row:
        expected = payload.get("version")
        if expected is not None and expected != row.version:
            raise PolicyError("version does not match the current policy.", 409)
        row.requirement_level, row.is_active = level, active
        row.version += 1
        row.updated_by = actor_id
    else:
        row = OrganizationDocumentRequirement(operational_organization_id=organization_id,
            document_definition_id=definition.id, requirement_level=level, is_active=active,
            created_by=actor_id, updated_by=actor_id)
        db.session.add(row)
    db.session.commit()
    return serialize(row, definition)


def effective_definitions(organization_id: int | None, shipping_type: str, project_id: int | None = None):
    """Return (definition, level) using project > organization > compatibility fallback."""
    applicable = list(db.session.scalars(select(DocumentDefinition).where(
        DocumentDefinition.is_active.is_(True),
        DocumentDefinition.applicability_scope.in_(["all", shipping_type])).order_by(
            DocumentDefinition.sort_order, DocumentDefinition.id)).all())
    def fallback(definition):
        return "REQUIRED" if definition.is_required else "OPTIONAL"
    if organization_id is None:
        return [(definition, fallback(definition)) for definition in applicable]
    policies = list(db.session.scalars(select(OrganizationDocumentRequirement).where(
        OrganizationDocumentRequirement.operational_organization_id == organization_id)).all())
    if policies:
        by_definition = {row.document_definition_id: row for row in policies}
        result = {definition.id: (definition, by_definition[definition.id].requirement_level)
                  for definition in applicable if definition.id in by_definition
                  and by_definition[definition.id].is_active
                  and by_definition[definition.id].requirement_level != "DISABLED"}
    else:
        result = {definition.id: (definition, fallback(definition)) for definition in applicable}
    if project_id is not None:
        from backend.project_configuration_models import ProjectDocumentRequirement
        from backend.operational_models import Project
        overrides = db.session.scalars(select(ProjectDocumentRequirement).join(
            Project, Project.id == ProjectDocumentRequirement.project_id).where(
            ProjectDocumentRequirement.project_id == project_id,
            Project.organization_id == organization_id,
            ProjectDocumentRequirement.is_active.is_(True))).all()
        applicable_by_id = {definition.id: definition for definition in applicable}
        for override in overrides:
            definition = applicable_by_id.get(override.document_definition_id)
            if definition:
                result[definition.id] = (definition, override.requirement_level)
    return sorted(result.values(), key=lambda pair: (pair[0].sort_order, pair[0].id))
