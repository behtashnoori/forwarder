"""Central MT-1C runtime quarantine enforcement.

The ownership analyzer publishes one decision for every row in an activated
entity census.  A watermark makes that census boundary explicit: rows at or
below it require a deterministic decision, while rows created after it retain
the current runtime behavior until a later census is activated.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, UniqueConstraint, and_, event, exists, func, or_, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Query, Session, with_loader_criteria

from backend.extensions import db
from backend.ownership_census import (
    OwnershipActiveCensus,
    OwnershipCensusScope,
    OwnershipDecision,
)
from backend.resource_identity import ResourceIdentity, scalar_identity


SAFE_CLASSIFICATION = "DETERMINISTIC"
DENIED_CLASSIFICATIONS = frozenset(
    {"QUARANTINED", "INVALID_LINEAGE", "CONFLICT", "UNKNOWN"}
)
CLASSIFICATIONS = frozenset({SAFE_CLASSIFICATION, *DENIED_CLASSIFICATIONS})

# This is intentionally the analyzer's closed entity set.  Contract tests keep
# it synchronized with scripts/mt1a_legacy_ownership_analyzer.py.
CERTIFIED_ENTITIES = frozenset(
    {
        "Activity", "ArtifactAssociation", "AssignmentLog", "AssignmentRule",
        "CRMCustomerLinkAudit", "CaseDocumentFile", "CaseDocumentRequirement",
        "Customer", "CustomerContact", "CustomerGamification",
        "CustomerWorkflowStep", "DocumentAuditEvent",
        "EconomicEvidenceAssociation", "ExpertConsoleLog",
        "ExpertConsoleMessage", "ExpertConsoleNotification", "ExpertQuote",
        "Opportunity", "OperationalShipment", "Project", "ReferralAssignmentLog",
        "ReferralAutoAssignState", "ReferralRule", "ReferralRuleState", "Report",
        "ShipmentRequest", "ShipmentRequestLog", "ShipmentTracking",
        "ShipmentTransportUnit", "ShipmentTransportUnitUpdate", "Task",
    }
)
CANONICAL_RESOURCE_TYPES = frozenset({*CERTIFIED_ENTITIES, "project_party_relationship"})

# A newly materialized child must not point at a denied parent.  The analyzer
# republishes all descendant decisions atomically when an existing root changes.
PARENT_REFERENCES: dict[str, tuple[tuple[str, str], ...]] = {
    "Project": (("primary_customer_id", "Customer"),),
    "ShipmentRequest": (
        ("project_id", "Project"), ("customer_id", "Customer"),
        ("gamification_customer_id", "CustomerGamification"),
    ),
    "ExpertQuote": (("shipment_request_id", "ShipmentRequest"),),
    "OperationalShipment": (
        ("project_id", "Project"), ("customer_id", "Customer"),
        ("shipment_request_id", "ShipmentRequest"),
        ("accepted_quote_id", "ExpertQuote"),
    ),
    "CustomerContact": (("customer_id", "Customer"),),
    "Opportunity": (("customer_id", "Customer"),),
    "Activity": (
        ("customer_id", "Customer"), ("opportunity_id", "Opportunity"),
        ("shipment_request_id", "ShipmentRequest"),
    ),
    "Task": (
        ("customer_id", "Customer"), ("opportunity_id", "Opportunity"),
        ("shipment_request_id", "ShipmentRequest"),
    ),
    "CustomerWorkflowStep": (
        ("customer_id", "CustomerGamification"),
        ("shipment_request_id", "ShipmentRequest"),
    ),
    "ShipmentTracking": (("shipment_request_id", "ShipmentRequest"),),
    "ShipmentTransportUnit": (("tracking_id", "ShipmentTracking"),),
    "ShipmentTransportUnitUpdate": (("unit_id", "ShipmentTransportUnit"),),
    "ShipmentRequestLog": (("shipment_request_id", "ShipmentRequest"),),
    "ExpertConsoleLog": (("shipment_request_id", "ShipmentRequest"),),
    "ExpertConsoleMessage": (("shipment_request_id", "ShipmentRequest"),),
    "ExpertConsoleNotification": (("shipment_request_id", "ShipmentRequest"),),
    "CRMCustomerLinkAudit": (
        ("shipment_request_id", "ShipmentRequest"),
        ("old_customer_id", "Customer"), ("new_customer_id", "Customer"),
    ),
    "AssignmentLog": (
        ("shipment_request_id", "ShipmentRequest"),
        ("assignment_rule_id", "AssignmentRule"),
    ),
    "ReferralRuleState": (("rule_id", "ReferralRule"),),
    "ReferralAssignmentLog": (
        ("request_id", "ShipmentRequest"), ("rule_id", "ReferralRule"),
    ),
    "CaseDocumentRequirement": (("shipment_request_id", "ShipmentRequest"),),
    "CaseDocumentFile": (
        ("shipment_request_id", "ShipmentRequest"),
        ("case_requirement_id", "CaseDocumentRequirement"),
    ),
    "ArtifactAssociation": (("document_file_id", "CaseDocumentFile"),),
    "EconomicEvidenceAssociation": (("document_file_id", "CaseDocumentFile"),),
    "DocumentAuditEvent": (
        ("shipment_request_id", "ShipmentRequest"),
        ("document_file_id", "CaseDocumentFile"),
    ),
    "project_party_relationship": (
        ("project_id", "Project"),
        ("customer_id", "Customer"),
    ),
}


class OwnershipCertificationScope(db.Model):
    """Atomically activated analyzer coverage for one entity type."""

    __tablename__ = "ownership_certification_scope"
    entity_type = db.Column(db.String(80), primary_key=True)
    certified_through_id = db.Column(db.BigInteger, nullable=False)
    census_id = db.Column(db.String(64), nullable=False)
    decision_epoch = db.Column(db.BigInteger, nullable=False, default=1)
    activated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        CheckConstraint("certified_through_id >= 0", name="ck_ownership_scope_watermark"),
        CheckConstraint("decision_epoch >= 1", name="ck_ownership_scope_epoch"),
    )


class OwnershipCertificationDecision(db.Model):
    """Ownership classification, deliberately separate from tenant assignment."""

    __tablename__ = "ownership_certification_decision"
    id = db.Column(db.BigInteger().with_variant(db.Integer, "sqlite"), primary_key=True)
    entity_type = db.Column(db.String(80), nullable=False, index=True)
    entity_id = db.Column(db.BigInteger, nullable=False)
    classification = db.Column(db.String(32), nullable=False)
    census_id = db.Column(db.String(64), nullable=False)
    decision_id = db.Column(db.String(128), nullable=False)
    decided_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_ownership_decision_entity"),
        CheckConstraint("entity_id > 0", name="ck_ownership_decision_entity_id"),
        CheckConstraint(
            "classification IN ('DETERMINISTIC','QUARANTINED','INVALID_LINEAGE','CONFLICT','UNKNOWN')",
            name="ck_ownership_decision_classification",
        ),
    )


class QuarantinedResource(LookupError):
    """Non-disclosing signal used by internal runtime boundaries."""


def visible_expression(entity_type: str, entity_id):
    """SQL predicate implementing explicit-deny and watermark fail-closed rules."""

    decisions = OwnershipCertificationDecision.__table__
    scopes = OwnershipCertificationScope.__table__
    denied = exists().where(
        decisions.c.entity_type == entity_type,
        decisions.c.entity_id == entity_id,
        decisions.c.classification != SAFE_CLASSIFICATION,
    )
    # Activating a census switches the entire entity type to positive
    # certification. The watermark is audit provenance, never a fail-open bound
    # for subsequently-created rows.
    covered = exists().where(scopes.c.entity_type == entity_type)
    cleared = exists().where(
        decisions.c.entity_type == entity_type,
        decisions.c.entity_id == entity_id,
        decisions.c.classification == SAFE_CLASSIFICATION,
    )
    legacy_visible = ~denied & or_(~covered, cleared)

    active = OwnershipActiveCensus.__table__
    modern_scopes = OwnershipCensusScope.__table__
    modern_decisions = OwnershipDecision.__table__
    roots = modern_decisions.alias("effective_ownership_root")
    # Once a canonical scope has ever been published for a resource type, the
    # active pointer and a complete local/root decision pair become mandatory.
    # A missing pointer therefore fails closed instead of falling back to MT-1C.
    modern_required = exists().where(modern_scopes.c.resource_type == entity_type)
    modern_clear = exists().where(
        active.c.singleton_id == 1,
        modern_scopes.c.census_id == active.c.census_id,
        modern_scopes.c.resource_type == entity_type,
        modern_decisions.c.census_id == active.c.census_id,
        modern_decisions.c.resource_type == entity_type,
        modern_decisions.c.scalar_integer_id == entity_id,
        modern_decisions.c.enforcement_state == "CLEAR",
        roots.c.census_id == active.c.census_id,
        roots.c.resource_type == modern_decisions.c.root_resource_type,
        roots.c.resource_key_hash == modern_decisions.c.root_resource_key_hash,
        roots.c.resource_key_payload == modern_decisions.c.root_resource_key_payload,
        roots.c.enforcement_state == "CLEAR",
    )
    return or_(and_(~modern_required, legacy_visible), modern_clear)


def exclude_quarantined(query, model):
    """Apply the authoritative predicate explicitly to an ORM query."""

    entity_type = model.__name__
    if entity_type not in CERTIFIED_ENTITIES:
        raise ValueError(f"{entity_type} is outside the ownership certification contract")
    return query.filter(visible_expression(entity_type, model.id))


def is_quarantined_identity(identity: ResourceIdentity) -> bool:
    """Resolve a canonical decision and its current authoritative lineage root."""

    if identity.resource_type not in CANONICAL_RESOURCE_TYPES:
        return True
    active = db.session.execute(
        select(OwnershipActiveCensus)
        .where(OwnershipActiveCensus.singleton_id == 1)
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one_or_none()
    scoped = db.session.execute(
        select(OwnershipCensusScope.census_id)
        .where(OwnershipCensusScope.resource_type == identity.resource_type)
        .limit(1)
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one_or_none()
    if active is None:
        if scoped is not None:
            return True
        if identity.scalar_integer is None:
            return True
        return _is_quarantined_legacy(identity.resource_type, identity.scalar_integer)
    scope = db.session.get(
        OwnershipCensusScope,
        (active.census_id, identity.resource_type),
        execution_options={"include_quarantined_for_certification": True},
    )
    if scope is None:
        if scoped is None and identity.scalar_integer is not None:
            return _is_quarantined_legacy(
                identity.resource_type, identity.scalar_integer
            )
        return True
    decision = db.session.execute(
        select(OwnershipDecision)
        .where(
            OwnershipDecision.census_id == active.census_id,
            OwnershipDecision.resource_type == identity.resource_type,
            OwnershipDecision.resource_key_hash == identity.key_hash,
        )
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one_or_none()
    if decision is None or decision.resource_key_payload != identity.key_payload:
        return True
    root = db.session.execute(
        select(OwnershipDecision)
        .where(
            OwnershipDecision.census_id == active.census_id,
            OwnershipDecision.resource_type == decision.root_resource_type,
            OwnershipDecision.resource_key_hash == decision.root_resource_key_hash,
        )
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one_or_none()
    return bool(
        decision.enforcement_state != "CLEAR"
        or root is None
        or root.resource_key_payload != decision.root_resource_key_payload
        or root.enforcement_state != "CLEAR"
    )


def _is_quarantined_legacy(entity_type: str, entity_id: int) -> bool:
    statement = select(visible_expression(entity_type, entity_id))
    return not bool(db.session.execute(statement).scalar_one())


def is_quarantined(entity_type: str, entity_id: int | None) -> bool:
    """Return True for denied, invalid, unknown, or missing covered metadata."""

    if entity_type not in CERTIFIED_ENTITIES or entity_id is None:
        return True
    return is_quarantined_identity(scalar_identity(entity_type, entity_id))


def assert_not_quarantined(entity_type: str, entity_id: int | None) -> None:
    if is_quarantined(entity_type, entity_id):
        raise QuarantinedResource("resource not found")


def assert_identity_not_quarantined(identity: ResourceIdentity) -> None:
    if is_quarantined_identity(identity):
        raise QuarantinedResource("resource not found")


def assert_instance_current(instance: Any, *, purpose: str = "read") -> tuple[int, str | int]:
    """Revalidate an already-loaded ORM object against the current census.

    Call this immediately before returning/serializing, mutating, referencing,
    refreshing, or downloading through a held instance.  The stamp is audit
    metadata only: each call performs a current-authority check.
    """

    state = sa_inspect(instance)
    entity_type = type(instance).__name__
    entity_id = state.identity[0] if state.identity and len(state.identity) == 1 else None
    if entity_type not in CERTIFIED_ENTITIES or entity_id is None:
        raise QuarantinedResource("resource not found")
    assert_not_quarantined(entity_type, entity_id)
    token = decision_epoch_token()
    state.info["ownership_census_guard"] = {
        "purpose": purpose,
        "token": token,
    }
    return token


def refresh_guarded(instance: Any, *, attributes: list[str] | None = None) -> Any:
    """Refresh a held instance without allowing a stale-clear resurrection."""

    assert_instance_current(instance, purpose="refresh")
    db.session.refresh(instance, attribute_names=attributes)
    assert_instance_current(instance, purpose="refresh")
    return instance


def decision_epoch_token() -> tuple[int, str | int]:
    """Cheap cache token; census activation must monotonically bump its epoch."""

    active = db.session.execute(
        select(OwnershipActiveCensus.cache_version, OwnershipActiveCensus.cache_token)
        .where(OwnershipActiveCensus.singleton_id == 1)
        .execution_options(include_quarantined_for_certification=True)
    ).one_or_none()
    if active is not None:
        return int(active.cache_version), str(active.cache_token)
    epoch = db.session.execute(
        select(func.coalesce(func.max(OwnershipCertificationScope.decision_epoch), 0))
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one()
    decision_count = db.session.execute(
        select(func.count(OwnershipCertificationDecision.id))
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one()
    return int(epoch), int(decision_count)


def _criterion_for(entity_type: str):
    def criterion(model):
        return visible_expression(entity_type, model.id)

    return criterion


@event.listens_for(Query, "before_compile", retval=True)
def _enforce_legacy_query_before_subquery(query):
    """Guard Flask-SQLAlchemy Query.count() before it wraps the query."""

    for description in query.column_descriptions:
        model = description.get("entity")
        if getattr(model, "__name__", None) in CERTIFIED_ENTITIES:
            query = query.enable_assertions(False).filter(
                visible_expression(model.__name__, model.id)
            )
    return query


@event.listens_for(Query, "before_compile_update", retval=True)
def _enforce_legacy_bulk_update(query, _update_context):
    return _enforce_legacy_query_before_subquery(query)


@event.listens_for(Query, "before_compile_delete", retval=True)
def _enforce_legacy_bulk_delete(query, _delete_context):
    return _enforce_legacy_query_before_subquery(query)


@event.listens_for(Session, "do_orm_execute")
def _enforce_on_every_orm_select(execute_state) -> None:
    if execute_state.execution_options.get("include_quarantined_for_certification", False):
        return
    if execute_state.is_update or execute_state.is_delete:
        mapper = execute_state.bind_arguments.get("mapper")
        model = getattr(mapper, "class_", None)
        statement_table = getattr(execute_state.statement, "table", None)
        if model is None and statement_table is not None:
            model = next(
                (
                    candidate.class_
                    for candidate in db.Model.registry.mappers
                    if candidate.local_table is statement_table
                ),
                None,
            )
        if getattr(model, "__name__", None) in CERTIFIED_ENTITIES:
            execute_state.statement = execute_state.statement.where(
                visible_expression(model.__name__, model.id)
            )
        return
    if not execute_state.is_select:
        return
    statement = execute_state.statement
    # Loader criteria protects entity materialization and relationship loads.
    # Explicit WHERE predicates also cover column-only projections, counts and
    # aggregates, where SQLAlchemy otherwise has no entity row to load.
    statement_entities = {
        description.get("entity")
        for description in getattr(statement, "column_descriptions", ())
        if description.get("entity") is not None
    }
    for model in statement_entities:
        if getattr(model, "__name__", None) in CERTIFIED_ENTITIES:
            statement = statement.where(visible_expression(model.__name__, model.id))
    for mapper in tuple(db.Model.registry.mappers):
        model = mapper.class_
        if model.__name__ in CERTIFIED_ENTITIES:
            statement = statement.options(
                with_loader_criteria(
                    model,
                    _criterion_for(model.__name__),
                    include_aliases=True,
                )
            )
    execute_state.statement = statement


@event.listens_for(Session, "before_flush")
def _prevent_quarantine_laundering(session: Session, _context: Any, _instances: Any) -> None:
    for obj in session.dirty.union(session.deleted):
        if type(obj).__name__ in CERTIFIED_ENTITIES:
            assert_instance_current(obj, purpose="delete" if obj in session.deleted else "mutate")
    for obj in session.new.union(session.dirty):
        for attribute, parent_type in PARENT_REFERENCES.get(
            type(obj).__name__, ()
        ):
            parent_id = getattr(obj, attribute, None)
            if parent_id is not None and is_quarantined(parent_type, parent_id):
                raise QuarantinedResource("referenced resource not found")


__all__ = [
    "CANONICAL_RESOURCE_TYPES", "CERTIFIED_ENTITIES", "CLASSIFICATIONS", "DENIED_CLASSIFICATIONS",
    "OwnershipCertificationDecision", "OwnershipCertificationScope",
    "QuarantinedResource", "assert_identity_not_quarantined", "assert_instance_current",
    "assert_not_quarantined", "decision_epoch_token", "exclude_quarantined",
    "is_quarantined", "is_quarantined_identity", "refresh_guarded", "visible_expression",
]
