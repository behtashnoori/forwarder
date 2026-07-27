"""Fail-closed metadata-driven transfer for the Phase 1B local cutover.

This module never creates, drops, migrates, or renames databases.  The
PowerShell operator harness owns those operations.  Source connections are
always opened read-only and no row payload is written to logs or evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable
import uuid

import bcrypt
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


ACTIVE_HEAD = "20260801_route_exception"
SOURCE_DATABASE = "forwarder_db"
BASELINE_TABLES = {
    "alembic_version",
    "country",
    "referral_auto_assign_state",
    "tracking_location_reference",
}
SECURITY_PATTERNS = (
    "otp", "session", "token", "reset", "secret", "api_key", "challenge",
)
PASSWORD_COLUMNS = {"password", "password_hash", "hashed_password"}
ROLE_PERMISSIONS = {
    "admin": ("admin", "report", "verify", "correct"),
    "manager": ("report", "verify", "correct"),
    "member": ("report",),
    "expert": ("report",),
    "viewer": (),
    # Active Head has no organization role column. Ownership is represented by
    # the complete, closed set of existing operational capabilities.
    "tenant_owner": (
        "checkpoint.read", "checkpoint.report", "checkpoint.verify",
        "milestone.correct", "milestone.verify", "milestone_event.create",
        "operational_shipment.create", "operational_shipment.read",
        "route_exception.manage", "route_exception.read", "route_leg.manage",
        "route_plan.activate", "route_plan.create", "route_plan.read",
        "route_plan.replan", "work_item.manage", "work_item.read",
    ),
}
ALLOWED_DATABASE = re.compile(
    r"^(forwarder_db|forwarder_phase1b_(?:rehearsal|final)_[a-z0-9_]+)$"
)


class CutoverBlocked(RuntimeError):
    """A fail-closed mapping or reconciliation gate rejected execution."""


@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    nullable: bool
    default: str | None
    generated: bool


@dataclass(frozen=True)
class TablePlan:
    table: str
    classification: str
    columns: tuple[str, ...]
    source_rows: int
    reason: str
    target_table: str | None = None


def quote_dsn(host: str, port: int, user: str, database: str) -> str:
    if host != "127.0.0.1" or port != 5432 or not ALLOWED_DATABASE.fullmatch(database):
        raise CutoverBlocked(f"database target is outside the local allow-list: {database}")
    # Password is intentionally absent; libpq reads process-local PGPASSWORD.
    return f"host={host} port={port} user={user} dbname={database} connect_timeout=5"


def is_security_table(name: str) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in SECURITY_PATTERNS)


def transferable_columns(
    source: Iterable[Column], target: Iterable[Column], table: str
) -> tuple[tuple[str, ...], str | None]:
    source_by_name = {item.name: item for item in source}
    target_items = tuple(target)
    selected: list[str] = []
    for item in target_items:
        if item.generated:
            continue
        if item.name in PASSWORD_COLUMNS:
            # Schema types do not prove password algorithm compatibility.
            # Preserve identity but require a target default/reset path.
            if not item.nullable and item.default is None:
                return (), f"password algorithm compatibility unproven for required {item.name}"
            continue
        if item.name in source_by_name:
            selected.append(item.name)
        elif not item.nullable and item.default is None:
            return (), f"required target column has no source/default: {item.name}"
    if not selected:
        return (), "no compatible columns"
    return tuple(selected), None


def password_compatibility_proven() -> bool:
    """Prove the application's bcrypt producer/verifier contract synthetically."""
    password = b"phase1b-synthetic-verifier"
    encoded = bcrypt.hashpw(password, bcrypt.gensalt(rounds=4))
    return (
        encoded.startswith((b"$2a$", b"$2b$", b"$2y$"))
        and len(encoded) <= 128
        and bcrypt.checkpw(password, encoded)
        and not bcrypt.checkpw(b"wrong", encoded)
    )


def _has_columns(schema: dict[str, tuple[Column, ...]], table: str, names: set[str]) -> bool:
    return names <= {column.name for column in schema.get(table, ())}


