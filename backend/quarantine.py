"""Central MT-1C runtime quarantine enforcement.

The ownership analyzer publishes one decision for every row in an activated
entity census.  A watermark makes that census boundary explicit: rows at or
below it require a deterministic decision, while rows created after it retain
the current runtime behavior until a later census is activated.
"""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from sqlalchemy import CheckConstraint, String, UniqueConstraint, and_, cast, event, exists, or_, select
from sqlalchemy.engine import Engine
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Query, Session, with_loader_criteria
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import TextClause

from backend.extensions import db
from backend.ownership_census import (
    OwnershipCensusScope,
    OwnershipDecision,
    OwnershipDecisionComponent,
)
from backend.census_context import ensure_census_context
from backend.census_context import CensusUnavailable
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
SIDE_EFFECT_ENTITIES = frozenset(
    {
        "AssignmentLog",
        "DocumentAuditEvent",
        "ExpertConsoleLog",
        "ExpertConsoleNotification",
        "OperationalAudit",
        "OperationalOutbox",
        "ReferralAssignmentLog",
    }
)
SIDE_EFFECT_TABLES = frozenset(
    {
        "assignment_log",
        "document_audit_event",
        "expert_console_log",
        "expert_console_notification",
        "operational_audit",
        "operational_outbox",
        "referral_assignment_log",
    }
)

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


