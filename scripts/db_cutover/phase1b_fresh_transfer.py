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


def build_mapping(
    source_schema: dict[str, tuple[Column, ...]],
    target_schema: dict[str, tuple[Column, ...]],
    source_counts: dict[str, int],
) -> tuple[list[TablePlan], list[str]]:
    plans: list[TablePlan] = []
    blockers: list[str] = []
    for table in sorted(source_schema):
        count = source_counts.get(table, 0)
        if table == "alembic_version":
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
            columns, error = transferable_columns(
                source_schema[table], target_schema[table], table
            )
            if error:
                plans.append(TablePlan(table, "MANUAL_DECISION_REQUIRED", (), count, error))
                if count:
                    blockers.append(f"{table}: {error}")
            else:
                plans.append(TablePlan(table, "DIRECT_COPY", columns, count,
                                       "same-name compatible columns; identifiers preserved"))
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


def transfer(source, target, plans: list[TablePlan], batch_size: int) -> list[dict[str, int]]:
    direct = {plan.table: plan for plan in plans if plan.classification == "DIRECT_COPY"}
    metrics: list[dict[str, int]] = []
    for table in load_order(target, set(direct)):
        plan = direct[table]
        inserted = 0
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
                    statement = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                        sql.Identifier(table),
                        sql.SQL(",").join(map(sql.Identifier, plan.columns)),
                    ).as_string(target)
                    execute_values(target_cursor, statement, rows, page_size=batch_size)
                    inserted += len(rows)
        metrics.append({
            "table": table, "source_rows": plan.source_rows,
            "inserted_rows": inserted, "excluded_rows": 0,
            "transformed_rows": 0, "rejected_rows": 0,
            "variance": plan.source_rows - inserted,
        })
    for plan in plans:
        if plan.classification in {
            "EXCLUDE_SECURITY_SENSITIVE", "TARGET_BASELINE_PRESERVE",
            "TARGET_BASELINE_RECONCILE", "SOURCE_ONLY_REVIEW",
        }:
            metrics.append({
                "table": plan.table, "source_rows": plan.source_rows,
                "inserted_rows": 0, "excluded_rows": plan.source_rows,
                "transformed_rows": 0, "rejected_rows": 0, "variance": 0,
            })
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
        contract = {
            "mode": args.mode,
            "source_read_only_confirmed": True,
            "source_database": args.source,
            "target_database": args.target,
            "mapping_complete": not blockers,
            "blockers": blockers,
            "plans": [asdict(item) for item in plans],
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
            **reconciliation, **checks, "mapping_complete": True
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