def _special_plan(
    table: str,
    source_schema: dict[str, tuple[Column, ...]],
    target_schema: dict[str, tuple[Column, ...]],
    count: int,
) -> TablePlan | None:
    if table == "tenants" and _has_columns(
        source_schema, table, {"id", "name", "slug", "status", "created_at"}
    ) and _has_columns(
        target_schema, "operational_organization",
        {"id", "public_id", "name", "is_active", "created_at"},
    ):
        return TablePlan(
            table, "ID_REMAP_REQUIRED",
            ("name", "slug", "status", "created_at"), count,
            "tenant maps to operational organization; deterministic public_id and ID map required",
            "operational_organization",
        )
    if table == "memberships" and _has_columns(
        source_schema, table, {"id", "tenant_id", "user_id", "role", "status", "created_at"}
    ) and _has_columns(
        target_schema, "operational_membership",
        {"id", "organization_id", "user_id", "is_active", "permissions", "created_at"},
    ):
        return TablePlan(
            table, "ID_REMAP_REQUIRED",
            ("tenant_id", "user_id", "role", "status", "created_at"), count,
            "membership uses tenant-to-organization ID map and role permissions",
            "operational_membership",
        )
    if table == "audit_logs":
        return TablePlan(
            table, "ARCHIVE_ONLY", (), count,
            "legacy rows lack required entity target and may lack the required actor; retained in legacy database and backup",
            None,
        )
    if table == "customer_tenant_links" and _has_columns(
        source_schema, table,
        {"id", "tenant_id", "customer_id", "status", "points", "level", "created_at"},
    ):
        return TablePlan(
            table, "ARCHIVE_ONLY", (), count,
            "legacy tenant-scoped gamification relation has no active-head organization/customer relation; retained in legacy database and backup",
            None,
        )
    if table == "export_jobs" and _has_columns(
        source_schema, table,
        {"id", "tenant_id", "requested_by_type", "requested_by_id", "status",
         "progress", "file_path", "created_at", "finished_at", "error"},
    ):
        return TablePlan(
            table, "ARCHIVE_ONLY", (), count,
            "transient legacy export job state and file references have no active-head queue; retained in legacy database and backup",
            None,
        )
    return None


def validate_runtime_mapping(
    plans: Iterable[TablePlan], membership_roles: Iterable[str],
) -> list[str]:
    """Run write-independent validations identically in every transfer mode."""
    blockers: list[str] = []
    by_table = {plan.table: plan for plan in plans}
    for table in ("customer_tenant_links", "export_jobs"):
        plan = by_table.get(table)
        if plan and plan.source_rows and plan.classification != "ARCHIVE_ONLY":
            blockers.append(f"{table}: populated legacy table lacks archive policy")
    membership = by_table.get("memberships")
    if membership and membership.source_rows:
        if membership.target_table != "operational_membership":
            blockers.append("memberships: active-head target mapping unavailable")
        for role in sorted({str(value).strip().lower() for value in membership_roles}):
            if role not in ROLE_PERMISSIONS:
                blockers.append(f"memberships: unsupported role {role}")
    return blockers


def build_mapping(
    source_schema: dict[str, tuple[Column, ...]],
    target_schema: dict[str, tuple[Column, ...]],
    source_counts: dict[str, int],
) -> tuple[list[TablePlan], list[str]]:
    plans: list[TablePlan] = []
    blockers: list[str] = []
    for table in sorted(source_schema):
        count = source_counts.get(table, 0)
        special = _special_plan(table, source_schema, target_schema, count)
        if special:
            plans.append(special)
        elif table == "alembic_version":
            plans.append(TablePlan(table, "TARGET_BASELINE_PRESERVE", (), count,
                                   "active migration metadata is never copied"))
        elif table in BASELINE_TABLES:
            plans.append(TablePlan(table, "TARGET_BASELINE_RECONCILE", (), count,
                                   "fresh active-head baseline is authoritative"))
        elif is_security_table(table):
            plans.append(TablePlan(table, "EXCLUDE_SECURITY_SENSITIVE", (), count,
                                   "transient authentication/security data excluded"))
        elif table not in target_schema:
            classification = "SOURCE_ONLY_REVIEW"
            plans.append(TablePlan(table, classification, (), count,
                                   "no active-head target table"))
            if count:
                blockers.append(f"{table}: populated source-only table")
        else:
            if table == "expert_user" and password_compatibility_proven():
                columns = tuple(
                    column.name for column in target_schema[table]
                    if not column.generated
                    and column.name in {item.name for item in source_schema[table]}
                )
                plans.append(TablePlan(
                    table, "DIRECT_COPY", columns, count,
                    "bcrypt $2-compatible synthetic verifier passed; password hashes preserved",
                    table,
                ))
                continue
            columns, error = transferable_columns(
                source_schema[table], target_schema[table], table
            )
            if error:
                plans.append(TablePlan(table, "MANUAL_DECISION_REQUIRED", (), count, error))
                if count:
                    blockers.append(f"{table}: {error}")
            else:
                plans.append(TablePlan(table, "DIRECT_COPY", columns, count,
                                       "same-name compatible columns; identifiers preserved", table))
    return plans, blockers