def visible_expression(entity_type: str, entity_id, *, session: Session | None = None):
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

    context = ensure_census_context(session)
    if context.legacy:
        return legacy_visible
    modern_scopes = OwnershipCensusScope.__table__
    modern_decisions = OwnershipDecision.__table__
    roots = modern_decisions.alias("effective_ownership_root")
    # Once a canonical scope has ever been published for a resource type, the
    # active pointer and a complete local/root decision pair become mandatory.
    # A missing pointer therefore fails closed instead of falling back to MT-1C.
    modern_required = exists().where(modern_scopes.c.resource_type == entity_type)
    modern_clear = exists().where(
        modern_scopes.c.census_id == context.census_id,
        modern_scopes.c.resource_type == entity_type,
        modern_decisions.c.census_id == context.census_id,
        modern_decisions.c.resource_type == entity_type,
        modern_decisions.c.scalar_integer_id == entity_id,
        modern_decisions.c.enforcement_state == "CLEAR",
        roots.c.census_id == context.census_id,
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
    return query.filter(visible_expression(entity_type, model.id, session=query.session))


def is_quarantined_identity(
    identity: ResourceIdentity, *, session: Session | None = None
) -> bool:
    """Resolve a canonical decision and its current authoritative lineage root."""

    if identity.resource_type not in CANONICAL_RESOURCE_TYPES:
        return True
    session = session or db.session
    try:
        context = ensure_census_context(session)
    except CensusUnavailable:
        return True
    scoped = session.execute(
        select(OwnershipCensusScope.census_id)
        .where(OwnershipCensusScope.resource_type == identity.resource_type)
        .limit(1)
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one_or_none()
    if context.legacy:
        if identity.scalar_integer is None:
            return True
        return _is_quarantined_legacy(
            identity.resource_type, identity.scalar_integer, session=session
        )
    scope = session.get(
        OwnershipCensusScope,
        (context.census_id, identity.resource_type),
        execution_options={"include_quarantined_for_certification": True},
    )
    if scope is None:
        if scoped is None and identity.scalar_integer is not None:
            return _is_quarantined_legacy(
                identity.resource_type, identity.scalar_integer, session=session
            )
        return True
    decision = session.execute(
        select(OwnershipDecision)
        .where(
            OwnershipDecision.census_id == context.census_id,
            OwnershipDecision.resource_type == identity.resource_type,
            OwnershipDecision.resource_key_hash == identity.key_hash,
        )
        .execution_options(include_quarantined_for_certification=True)
    ).scalar_one_or_none()
    if decision is None or decision.resource_key_payload != identity.key_payload:
        return True
    root = session.execute(
        select(OwnershipDecision)
        .where(
            OwnershipDecision.census_id == context.census_id,
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


def _is_quarantined_legacy(
    entity_type: str, entity_id: int, *, session: Session | None = None
) -> bool:
    session = session or db.session
    decisions = OwnershipCertificationDecision.__table__
    scopes = OwnershipCertificationScope.__table__
    denied = exists().where(
        decisions.c.entity_type == entity_type,
        decisions.c.entity_id == entity_id,
        decisions.c.classification != SAFE_CLASSIFICATION,
    )
    covered = exists().where(scopes.c.entity_type == entity_type)
    cleared = exists().where(
        decisions.c.entity_type == entity_type,
        decisions.c.entity_id == entity_id,
        decisions.c.classification == SAFE_CLASSIFICATION,
    )
    return not bool(session.execute(select(~denied & or_(~covered, cleared))).scalar_one())


def is_quarantined(
    entity_type: str, entity_id: int | None, *, session: Session | None = None
) -> bool:
    """Return True for denied, invalid, unknown, or missing covered metadata."""

    if entity_type not in CERTIFIED_ENTITIES or entity_id is None:
        return True
    return is_quarantined_identity(
        scalar_identity(entity_type, entity_id), session=session
    )


def assert_not_quarantined(
    entity_type: str, entity_id: int | None, *, session: Session | None = None
) -> None:
    if is_quarantined(entity_type, entity_id, session=session):
        raise QuarantinedResource("resource not found")


def assert_identity_not_quarantined(
    identity: ResourceIdentity, *, session: Session | None = None
) -> None:
    if is_quarantined_identity(identity, session=session):
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
    session = state.session or db.session
    assert_not_quarantined(entity_type, entity_id, session=session)
    token = decision_epoch_token(session=session)
    state.info["ownership_census_guard"] = {
        "purpose": purpose,
        "token": token,
    }
    return token


def refresh_guarded(instance: Any, *, attributes: list[str] | None = None) -> Any:
    """Refresh a held instance without allowing a stale-clear resurrection."""

    assert_instance_current(instance, purpose="refresh")
    (sa_inspect(instance).session or db.session).refresh(
        instance, attribute_names=attributes
    )
    assert_instance_current(instance, purpose="refresh")
    return instance


def decision_epoch_token(*, session: Session | None = None) -> tuple[int, str | int]:
    """Cheap cache token; census activation must monotonically bump its epoch."""

    return ensure_census_context(session or db.session).token


def project_party_visible_expression(table_or_alias, *, session: Session | None = None):
    """Correlated effective-clear predicate for the canonical association row."""

    context = ensure_census_context(session or db.session)
    if context.legacy:
        return True
    decisions = OwnershipDecision.__table__
    roots = decisions.alias("project_party_effective_root")
    components = OwnershipDecisionComponent.__table__
    project_component = components.alias("project_party_project_component")
    customer_component = components.alias("project_party_customer_component")
    role_component = components.alias("project_party_role_component")
    scopes = OwnershipCensusScope.__table__
    ever_scoped = exists().where(
        scopes.c.resource_type == "project_party_relationship"
    )
    clear = exists(
        select(decisions.c.id)
        .select_from(
            decisions.join(
                project_component,
                and_(
                    project_component.c.decision_id == decisions.c.id,
                    project_component.c.ordinal == 0,
                ),
            )
            .join(
                customer_component,
                and_(
                    customer_component.c.decision_id == decisions.c.id,
                    customer_component.c.ordinal == 1,
                ),
            )
            .join(
                role_component,
                and_(
                    role_component.c.decision_id == decisions.c.id,
                    role_component.c.ordinal == 2,
                ),
            )
            .join(
                roots,
                and_(
                    roots.c.census_id == decisions.c.census_id,
                    roots.c.resource_type == decisions.c.root_resource_type,
                    roots.c.resource_key_hash == decisions.c.root_resource_key_hash,
                    roots.c.resource_key_payload == decisions.c.root_resource_key_payload,
                ),
            )
        )
        .where(
            decisions.c.census_id == context.census_id,
            decisions.c.resource_type == "project_party_relationship",
            decisions.c.enforcement_state == "CLEAR",
            roots.c.enforcement_state == "CLEAR",
            project_component.c.component_name == "project_id",
            project_component.c.component_kind == "INTEGER",
            project_component.c.canonical_value
            == cast(table_or_alias.c.project_id, String),
            customer_component.c.component_name == "customer_id",
            customer_component.c.component_kind == "INTEGER",
            customer_component.c.canonical_value
            == cast(table_or_alias.c.customer_id, String),
            role_component.c.component_name == "party_role",
            role_component.c.component_kind == "STRING",
            role_component.c.canonical_value == table_or_alias.c.party_role,
        )
    )
    return or_(~ever_scoped, clear)


def _project_party_occurrences(statement) -> tuple[Any, ...]:
    from sqlalchemy.sql.selectable import Join  # noqa: PLC0415
    from backend.operational_models import project_party_relationship  # noqa: PLC0415

    found = []

    def visit(node):
        if isinstance(node, Join):
            visit(node.left)
            visit(node.right)
            return
        if node is project_party_relationship or getattr(node, "original", None) is project_party_relationship:
            found.append(node)

    for from_clause in getattr(statement, "get_final_froms", lambda: ())():
        visit(from_clause)
    return tuple(found)


def _mentioned_protected_tables(statement) -> frozenset[str]:
    protected = SIDE_EFFECT_TABLES.union({"project_party_relationship"})
    if isinstance(statement, TextClause):
        sql = statement.text.lower()
        return frozenset(
            name for name in protected
            if re.search(rf"(?<![a-z0-9_]){re.escape(name)}(?![a-z0-9_])", sql)
        )
    found = set()
    for node in visitors.iterate(statement):
        name = getattr(node, "name", None)
        original_name = getattr(getattr(node, "original", None), "name", None)
        for candidate in (name, original_name):
            if candidate in protected:
                found.add(candidate)
    return frozenset(found)


@event.listens_for(Engine, "before_execute", retval=True)
def _reject_unfenced_connection_core(
    _connection, clauseelement, multiparams, params, execution_options
):
    """Reject raw/direct-Connection access that cannot carry the Session fence."""

    if execution_options.get("include_quarantined_for_certification", False):
        return clauseelement, multiparams, params
    mentioned = _mentioned_protected_tables(clauseelement)
    protected_project_access = "project_party_relationship" in mentioned
    text_write = isinstance(clauseelement, TextClause) and bool(
        re.match(r"\s*(?:insert|update|delete)\b", clauseelement.text, re.IGNORECASE)
    )
    protected_side_effect_write = bool(mentioned.intersection(SIDE_EFFECT_TABLES)) and (
        text_write
        or any(
            bool(getattr(clauseelement, attribute, False))
            for attribute in ("is_insert", "is_update", "is_delete")
        )
    )
    orm_flush = bool(_connection.info.get("ownership_census_orm_flush", False))
    if (
        (protected_project_access or (protected_side_effect_write and not orm_flush))
        and not execution_options.get("ownership_census_core_guarded", False)
    ):
        raise QuarantinedResource("protected Core resource requires census repository")
    return clauseelement, multiparams, params


@event.listens_for(Engine, "commit")
@event.listens_for(Engine, "rollback")
def _clear_connection_flush_capability(connection) -> None:
    connection.info.pop("ownership_census_orm_flush", None)


def assert_session_materializable(session: Session | None = None):
    """Final response/export/download boundary for all held certified instances."""

    session = session or db.session
    context = ensure_census_context(session)
    if context.legacy and context.token == (0, 0):
        return context
    for instance in tuple(session.identity_map.values()):
        if type(instance).__name__ in CERTIFIED_ENTITIES:
            assert_instance_current(instance, purpose="materialize")
    return context


@event.listens_for(Query, "before_compile", retval=True)
def _enforce_legacy_query_before_subquery(query):
    """Guard Flask-SQLAlchemy Query.count() before it wraps the query."""

    for description in query.column_descriptions:
        model = description.get("entity")
        if getattr(model, "__name__", None) in CERTIFIED_ENTITIES:
            query = query.enable_assertions(False).filter(
                visible_expression(model.__name__, model.id, session=query.session)
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
    statement_table = getattr(execute_state.statement, "table", None)
    statement_table_name = getattr(statement_table, "name", None)
    if execute_state.is_insert:
        if statement_table_name in SIDE_EFFECT_TABLES:
            # Core DML has no mapped instance on which the parent-reference
            # contract can run.  Side effects must use the mapped/service path
            # so before_flush validates every certified input under pinned N.
            raise QuarantinedResource("protected side effect requires census repository")
        if statement_table_name == "project_party_relationship":
            context = ensure_census_context(execute_state.session)
            # A canonical census is a complete immutable set. A newly inserted
            # association has no decision in pinned N and therefore fails closed.
            if not context.legacy or context.token != (0, 0):
                raise QuarantinedResource("referenced resource not found")
        if statement_table_name == "project_party_relationship":
            execute_state.statement = execute_state.statement.execution_options(
                ownership_census_core_guarded=True
            )
        return
    if execute_state.is_update or execute_state.is_delete:
        if statement_table_name in SIDE_EFFECT_TABLES:
            # As with Core INSERT, set-based side-effect mutation cannot prove
            # the eligibility of each referenced certified resource.
            raise QuarantinedResource("protected side effect requires census repository")
        mapper = execute_state.bind_arguments.get("mapper")
        model = getattr(mapper, "class_", None)
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
            ensure_census_context(execute_state.session)
            execute_state.statement = execute_state.statement.where(
                visible_expression(
                    model.__name__, model.id, session=execute_state.session
                )
            )
        occurrences = _project_party_occurrences(execute_state.statement)
        if not occurrences and getattr(statement_table, "name", None) == "project_party_relationship":
            occurrences = (statement_table,)
        if occurrences:
            ensure_census_context(execute_state.session)
        for occurrence in occurrences:
            execute_state.statement = execute_state.statement.where(
                project_party_visible_expression(
                    occurrence, session=execute_state.session
                )
            )
        if getattr(model, "__name__", None) in CERTIFIED_ENTITIES or occurrences:
            execute_state.session.info["ownership_census_sensitive_write"] = True
        if occurrences:
            execute_state.statement = execute_state.statement.execution_options(
                ownership_census_core_guarded=True
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
            statement = statement.where(
                visible_expression(
                    model.__name__, model.id, session=execute_state.session
                )
            )
    occurrences = _project_party_occurrences(statement)
    mentions = _mentioned_protected_tables(statement)
    if "project_party_relationship" in mentions and not occurrences:
        raise QuarantinedResource("unsupported protected Core statement shape")
    for occurrence in occurrences:
        statement = statement.where(
            project_party_visible_expression(
                occurrence, session=execute_state.session
            )
        )
    if occurrences:
        statement = statement.execution_options(ownership_census_core_guarded=True)
    for model in statement_entities:
        if getattr(model, "__name__", None) in CERTIFIED_ENTITIES:
            statement = statement.options(
                with_loader_criteria(
                    model,
                    visible_expression(
                        model.__name__, model.id, session=execute_state.session
                    ),
                    include_aliases=True,
                )
            )
    execute_state.statement = statement


@event.listens_for(Session, "before_flush")
def _prevent_quarantine_laundering(session: Session, _context: Any, _instances: Any) -> None:
    if any(
        type(obj).__name__ in CERTIFIED_ENTITIES.union(SIDE_EFFECT_ENTITIES)
        for obj in session.new.union(session.dirty).union(session.deleted)
    ):
        ensure_census_context(session)
        session.connection().info["ownership_census_orm_flush"] = True
    for obj in session.dirty.union(session.deleted):
        if type(obj).__name__ in CERTIFIED_ENTITIES:
            assert_instance_current(obj, purpose="delete" if obj in session.deleted else "mutate")
    for obj in session.new.union(session.dirty):
        for attribute, parent_type in PARENT_REFERENCES.get(
            type(obj).__name__, ()
        ):
            parent_id = getattr(obj, attribute, None)
            if parent_id is not None and is_quarantined(
                parent_type, parent_id, session=session
            ):
                raise QuarantinedResource("referenced resource not found")


@event.listens_for(Session, "after_flush_postexec")
def _clear_orm_flush_capability(session: Session, _context: Any) -> None:
    if session.in_transaction():
        session.connection().info.pop("ownership_census_orm_flush", None)


@event.listens_for(Session, "before_commit")
def _validate_side_effect_fence_before_commit(session: Session) -> None:
    changed = session.new.union(session.dirty).union(session.deleted)
    if session.info.get("ownership_census_sensitive_write") or any(
        type(obj).__name__ in CERTIFIED_ENTITIES.union(SIDE_EFFECT_ENTITIES)
        for obj in changed
    ):
        ensure_census_context(session)


__all__ = [
    "CANONICAL_RESOURCE_TYPES", "CERTIFIED_ENTITIES", "CLASSIFICATIONS", "DENIED_CLASSIFICATIONS",
    "OwnershipCertificationDecision", "OwnershipCertificationScope",
    "QuarantinedResource", "assert_identity_not_quarantined", "assert_instance_current",
    "assert_session_materializable",
    "assert_not_quarantined", "decision_epoch_token", "exclude_quarantined",
    "is_quarantined", "is_quarantined_identity", "project_party_visible_expression",
    "refresh_guarded", "visible_expression",
]
