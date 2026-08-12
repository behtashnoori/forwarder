#!/usr/bin/env python3
"""SELECT-only MT-1B ownership fixpoint analyzer and readiness evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from sqlalchemy import MetaData, create_engine, inspect, select, text

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.resource_identity import composite_identity, scalar_identity  # noqa: E402

SCHEMA_PATH = (
    Path(__file__).parents[1] / "docs/architecture/legacy-tenant-mapping.schema.json"
)
INVENTORY_PATH = (
    Path(__file__).parents[1] / "docs/architecture/tenant-ownership-inventory.yaml"
)
DIRECT = {
    "Project": ("project", "organization_id", True),
    "OperationalShipment": ("operational_shipment", "organization_id", True),
    "ExpertQuote": ("expert_quote", "operational_organization_id", False),
    "ArtifactAssociation": (
        "operational_artifact_association",
        "organization_id",
        True,
    ),
    "EconomicEvidenceAssociation": (
        "economic_evidence_association",
        "organization_id",
        True,
    ),
}
ROOTS = {
    "ShipmentRequest": "shipment_request",
    "Customer": "customer",
    "AssignmentRule": "assignment_rule",
    "ReferralRule": "referral_rule",
    "ReferralAutoAssignState": "referral_auto_assign_state",
    "Report": "report",
    "CustomerGamification": "customer_gamification",
}


@dataclass(frozen=True)
class Edge:
    child: str
    table: str
    column: str
    parent: str
    required: bool = False
    reverse: bool = False


# Every ambiguous descendant in tenant-ownership-inventory.yaml is represented.
EDGES = (
    Edge("Project", "project", "primary_customer_id", "Customer", True, True),
    Edge("ShipmentRequest", "shipment_request", "project_id", "Project", reverse=True),
    Edge(
        "ShipmentRequest", "shipment_request", "customer_id", "Customer", reverse=True
    ),
    Edge(
        "ShipmentRequest",
        "shipment_request",
        "gamification_customer_id",
        "CustomerGamification",
        reverse=True,
    ),
    Edge(
        "ExpertQuote",
        "expert_quote",
        "shipment_request_id",
        "ShipmentRequest",
        True,
        True,
    ),
    Edge(
        "OperationalShipment",
        "operational_shipment",
        "project_id",
        "Project",
        reverse=True,
    ),
    Edge(
        "OperationalShipment",
        "operational_shipment",
        "customer_id",
        "Customer",
        reverse=True,
    ),
    Edge(
        "OperationalShipment",
        "operational_shipment",
        "shipment_request_id",
        "ShipmentRequest",
        reverse=True,
    ),
    Edge(
        "OperationalShipment",
        "operational_shipment",
        "accepted_quote_id",
        "ExpertQuote",
        reverse=True,
    ),
    Edge("CustomerContact", "customer_contact", "customer_id", "Customer", True),
    Edge("Opportunity", "opportunity", "customer_id", "Customer", True),
    Edge("Activity", "activity", "customer_id", "Customer"),
    Edge("Activity", "activity", "opportunity_id", "Opportunity"),
    Edge("Activity", "activity", "shipment_request_id", "ShipmentRequest"),
    Edge("Task", "task", "customer_id", "Customer"),
    Edge("Task", "task", "opportunity_id", "Opportunity"),
    Edge("Task", "task", "shipment_request_id", "ShipmentRequest"),
    Edge(
        "CustomerWorkflowStep",
        "customer_workflow_step",
        "customer_id",
        "CustomerGamification",
        True,
    ),
    Edge(
        "CustomerWorkflowStep",
        "customer_workflow_step",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "ShipmentTracking",
        "shipment_tracking",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "ShipmentTransportUnit",
        "shipment_transport_unit",
        "tracking_id",
        "ShipmentTracking",
        True,
    ),
    Edge(
        "ShipmentTransportUnitUpdate",
        "shipment_transport_unit_update",
        "unit_id",
        "ShipmentTransportUnit",
        True,
    ),
    Edge(
        "ShipmentRequestLog",
        "shipment_request_log",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "ExpertConsoleLog",
        "expert_console_log",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "ExpertConsoleMessage",
        "expert_console_message",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "ExpertConsoleNotification",
        "expert_console_notification",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "CRMCustomerLinkAudit",
        "crm_customer_link_audit",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "CRMCustomerLinkAudit", "crm_customer_link_audit", "old_customer_id", "Customer"
    ),
    Edge(
        "CRMCustomerLinkAudit", "crm_customer_link_audit", "new_customer_id", "Customer"
    ),
    Edge(
        "AssignmentLog",
        "assignment_log",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge("AssignmentLog", "assignment_log", "assignment_rule_id", "AssignmentRule"),
    Edge("ReferralRuleState", "referral_rule_state", "rule_id", "ReferralRule", True),
    Edge(
        "ReferralAssignmentLog",
        "referral_assignment_log",
        "request_id",
        "ShipmentRequest",
        True,
    ),
    Edge("ReferralAssignmentLog", "referral_assignment_log", "rule_id", "ReferralRule"),
    Edge(
        "CaseDocumentRequirement",
        "case_document_requirement",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "CaseDocumentFile",
        "case_document_file",
        "shipment_request_id",
        "ShipmentRequest",
        True,
    ),
    Edge(
        "CaseDocumentFile",
        "case_document_file",
        "case_requirement_id",
        "CaseDocumentRequirement",
    ),
    Edge(
        "ArtifactAssociation",
        "operational_artifact_association",
        "document_file_id",
        "CaseDocumentFile",
        True,
        True,
    ),
    Edge(
        "EconomicEvidenceAssociation",
        "economic_evidence_association",
        "document_file_id",
        "CaseDocumentFile",
        True,
        True,
    ),
    Edge(
        "DocumentAuditEvent",
        "document_audit_event",
        "shipment_request_id",
        "ShipmentRequest",
    ),
    Edge(
        "DocumentAuditEvent",
        "document_audit_event",
        "document_file_id",
        "CaseDocumentFile",
    ),
    Edge(
        "project_party_relationship",
        "project_party_relationship",
        "project_id",
        "Project",
        True,
    ),
    Edge(
        "project_party_relationship",
        "project_party_relationship",
        "customer_id",
        "Customer",
        True,
        True,
    ),
)

ENTITY_TABLE = {
    **ROOTS,
    **{name: value[0] for name, value in DIRECT.items()},
    **{e.child: e.table for e in EDGES},
}
REQUIRED_QUARANTINE_SURFACES = {
    "API list",
    "API detail",
    "search",
    "selector",
    "report",
    "export",
    "job",
    "notification",
    "document download",
    "public tracking",
    "admin tooling",
    "CLI tooling",
    "cache",
    "joins/materialization",
    "monitoring/analytics",
}
REQUIRED_POSTGRESQL_SCENARIOS = set("ABCDEFGHIJKLM")
CONDITIONAL_COLUMNS = {"operational_shipment": {"source_type"}}


def _inventory_ambiguous_entities():
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    return {
        name
        for name, entry in inventory["entities"].items()
        if entry["scope"] == "LEGACY_AMBIGUOUS"
    }


def _canonical_analyzer_identity(metadata, entity, row):
    """Use the runtime serializer; legacy ``entity_id`` remains report-only."""

    table = metadata.tables[ENTITY_TABLE[entity]]
    primary_keys = [column.name for column in table.primary_key.columns]
    if primary_keys == ["id"]:
        value = row["id"]
        kind = "INTEGER" if isinstance(value, int) and not isinstance(value, bool) else "STRING"
        return scalar_identity(entity, value, kind=kind).as_json()
    return composite_identity(
        entity,
        tuple(
            (
                name,
                "INTEGER"
                if isinstance(row[name], int) and not isinstance(row[name], bool)
                else "STRING",
                row[name],
            )
            for name in primary_keys
        ),
    ).as_json()


def _validate_coverage(metadata, names):
    ambiguous = _inventory_ambiguous_entities()
    covered = set(ENTITY_TABLE) & ambiguous
    if covered != ambiguous:
        raise ValueError(
            f"coverage error: inventory mismatch missing={sorted(ambiguous - covered)} "
            f"unexpected={sorted(covered - ambiguous)}"
        )
    required_tables = set(ENTITY_TABLE.values()) | {"operational_organization"}
    missing_tables = sorted(required_tables - names)
    if missing_tables:
        raise ValueError(f"coverage error: missing declared tables {missing_tables}")
    required_columns = defaultdict(set)
    for edge in EDGES:
        required_columns[edge.table].add(edge.column)
    for table_name, owner_column, _required in DIRECT.values():
        required_columns[table_name].add(owner_column)
    for table_name, columns in CONDITIONAL_COLUMNS.items():
        required_columns[table_name].update(columns)
    for table_name, columns in required_columns.items():
        missing = sorted(columns - set(metadata.tables[table_name].c.keys()))
        if missing:
            raise ValueError(
                f"coverage error: {table_name} missing declared columns {missing}"
            )


def load_mappings(path, connection=None):
    if path is None:
        return {}
    document = (
        json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(path, dict)
        else path
    )
    try:
        Draft202012Validator(
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
            format_checker=FormatChecker(),
        ).validate(document)
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "document"
        raise ValueError(
            f"invalid mapping document at {location}: {exc.message}"
        ) from exc
    allowed_types = _inventory_ambiguous_entities() - {"project_party_relationship"}
    required = {
        "entity_type",
        "entity_id",
        "target_organization_id",
        "reason",
        "operator_identity",
        "reviewer_identity",
        "created_at",
        "decision_version",
        "decision_id",
        "review_status",
    }
    allowed = required | {"supersedes_decision_id", "conflict_adjudication"}
    allowed_status = {"ACTIVE", "SUPERSEDED", "REJECTED", "PENDING_REVIEW"}
    if (
        set(document) != {"format_version", "mappings"}
        or document.get("format_version") != 2
        or not isinstance(document.get("mappings"), list)
    ):
        raise ValueError(
            "invalid mapping document: expected format_version=2 and mappings"
        )
    for item in document["mappings"]:
        if (
            not isinstance(item, dict)
            or set(item) - allowed
            or not required.issubset(item)
            or item.get("entity_type") not in allowed_types
        ):
            raise ValueError(
                "invalid mapping document: missing or invalid required property"
            )
        if (
            type(item["entity_id"]) is not int
            or item["entity_id"] < 1
            or type(item["target_organization_id"]) is not int
            or item["target_organization_id"] < 1
        ):
            raise ValueError(
                "invalid mapping document: stable IDs must be positive integers"
            )
        if (
            type(item["decision_version"]) is not int
            or item["decision_version"] < 1
            or item["review_status"] not in allowed_status
        ):
            raise ValueError(
                "invalid mapping document: decision version or review status"
            )
        string_fields = (
            "reason",
            "operator_identity",
            "reviewer_identity",
            "created_at",
            "decision_id",
        )
        if (
            any(not isinstance(item[name], str) for name in string_fields)
            or len(item["reason"]) < 10
            or len(item["decision_id"]) < 8
        ):
            raise ValueError(
                "invalid mapping document: reason, decision ID, or timestamp"
            )
        try:
            parsed_at = datetime.fromisoformat(
                item["created_at"].replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                "invalid mapping document: timestamp must be RFC3339"
            ) from exc
        if parsed_at.tzinfo is None:
            raise ValueError(
                "invalid mapping document: timestamp must include timezone"
            )
        adjudication = item.get("conflict_adjudication")
        if adjudication is not None:
            expected = {
                "candidate_organization_ids",
                "evidence_reference",
                "policy_version",
            }
            if not isinstance(adjudication, dict) or set(adjudication) != expected:
                raise ValueError("invalid conflict adjudication")
            candidates = adjudication["candidate_organization_ids"]
            if (
                not isinstance(candidates, list)
                or len(candidates) < 2
                or any(type(value) is not int or value < 1 for value in candidates)
                or len(set(candidates)) != len(candidates)
                or not all(
                    isinstance(adjudication[name], str) and adjudication[name]
                    for name in ("evidence_reference", "policy_version")
                )
            ):
                raise ValueError("invalid conflict adjudication")
    by_decision, history, active = {}, defaultdict(list), {}
    for item in document["mappings"]:
        if item["operator_identity"] == item["reviewer_identity"]:
            raise ValueError("operator and reviewer must be different")
        if item["decision_id"] in by_decision:
            raise ValueError("duplicate decision_id")
        by_decision[item["decision_id"]] = item
        history[(item["entity_type"], item["entity_id"])].append(item)
    for key, decisions in history.items():
        ids = {d["decision_id"] for d in decisions}
        versions = sorted(d["decision_version"] for d in decisions)
        if len(set(versions)) != len(versions):
            raise ValueError("duplicate or contradictory decision version")
        if versions != list(range(1, max(versions) + 1)):
            raise ValueError("decision versions must be contiguous")
        ordered = sorted(decisions, key=lambda item: item["decision_version"])
        parsed_times = {}
        for decision in ordered:
            parsed_times[decision["decision_id"]] = datetime.fromisoformat(
                decision["created_at"].replace("Z", "+00:00")
            )
            supersedes = decision.get("supersedes_decision_id")
            predecessor = by_decision.get(supersedes) if supersedes else None
            if supersedes and (
                supersedes not in ids
                or predecessor["decision_version"] + 1 != decision["decision_version"]
                or parsed_times.get(supersedes) >= parsed_times[decision["decision_id"]]
            ):
                raise ValueError("invalid supersession history")
            if decision["decision_version"] > 1 and not supersedes:
                raise ValueError("invalid supersession history")
            if decision["decision_version"] == 1 and supersedes:
                raise ValueError("invalid supersession history")
        # Effective state is derived from the immutable chain tip. Older ACTIVE
        # decisions are superseded by linkage; they are never rewritten in place.
        effective = ordered[-1]
        if effective["review_status"] == "ACTIVE":
            active[key] = effective
    if connection is not None:
        _validate_mapping_references(
            connection,
            {
                (d["entity_type"], d["entity_id"], d["decision_id"]): d
                for d in document["mappings"]
            },
        )
    return active


def _validate_mapping_references(connection, mappings):
    names = set(inspect(connection).get_table_names())
    metadata = MetaData()
    metadata.reflect(
        connection,
        only=list(names & (set(ENTITY_TABLE.values()) | {"operational_organization"})),
    )
    orgs = (
        set(
            connection.execute(
                select(metadata.tables["operational_organization"].c.id)
            ).scalars()
        )
        if "operational_organization" in metadata.tables
        else set()
    )
    for key, item in mappings.items():
        entity, entity_id = key[:2]
        table = metadata.tables.get(ENTITY_TABLE.get(entity, ""))
        if (
            table is None
            or connection.execute(
                select(table.c.id).where(table.c.id == entity_id)
            ).first()
            is None
        ):
            raise ValueError(f"mapping references missing row {entity}:{entity_id}")
        if item["target_organization_id"] not in orgs:
            raise ValueError(
                f"mapping {entity}:{entity_id} references missing organization"
            )
        adjudication = item.get("conflict_adjudication")
        if adjudication:
            missing = sorted(set(adjudication["candidate_organization_ids"]) - orgs)
            if missing:
                raise ValueError(
                    f"mapping {entity}:{entity_id} adjudicates missing organizations {missing}"
                )


def analyze(connection, mappings=None, *, require_full_coverage=True):
    mappings = mappings or {}
    if isinstance(mappings, dict) and mappings and "mappings" in mappings:
        mappings = load_mappings(mappings, connection)
    names = set(inspect(connection).get_table_names())
    metadata = MetaData()
    metadata.reflect(
        connection,
        only=list(names & (set(ENTITY_TABLE.values()) | {"operational_organization"})),
    )
    if require_full_coverage:
        _validate_coverage(metadata, names)
    nodes, values = {}, {}
    for entity, table_name in ENTITY_TABLE.items():
        table = metadata.tables.get(table_name)
        if table is None:
            continue
        primary_keys = [column.name for column in table.primary_key.columns]
        if not primary_keys:
            raise ValueError(f"coverage error: {table_name} has no stable primary key")
        lineage_columns = {"id", *primary_keys}
        lineage_columns.update(
            edge.column for edge in EDGES if edge.table == table_name
        )
        lineage_columns.update(
            value[1] for value in DIRECT.values() if value[0] == table_name
        )
        lineage_columns.update(CONDITIONAL_COLUMNS.get(table_name, set()))
        selected = [
            table.c[name] for name in sorted(lineage_columns) if name in table.c
        ]
        for row in connection.execute(select(*selected)).mappings():
            if primary_keys == ["id"]:
                entity_id = row["id"]
            else:
                entity_id = ";".join(f"{name}={row[name]}" for name in primary_keys)
            key = (entity, entity_id)
            nodes[key] = defaultdict(set)
            values[key] = row
    invalid = defaultdict(set)
    organization_table = metadata.tables.get("operational_organization")
    if organization_table is None and any(key[0] in DIRECT for key in nodes):
        raise ValueError("coverage error: operational_organization table missing")
    organization_ids = (
        set(connection.execute(select(organization_table.c.id)).scalars())
        if organization_table is not None
        else set()
    )
    for entity, (table_name, column, required) in DIRECT.items():
        for key in [k for k in nodes if k[0] == entity]:
            org = values[key].get(column)
            if org is None:
                if required:
                    invalid[key].add(
                        f"required_direct_owner_missing:{table_name}.{column}"
                    )
            elif org not in organization_ids:
                invalid[key].add(f"dangling_organization:{table_name}.{column}->{org}")
            else:
                nodes[key][org].add(f"seed:{table_name}.{column}={org}")
    links = []
    for edge in EDGES:
        for child in [k for k in nodes if k[0] == edge.child]:
            parent_id = values[child].get(edge.column)
            if parent_id is None:
                if edge.required:
                    invalid[child].add(
                        f"required_parent_missing:{edge.table}.{edge.column}"
                    )
                continue
            parent = (edge.parent, parent_id)
            if parent not in nodes:
                invalid[child].add(
                    f"dangling_parent:{edge.table}.{edge.column}->{edge.parent}:{parent_id}"
                )
                continue
            links.append(
                (parent, child, f"{edge.table}.{edge.column}->{edge.parent}", True)
            )
            if edge.reverse:
                links.append(
                    (
                        child,
                        parent,
                        f"reverse:{edge.table}.{edge.column}->{edge.parent}",
                        False,
                    )
                )
    for key in [item for item in nodes if item[0] == "OperationalShipment"]:
        row = values[key]
        source_type = row.get("source_type")
        if source_type == "accepted_quote":
            if (
                row.get("shipment_request_id") is None
                or row.get("accepted_quote_id") is None
            ):
                invalid[key].add(
                    "invalid_source_shape:operational_shipment.accepted_quote"
                )
        elif source_type == "direct":
            if (
                row.get("customer_id") is None
                or row.get("shipment_request_id") is not None
                or row.get("accepted_quote_id") is not None
            ):
                invalid[key].add("invalid_source_shape:operational_shipment.direct")
        else:
            invalid[key].add(
                f"invalid_source_shape:operational_shipment.source_type={source_type}"
            )
    for key in [item for item in nodes if item[0] == "CaseDocumentFile"]:
        requirement_id = values[key].get("case_requirement_id")
        if requirement_id is not None:
            requirement = ("CaseDocumentRequirement", requirement_id)
            if requirement in values and values[requirement].get(
                "shipment_request_id"
            ) != values[key].get("shipment_request_id"):
                invalid[key].add(
                    "incompatible_lineage:case_document_file.requirement_request"
                )
    for key in [item for item in nodes if item[0] == "DocumentAuditEvent"]:
        file_id = values[key].get("document_file_id")
        request_id = values[key].get("shipment_request_id")
        document = ("CaseDocumentFile", file_id)
        if (
            file_id is not None
            and request_id is not None
            and document in values
            and values[document].get("shipment_request_id") != request_id
        ):
            invalid[key].add("incompatible_lineage:document_audit_event.file_request")
    changed = True
    iterations = 0
    limit = max(1, len(nodes) + 1)
    while changed and iterations < limit:
        changed = False
        iterations += 1
        for source, target, path, propagate_invalid in links:
            if propagate_invalid and invalid[source]:
                reason = f"invalid_required_parent:{path}"
                if reason not in invalid[target]:
                    invalid[target].add(reason)
                    changed = True
    if changed:
        raise ValueError("invalid-lineage fixpoint did not converge")
    changed = True
    iterations = 0
    while changed and iterations < limit:
        changed = False
        iterations += 1
        for source, target, path, _propagate_invalid in links:
            if invalid[source] or invalid[target]:
                continue
            for org in list(nodes[source]):
                witness = f"via:{source[0]}:{source[1]}->{path}"
                is_new_candidate = org not in nodes[target]
                nodes[target][org].add(witness)
                if is_new_candidate:
                    changed = True
    if changed:
        raise ValueError("ownership fixpoint did not converge; cycle handling failure")
    _validate_mapping_references(connection, mappings)
    results = []
    for key in sorted(nodes, key=lambda value: (value[0], str(value[1]))):
        entity, entity_id = key
        evidence = nodes[key]
        mapping = mappings.get(key)
        lineage_candidates = sorted(evidence)
        mapping_status = "NONE"
        if mapping:
            target = mapping["target_organization_id"]
            adjudication = mapping.get("conflict_adjudication")
            explicit = bool(adjudication)
            if explicit and (
                sorted(adjudication["candidate_organization_ids"]) != lineage_candidates
                or target not in lineage_candidates
            ):
                mapping_status = "REJECTED_STALE_ADJUDICATION"
            elif len(lineage_candidates) > 1 and not explicit:
                mapping_status = "REJECTED_CONFLICT_OVERRIDE"
            elif lineage_candidates and target not in lineage_candidates:
                mapping_status = "REJECTED_EVIDENCE_DISAGREEMENT"
            else:
                mapping_status = "ACTIVE_ADJUDICATED" if explicit else "ACTIVE"
                evidence[target].add(f"mapping:{mapping['decision_id']}")
        candidates = sorted(evidence)
        if invalid[key]:
            classification = "INVALID_LINEAGE"
        elif len(candidates) > 1 and mapping_status != "ACTIVE_ADJUDICATED":
            classification = "CONFLICT"
        elif len(candidates) == 1:
            classification = "DETERMINISTIC"
        elif mapping_status in {"ACTIVE", "ACTIVE_ADJUDICATED"}:
            classification = "DETERMINISTIC"
        else:
            classification = "UNRESOLVED"
        results.append(
            {
                "entity_type": entity,
                "entity_id": entity_id,
                "resource_identity": _canonical_analyzer_identity(
                    metadata, entity, values[key]
                ),
                "classification": classification,
                "candidate_organization_ids": candidates,
                "evidence_paths": [
                    {"organization_id": org, "paths": sorted(evidence[org])}
                    for org in sorted(evidence)
                ],
                "invalid_lineage_reasons": sorted(invalid[key]),
                "mapping_status": mapping_status,
                "quarantine_status": "CLEAR"
                if classification == "DETERMINISTIC"
                else "QUARANTINED",
            }
        )
    return results


def _load_evidence(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    return json.loads(Path(value).read_text(encoding="utf-8"))


def evaluate_readiness(
    rows,
    *,
    quarantine_matrix=None,
    postgresql_evidence=None,
    security_review_evidence=None,
):
    matrix = _load_evidence(quarantine_matrix)
    surfaces = matrix.get("surfaces", []) if isinstance(matrix, dict) else []
    surface_names = {item.get("surface") for item in surfaces if isinstance(item, dict)}
    quarantine_matrix_pass = surface_names == REQUIRED_QUARANTINE_SURFACES and all(
        item.get("pass") is True for item in surfaces
    )
    postgres = _load_evidence(postgresql_evidence)
    scenarios = postgres.get("scenarios", {}) if isinstance(postgres, dict) else {}
    postgresql_certification_pass = (
        postgres.get("database_backend") == "postgresql"
        and postgres.get("loopback_only") is True
        and postgres.get("transaction_read_only") is True
        and postgres.get("mutation_sqlstate") == "25006"
        and set(scenarios) == REQUIRED_POSTGRESQL_SCENARIOS
        and all(value == "PASS" for value in scenarios.values())
    )
    security = _load_evidence(security_review_evidence)
    security_review_pass = (
        security.get("independent") is True
        and security.get("classification") == "MT-1B SECURITY REVIEW — PASS"
    )
    counts = Counter(row["classification"] for row in rows)
    mapping_failures = sum(row["mapping_status"].startswith("REJECTED") for row in rows)
    ready = (
        not (
            counts["CONFLICT"]
            or counts["INVALID_LINEAGE"]
            or counts["UNRESOLVED"]
            or mapping_failures
        )
        and quarantine_matrix_pass
        and postgresql_certification_pass
        and security_review_pass
    )
    return {
        "MT1_OWNERSHIP_RESOLUTION_READY": ready,
        "classification_counts": dict(sorted(counts.items())),
        "mapping_failures": mapping_failures,
        "quarantine_matrix_pass": bool(quarantine_matrix_pass),
        "postgresql_certification_pass": bool(postgresql_certification_pass),
        "security_review_pass": bool(security_review_pass),
    }


def evaluate_dataset_provenance(rows, provenance=None, *, observed_census_hashes=None):
    """Evaluate the dataset-level MT-1 gate without changing row ownership."""
    provenance = _load_evidence(provenance)
    classification = provenance.get("dataset_classification", "UNKNOWN")
    result = {
        "LEGACY_DATA_PROVENANCE_CLASSIFIED": False,
        "LEGACY_DATASET_CLASSIFICATION": classification,
        "REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED": True,
        "SYNTHETIC_LEGACY_DISPOSITION_READY": False,
        "MT1_REAL_DATA_GATE_APPLICABLE": True,
        "LEGACY_SYNTHETIC_ADJUDICATION_STATUS": "NOT_APPLICABLE_TO_UNKNOWN",
        "provenance_gate_pass": False,
    }
    if classification == "SYNTHETIC_ONLY":
        required = {
            "legacy_real_customer_data_present": False,
            "human_ownership_adjudication_required_for_this_dataset": False,
            "auto_tenant_assignment_allowed": False,
            "synthetic_data_may_be_disposed_only_by_explicit_policy": True,
            "real_data_census_required_if_real_legacy_data_is_ever_introduced": True,
        }
        assertions_valid = all(provenance.get(key) is value for key, value in required.items())
        declared_hashes = provenance.get("source_census_hashes")
        hash_binding_valid = (
            isinstance(declared_hashes, dict)
            and declared_hashes == observed_census_hashes
            and set(declared_hashes) == {"csv_sha256", "summary_sha256"}
            and all(
                isinstance(value, str) and len(value) == 64
                for value in declared_hashes.values()
            )
        )
        row_count_valid = provenance.get("total_rows") == len(rows)
        no_candidates = all(not row.get("candidate_organization_ids") for row in rows)
        no_active_mappings = all(
            row.get("mapping_status", "NONE") not in {"ACTIVE", "ACTIVE_ADJUDICATED"}
            for row in rows
        )
        valid = (
            assertions_valid
            and hash_binding_valid
            and row_count_valid
            and no_candidates
            and no_active_mappings
        )
        result.update(
            {
                "LEGACY_DATA_PROVENANCE_CLASSIFIED": valid,
                "REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED": False if valid else True,
                "SYNTHETIC_LEGACY_DISPOSITION_READY": bool(
                    valid and provenance.get("recommended_disposition")
                    == "KEEP_QUARANTINED_SYNTHETIC"
                ),
                "MT1_REAL_DATA_GATE_APPLICABLE": False if valid else True,
                "LEGACY_SYNTHETIC_ADJUDICATION_STATUS": (
                    "NOT_APPLICABLE" if valid else "INVALID_CLASSIFICATION"
                ),
                "provenance_gate_pass": valid,
            }
        )
        return result
    if classification == "REAL_NON_PRODUCTION_CLONE":
        result["LEGACY_DATA_PROVENANCE_CLASSIFIED"] = True
        result["provenance_gate_pass"] = True
        return result
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--mapping")
    parser.add_argument("--output")
    parser.add_argument("--quarantine-matrix")
    parser.add_argument("--postgresql-evidence")
    parser.add_argument("--security-review-evidence")
    parser.add_argument("--dataset-provenance")
    parser.add_argument("--source-census-csv-sha256")
    parser.add_argument("--source-census-summary-sha256")
    args = parser.parse_args()
    engine = create_engine(args.database_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        if connection.dialect.name == "postgresql":
            connection.execute(text("SET TRANSACTION READ ONLY"))
        mappings = load_mappings(args.mapping, connection)
        rows = analyze(connection, mappings)
        transaction.rollback()
    readiness = evaluate_readiness(
        rows,
        quarantine_matrix=args.quarantine_matrix,
        postgresql_evidence=args.postgresql_evidence,
        security_review_evidence=args.security_review_evidence,
    )
    observed_census_hashes = None
    if args.source_census_csv_sha256 and args.source_census_summary_sha256:
        observed_census_hashes = {
            "csv_sha256": args.source_census_csv_sha256,
            "summary_sha256": args.source_census_summary_sha256,
        }
    dataset_gate = evaluate_dataset_provenance(
        rows,
        args.dataset_provenance,
        observed_census_hashes=observed_census_hashes,
    )
    report = {
        "report_version": 2,
        "read_only": True,
        "rows": rows,
        "counts": dict(sorted(Counter(r["classification"] for r in rows).items())),
        "readiness": readiness,
        "dataset_gate": dataset_gate,
    }
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    Path(args.output).write_text(output, encoding="utf-8") if args.output else print(
        output, end=""
    )


if __name__ == "__main__":
    main()