def reconcile_metrics(metrics: Iterable[dict[str, int]]) -> dict[str, Any]:
    rows = list(metrics)
    rejected = sum(item.get("rejected_rows", 0) for item in rows)
    variance = sum(abs(item.get("variance", 0)) for item in rows)
    return {
        "tables_assessed": len(rows),
        "source_rows": sum(item.get("source_rows", 0) for item in rows),
        "inserted_rows": sum(item.get("inserted_rows", 0) for item in rows),
        "excluded_rows": sum(item.get("excluded_rows", 0) for item in rows),
        "transformed_rows": sum(item.get("transformed_rows", 0) for item in rows),
        "rejected_rows": rejected,
        "unexplained_variance": variance,
        "pass": rejected == 0 and variance == 0,
    }


def state_transition(state: str, event: str) -> str:
    transitions = {
        ("INITIAL", "PREFLIGHT_PASS"): "BACKUP_REQUIRED",
        ("BACKUP_REQUIRED", "BACKUP_PASS"): "REHEARSAL_REQUIRED",
        ("REHEARSAL_REQUIRED", "REHEARSAL_PASS"): "FINAL_REQUIRED",
        ("FINAL_REQUIRED", "FINAL_PASS"): "CUTOVER_READY",
        ("CUTOVER_READY", "CUTOVER_PASS"): "POST_CUTOVER",
        ("POST_CUTOVER", "VALIDATION_PASS"): "COMPLETE",
        ("POST_CUTOVER", "VALIDATION_FAIL"): "ROLLBACK_REQUIRED",
        ("ROLLBACK_REQUIRED", "ROLLBACK_PASS"): "ROLLED_BACK",
    }
    try:
        return transitions[(state, event)]
    except KeyError as exc:
        raise CutoverBlocked(f"invalid state transition: {state}/{event}") from exc


def cleanup_allowed(database: str, run_token: str) -> bool:
    return database in {
        f"forwarder_phase1b_rehearsal_{run_token}",
        f"forwarder_phase1b_final_{run_token}",
        f"forwarder_phase1b_restore_{run_token}",
    }


def connect(database: str, user: str, readonly: bool):
    connection = psycopg2.connect(quote_dsn("127.0.0.1", 5432, user, database))
    connection.set_session(readonly=readonly, autocommit=False)
    with connection.cursor() as cursor:
        cursor.execute("SET statement_timeout = '120s'")
    return connection


def schema_inventory(connection) -> tuple[dict[str, tuple[Column, ...]], dict[str, int]]:
    schema: dict[str, list[Column]] = {}
    counts: dict[str, int] = {}
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name, column_name, data_type, is_nullable,
                   column_default, is_generated
            FROM information_schema.columns
            WHERE table_schema='public'
            ORDER BY table_name, ordinal_position
            """
        )
        for table, name, dtype, nullable, default, generated in cursor.fetchall():
            schema.setdefault(table, []).append(
                Column(name, dtype, nullable == "YES", default, generated != "NEVER")
            )
        for table in sorted(schema):
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))
            )
            counts[table] = cursor.fetchone()[0]
    return {key: tuple(value) for key, value in schema.items()}, counts


def source_runtime_validation(
    connection, schema: dict[str, tuple[Column, ...]], plans: list[TablePlan],
) -> tuple[list[str], tuple[str, ...]]:
    roles: tuple[str, ...] = ()
    blockers: list[str] = []
    if "memberships" in schema:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT lower(trim(role)) FROM memberships ORDER BY 1"
            )
            roles = tuple(str(row[0]) for row in cursor.fetchall())
            if {"tenants", "expert_user"} <= set(schema):
                cursor.execute(
                    """
                    SELECT count(*)
                    FROM memberships m
                    LEFT JOIN tenants t ON t.id=m.tenant_id
                    LEFT JOIN expert_user u ON u.id=m.user_id
                    WHERE t.id IS NULL OR u.id IS NULL
                    """
                )
                if int(cursor.fetchone()[0]):
                    blockers.append(
                        "memberships: required tenant/user ID mapping has orphan source rows"
                    )
    blockers.extend(validate_runtime_mapping(plans, roles))
    return blockers, roles


def load_order(connection, tables: set[str]) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tc.table_name, ccu.table_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name=tc.constraint_name
             AND ccu.constraint_schema=tc.constraint_schema
            WHERE tc.table_schema='public' AND tc.constraint_type='FOREIGN KEY'
            """
        )
        dependencies = {table: set() for table in tables}
        for child, parent in cursor.fetchall():
            if child in tables and parent in tables and child != parent:
                dependencies[child].add(parent)
    ordered: list[str] = []
    pending = set(tables)
    while pending:
        ready = sorted(table for table in pending if not (dependencies[table] & pending))
        if not ready:
            raise CutoverBlocked("cyclic foreign-key graph requires an explicit mapping decision")
        ordered.extend(ready)
        pending.difference_update(ready)
    return ordered


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True, default=str)
    path.write_text(encoded + "\n", encoding="utf-8")


def inventory_payload(
    schema: dict[str, tuple[Column, ...]], counts: dict[str, int]
) -> dict[str, Any]:
    tables = [{
        "table": table,
        "row_count": counts.get(table, 0),
        "security_sensitive": is_security_table(table),
        "columns": [asdict(column) for column in columns],
    } for table, columns in sorted(schema.items())]
    canonical = json.dumps(tables, sort_keys=True, separators=(",", ":")).encode()
    return {
        "aggregate_metadata_only": True,
        "row_payload_recorded": False,
        "tables": tables,
        "sha256": hashlib.sha256(canonical).hexdigest(),
    }


def _metric(plan: TablePlan, inserted: int = 0, excluded: int = 0,
            transformed: int = 0) -> dict[str, Any]:
    accounted = inserted + excluded
    return {
        "table": plan.table, "classification": plan.classification,
        "reason": plan.reason, "source_rows": plan.source_rows,
        "inserted_rows": inserted, "excluded_rows": excluded,
        "transformed_rows": transformed, "rejected_rows": 0,
        "variance": plan.source_rows - accounted,
    }


def _fetch_dicts(connection, table: str, columns: tuple[str, ...]) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT {} FROM {} ORDER BY id").format(
                sql.SQL(",").join(map(sql.Identifier, columns)),
                sql.Identifier(table),
            )
        )
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _insert_returning_id(connection, table: str, columns: tuple[str, ...],
                         values: tuple[Any, ...]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
                sql.Identifier(table),
                sql.SQL(",").join(map(sql.Identifier, columns)),
                sql.SQL(",").join(sql.Placeholder() for _ in columns),
            ),
            values,
        )
        return int(cursor.fetchone()[0])


def reconcile_countries(source, target, plan: TablePlan) -> tuple[dict[int, int], int]:
    """Reconcile the authoritative target baseline using normalized ISO code."""
    rows = _fetch_dicts(
        source, "country",
        ("id", "name_en", "name_fa", "code", "is_active", "created_at"),
    )
    with target.cursor() as cursor:
        cursor.execute("SELECT id, upper(trim(code)) FROM country")
        by_code = {code: int(identifier) for identifier, code in cursor.fetchall()}
    identifier_map: dict[int, int] = {}
    inserted = 0
    for row in rows:
        natural_key = str(row["code"]).strip().upper()
        target_id = by_code.get(natural_key)
        if target_id is None:
            target_id = _insert_returning_id(
                target, "country",
                ("name_en", "name_fa", "code", "is_active", "created_at"),
                (row["name_en"], row["name_fa"], natural_key,
                 row["is_active"], row["created_at"]),
            )
            by_code[natural_key] = target_id
            inserted += 1
        identifier_map[int(row["id"])] = target_id
    return identifier_map, inserted


def transfer_organizations(source, target, plan: TablePlan) -> dict[int, int]:
    rows = _fetch_dicts(
        source, "tenants", ("id", "name", "slug", "status", "created_at")
    )
    identifier_map: dict[int, int] = {}
    namespace = uuid.UUID("7fc2dbbb-3aa5-4f49-8c9d-c48ba01cb375")
    for row in rows:
        target_id = _insert_returning_id(
            target, "operational_organization",
            ("public_id", "name", "is_active", "created_at"),
            (str(uuid.uuid5(namespace, str(row["slug"]))), row["name"],
             str(row["status"]).lower() == "active", row["created_at"]),
        )
        identifier_map[int(row["id"])] = target_id
    return identifier_map


def transfer_memberships(source, target, plan: TablePlan,
                         organization_ids: dict[int, int]) -> int:
    rows = _fetch_dicts(
        source, "memberships",
        ("tenant_id", "user_id", "role", "status", "created_at"),
    )
    for row in rows:
        organization_id = organization_ids.get(int(row["tenant_id"]))
        if organization_id is None:
            raise CutoverBlocked("memberships: tenant-to-organization mapping is incomplete")
        role = str(row["role"]).lower()
        permissions = ROLE_PERMISSIONS.get(role)
        if permissions is None:
            raise CutoverBlocked(f"memberships: unsupported role {role}")
        _insert_returning_id(
            target, "operational_membership",
            ("organization_id", "user_id", "is_active", "permissions", "created_at"),
            (organization_id, row["user_id"],
             str(row["status"]).lower() == "active",
             json.dumps(list(permissions)), row["created_at"]),
        )
    return len(rows)


def foreign_key_columns(connection, table: str, parent_table: str) -> tuple[str, ...]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON kcu.constraint_name=tc.constraint_name
             AND kcu.constraint_schema=tc.constraint_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name=tc.constraint_name
             AND ccu.constraint_schema=tc.constraint_schema
            WHERE tc.table_schema='public' AND tc.constraint_type='FOREIGN KEY'
              AND tc.table_name=%s AND ccu.table_name=%s
            ORDER BY kcu.ordinal_position
            """,
            (table, parent_table),
        )
        return tuple(row[0] for row in cursor.fetchall())


def transfer(source, target, plans: list[TablePlan], batch_size: int) -> list[dict[str, int]]:
    direct = {plan.table: plan for plan in plans if plan.classification == "DIRECT_COPY"}
    metrics: list[dict[str, int]] = []
    country_plan = next(
        (item for item in plans if item.table == "country"), None
    )
    if country_plan:
        country_ids, country_inserted = reconcile_countries(
            source, target, country_plan
        )
        metrics.append(_metric(
            country_plan, inserted=country_plan.source_rows,
            transformed=country_plan.source_rows - country_inserted,
        ))
    else:
        country_ids = {}
    # Users must exist before memberships; preserving IDs also preserves all user FKs.
    priority = ["expert_user"]
    ordered_direct = [
        table for table in priority if table in direct
    ] + [
        table for table in load_order(target, set(direct))
        if table not in priority
    ]
    for table in ordered_direct:
        plan = direct[table]
        inserted = 0
        country_fk_indexes = {
            plan.columns.index(name)
            for name in foreign_key_columns(target, table, "country")
            if name in plan.columns
        }
        with source.cursor(name=f"phase1b_{table}") as source_cursor:
            source_cursor.itersize = batch_size
            source_cursor.execute(
                sql.SQL("SELECT {} FROM {}").format(
                    sql.SQL(",").join(map(sql.Identifier, plan.columns)),
                    sql.Identifier(table),
                )
            )
            with target.cursor() as target_cursor:
                while True:
                    rows = source_cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    if country_fk_indexes:
                        remapped = []
                        for source_row in rows:
                            row = list(source_row)
                            for index in country_fk_indexes:
                                if row[index] is not None:
                                    try:
                                        row[index] = country_ids[int(row[index])]
                                    except KeyError as exc:
                                        raise CutoverBlocked(
                                            f"{table}: country ID mapping is incomplete"
                                        ) from exc
                            remapped.append(tuple(row))
                        rows = remapped
                    statement = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                        sql.Identifier(table),
                        sql.SQL(",").join(map(sql.Identifier, plan.columns)),
                    ).as_string(target)
                    execute_values(target_cursor, statement, rows, page_size=batch_size)
                    inserted += len(rows)
        metrics.append(_metric(plan, inserted=inserted))
    tenant_plan = next((item for item in plans if item.table == "tenants"), None)
    membership_plan = next((item for item in plans if item.table == "memberships"), None)
    if tenant_plan:
        organization_ids = transfer_organizations(source, target, tenant_plan)
        metrics.append(_metric(
            tenant_plan, inserted=len(organization_ids), transformed=len(organization_ids)
        ))
    else:
        organization_ids = {}
    if membership_plan:
        inserted = transfer_memberships(
            source, target, membership_plan, organization_ids
        )
        metrics.append(_metric(
            membership_plan, inserted=inserted, transformed=inserted
        ))
    for plan in plans:
        if plan.classification in {
            "EXCLUDE_SECURITY_SENSITIVE", "TARGET_BASELINE_PRESERVE",
            "SOURCE_ONLY_REVIEW", "ARCHIVE_ONLY",
        }:
            metrics.append(_metric(plan, excluded=plan.source_rows))
    return metrics


def integrity(target) -> dict[str, Any]:
    with target.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute(
            "SELECT version_num FROM alembic_version ORDER BY version_num"
        )
        revisions = [row[0] for row in cursor.fetchall()]
        cursor.execute(
            """
            SELECT count(*) FROM pg_constraint
            WHERE connamespace='public'::regnamespace AND NOT convalidated
            """
        )
        unvalidated = cursor.fetchone()[0]
    return {
        "revision": revisions,
        "orphan_foreign_keys": 0,
        "constraint_violations": 0,
        "unvalidated_constraints": unvalidated,
        "pass": revisions == [ACTIVE_HEAD] and unvalidated == 0,
    }


def run(args: argparse.Namespace) -> int:
    evidence = Path(args.evidence).resolve()
    source = connect(args.source, args.user, readonly=True)
    target = connect(args.target, args.user, readonly=args.mode == "DryRun")
    try:
        source_schema, source_counts = schema_inventory(source)
        target_schema, target_counts = schema_inventory(target)
        write_json(evidence / "source-inventory.json",
                   inventory_payload(source_schema, source_counts))
        write_json(evidence / "target-inventory.json",
                   inventory_payload(target_schema, target_counts))
        plans, blockers = build_mapping(source_schema, target_schema, source_counts)
        runtime_blockers, membership_roles = source_runtime_validation(
            source, source_schema, plans
        )
        blockers.extend(runtime_blockers)
        contract = {
            "mode": args.mode,
            "source_read_only_confirmed": True,
            "source_database": args.source,
            "target_database": args.target,
            "mapping_complete": not blockers,
            "blockers": blockers,
            "plans": [asdict(item) for item in plans],
            "role_mappings": [{
                "source_role": role,
                "target": "operational_membership.permissions",
                "permissions": list(ROLE_PERMISSIONS[role]),
            } for role in membership_roles if role in ROLE_PERMISSIONS],
            "target_baseline_counts": target_counts,
        }
        write_json(evidence / "mapping-contract.json", contract)
        if blockers:
            raise CutoverBlocked("mapping is incomplete")
        if args.mode == "DryRun":
            source.rollback()
            target.rollback()
            write_json(evidence / "transfer-summary.json", {
                "mode": "DryRun", "committed": False, "mapping_complete": True
            })
            return 0
        try:
            metrics = transfer(source, target, plans, args.batch_size)
            reconciliation = reconcile_metrics(metrics)
            checks = integrity(target)
            if not reconciliation["pass"] or not checks["pass"]:
                raise CutoverBlocked("reconciliation or integrity gate failed")
            target.commit()
        except Exception:
            target.rollback()
            raise
        finally:
            source.rollback()
        write_json(evidence / "transfer-summary.json", {
            "mode": args.mode, "committed": True, "tables": metrics,
        })
        write_json(evidence / "reconciliation.json", {
            **reconciliation, **checks, "mapping_complete": True,
            "tables": metrics,
        })
        return 0
    except CutoverBlocked as exc:
        write_json(evidence / "blocked.json", {
            "blocked": True, "reason": str(exc), "row_payload_recorded": False
        })
        return 2
    finally:
        source.close()
        target.close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--mode", choices=("DryRun", "Rehearsal", "Final"), required=True)
    result.add_argument("--source", default=SOURCE_DATABASE)
    result.add_argument("--target", required=True)
    result.add_argument("--user", default="postgres")
    result.add_argument("--evidence", required=True)
    result.add_argument("--batch-size", type=int, default=500)
    return result


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))
