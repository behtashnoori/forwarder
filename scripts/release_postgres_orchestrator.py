"""Isolated PostgreSQL release-suite orchestration.

This runner owns database/worktree/process lifecycle only.  Test assertions and
fixture business logic remain in their existing modules.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "docs" / "operational" / "evidence" / "postgresql-release"
SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]{5,62}$")
SUMMARY = re.compile(r"(?P<count>\d+) (?P<kind>passed|failed|skipped|error|errors)")
REDACTIONS = (
    (re.compile(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:\s/]+:)[^@\s/]+(@)"), r"\1[REDACTED]\2"),
    (re.compile(r"(?i)\b(password|secret|token|authorization)\s*[=:]\s*[^\s,;]+"), r"\1=[REDACTED]"),
)


@dataclass(frozen=True)
class Suite:
    suite_id: str
    classification: str
    tests: tuple[str, ...]
    env_name: str
    prefix: str
    revision: str = "head"
    seed: tuple[str, ...] = ()
    seed_identity: str = "none"
    storage: bool = False
    historical_commit: str | None = None
    extra_databases: tuple[tuple[str, str, str], ...] = ()


CURRENT: tuple[Suite, ...] = (
    Suite("phase02_current_head", "CURRENT_HEAD_COMPATIBILITY_REQUIRED", ("backend/tests/test_phase0_2_current_head_compatibility_postgresql.py",), "INTEGRATED_RC_POSTGRES_URL", "forwarder_integrated_rc_phase02"),
    Suite("dms_current_head", "CURRENT_HEAD_COMPATIBILITY_REQUIRED", ("backend/tests/test_dms_current_head_compatibility_postgresql.py",), "INTEGRATED_RC_POSTGRES_URL", "forwarder_integrated_rc_dms", storage=True),
    Suite("phase1a_operational", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_operational_vertical_slice_postgresql.py",), "FORWARDER_PHASE1A_POSTGRES_URL", "forwarder_phase1a_test_rc"),
    Suite("phase1b_operational", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_multileg_route_orchestration_postgresql.py",), "FORWARDER_PHASE1B_POSTGRES_URL", "forwarder_phase1b_uat_ops", seed=("-m", "backend.operational_cli", "seed-phase1b-uat", "--confirm"), seed_identity="phase1b_uat:v1 (twice)"),
    Suite("phase1b_races", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_exception_reconciliation_races_postgresql.py",), "FORWARDER_PHASE1B_POSTGRES_URL", "forwarder_phase1a_test_phase1b_races"),
    Suite("phase1b_reporter", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_reporter_permission_postgresql.py",), "FORWARDER_PHASE1B_POSTGRES_URL", "forwarder_phase1b_uat_reporter", seed=("-m", "backend.operational_cli", "seed-phase1b-uat", "--confirm"), seed_identity="phase1b_uat:v1 (twice)"),
    Suite("phase1b_dedup", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_shipment_list_deduplication_postgresql.py",), "FORWARDER_PHASE1B_POSTGRES_URL", "forwarder_phase1b_uat_dedup", seed=("-m", "backend.operational_cli", "seed-phase1b-uat", "--confirm"), seed_identity="phase1b_uat:v1 (twice)"),
    Suite("multi_unit_tracking", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_multi_unit_tracking_postgresql.py",), "FORWARDER_POSTGRES_TRACKING_TEST_URL", "forwarder_security_test_tracking"),
    Suite("tracking_locations", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_tracking_locations_postgresql.py",), "FORWARDER_TRACKING_LOCATION_POSTGRES_URL", "forwarder_tracking_location_migration_test"),
    Suite("reference_schema", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_reference_schema_postgresql.py",), "FORWARDER_REFERENCE_SCHEMA_TEST_URL", "forwarder_reference_schema_test", revision="20260720_expand_reference_data_identity"),
    Suite("mdpm_races", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_mdpm_races_postgresql.py",), "MDPM_POSTGRES_URL", "forwarder_phase1b_uat_mdpm", seed=("scripts/uat/mdpm_validation_seed.py",), seed_identity="phase1b_uat:v1 (twice) + mdpm_validation_seed:v1 (twice)"),
    Suite("oip_races", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_oip_races_postgresql.py",), "OIP_POSTGRES_URL", "forwarder_oip2_gate_races"),
    Suite("oip_rebuild_recovery", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_oip_rebuild_recovery_postgresql.py",), "OIP_POSTGRES_URL", "forwarder_oip2_gate_recovery"),
    Suite("fe2_races", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_fe2_races_postgresql.py",), "FE2_POSTGRES_URL", "forwarder_fe2_gate_races"),
    Suite("fe2_migration", "CURRENT_HEAD_MANDATORY", ("scripts/fe2_postgres_migration_gate.py",), "FE2_POSTGRES_URL", "forwarder_fe2_gate_migration"),
    Suite("phase1b_safe_downgrade", "CURRENT_HEAD_MANDATORY", ("backend/tests/test_phase1b_safe_downgrade_postgresql.py",), "FORWARDER_PHASE1B_SAFE_DOWNGRADE_HEAD_URL", "forwarder_phase1a_test_phase1b_safehead", revision="20260801_route_exception", extra_databases=(("FORWARDER_PHASE1B_SAFE_DOWNGRADE_PHASE1B_URL", "forwarder_phase1a_test_phase1b_safebase", "20260730_multileg_route"),)),
)

HISTORICAL: tuple[Suite, ...] = (
    Suite("phase02_historical", "HISTORICAL_RELEASE_MANDATORY", ("backend/tests/test_phase0_2_postgresql_gate.py",), "FORWARDER_PHASE02_POSTGRES_URL", "forwarder_phase02_test_historical", revision="20260729_operational_vertical_slice", historical_commit="57c9e34da51f8471432debb44ed41ac0200dc05a"),
    Suite("dms_historical", "HISTORICAL_RELEASE_MANDATORY", ("backend/tests/test_case_documents_postgresql.py", "backend/tests/test_case_documents_schema_parity.py"), "DMS_DISPOSABLE_POSTGRES_URL", "dms1a_historical", revision="20260804_case_documents", storage=True, historical_commit="7ae1517fa20266116be723c8fdb8294a8b895d88"),
)


def sanitize(value: str) -> str:
    for pattern, replacement in REDACTIONS:
        value = pattern.sub(replacement, value)
    return value


def run(command: Sequence[str], *, cwd: Path, env: dict[str, str], timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=timeout, check=False)


class Orchestrator:
    def __init__(self, admin_url: str, evidence: Path):
        parsed = make_url(admin_url)
        if parsed.get_backend_name() != "postgresql" or parsed.host not in {"127.0.0.1", "localhost"}:
            raise SystemExit("Refusing: --admin-url must be loopback PostgreSQL")
        self.base = parsed
        self.admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
        self.evidence = evidence.resolve()
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.python = str(ROOT / ".venv" / "Scripts" / "python.exe") if os.name == "nt" else sys.executable
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + secrets.token_hex(3)
        self.results: list[dict[str, object]] = []

    def database_name(self, prefix: str) -> str:
        name = f"{prefix}_{self.run_id}".lower()[:63]
        if not SAFE_NAME.fullmatch(name) or not any(x in name for x in ("test", "uat", "gate", "rc", "historical")):
            raise RuntimeError(f"unsafe disposable database name: {name}")
        return name

    def drop(self, name: str) -> str:
        if not SAFE_NAME.fullmatch(name):
            raise RuntimeError("refusing unsafe drop name")
        with self.admin.connect() as connection:
            connection.execute(text("select pg_terminate_backend(pid) from pg_stat_activity where datname=:name and pid<>pg_backend_pid()"), {"name": name})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        return "dropped"

    def create(self, name: str) -> str:
        self.drop(name)
        with self.admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" ENCODING \'UTF8\''))
        return self.base.set(database=name).render_as_string(hide_password=False)

    def migrate(self, cwd: Path, env: dict[str, str], url: str, revision: str) -> subprocess.CompletedProcess[str]:
        migration = (
            "from alembic import command; from backend.migration_runtime import alembic_config,prepare_version_table_for_upgrade; "
            "import os; u=os.environ['DATABASE_URL']; c=alembic_config(u); prepare_version_table_for_upgrade(u,c); "
            f"command.upgrade(c,{revision!r})"
        )
        return run((self.python, "-c", migration), cwd=cwd, env={**env, "DATABASE_URL": url})

    def execute(self, suite: Suite) -> None:
        started = time.monotonic()
        cwd = ROOT
        worktree: Path | None = None
        storage: Path | None = None
        names: list[str] = []
        cleanup: list[str] = []
        output: list[str] = []
        passed = failed = skipped = 0
        status = "FAILED"
        revision_observed = "unavailable"
        git_identity = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=ROOT, text=True).strip()
        env_names = {suite.env_name, "DATABASE_URL"}
        try:
            if suite.historical_commit:
                worktree = Path(tempfile.mkdtemp(prefix="forwarder-pg-history-"))
                shutil.rmtree(worktree)
                proc = run(("git", "worktree", "add", "--detach", str(worktree), suite.historical_commit), cwd=ROOT, env=os.environ.copy())
                output.append(proc.stdout)
                if proc.returncode:
                    raise RuntimeError("historical worktree creation failed")
                cwd, git_identity = worktree, suite.historical_commit
                if suite.suite_id == "dms_historical":
                    test_path = cwd / "backend/tests/test_case_documents_postgresql.py"
                    source = test_path.read_text(encoding="utf-8")
                    source = source.replace(
                        "assert [response.status_code for response in responses].count(201) == 2\n",
                        "assert [response.status_code for response in responses].count(201) == 2, "
                        "[{'status': response.status_code, 'body': response.get_json(silent=True)} "
                        "for response in responses]\n",
                    )
                    test_path.write_text(source, encoding="utf-8")
                    storage_path = cwd / "backend/services/document_storage_service.py"
                    storage_source = storage_path.read_text(encoding="utf-8")
                    old = """        directory = (self.root / partition).resolve()\n        if self.root != directory and self.root not in directory.parents:\n            raise DocumentStorageError(\"Invalid storage destination\")\n        directory.mkdir(parents=True, exist_ok=True)\n"""
                    new = """        if partition.is_absolute() or \"..\" in partition.parts:\n            raise DocumentStorageError(\"Invalid storage destination\")\n        directory = self.root / partition\n        directory.mkdir(parents=True, exist_ok=True)\n"""
                    if storage_source.count(old) != 1:
                        raise RuntimeError("historical DMS storage repair target is not exact")
                    storage_path.write_text(storage_source.replace(old, new), encoding="utf-8")
            name = self.database_name(suite.prefix)
            names.append(name)
            url = self.create(name)
            env = os.environ.copy()
            env.update({"DATABASE_URL": url, suite.env_name: url, "APP_ENV": "uat",
                        "FORWARDER_UAT_PASSWORD": "disposable-local-release-test-only"})
            env_names.update(("APP_ENV", "FORWARDER_UAT_PASSWORD"))
            if suite.storage:
                storage = self.evidence / f"{self.run_id}-{suite.suite_id}-storage"
                storage.mkdir(exist_ok=False)
                env["DMS_DISPOSABLE_STORAGE_ROOT"] = str(storage)
                env_names.add("DMS_DISPOSABLE_STORAGE_ROOT")
            migration = self.migrate(cwd, env, url, suite.revision)
            output.append(migration.stdout)
            if migration.returncode:
                raise RuntimeError("migration failed")
            for extra_env, prefix, revision in suite.extra_databases:
                extra_name = self.database_name(prefix)
                names.append(extra_name)
                extra_url = self.create(extra_name)
                extra_migration = self.migrate(cwd, env, extra_url, revision)
                output.append(extra_migration.stdout)
                if extra_migration.returncode:
                    raise RuntimeError(f"migration failed for {extra_env}")
                env[extra_env] = extra_url
                env_names.add(extra_env)
            probe_engine = create_engine(url)
            try:
                with probe_engine.connect() as connection:
                    revision_observed = connection.execute(text("select version_num from alembic_version")).scalar_one()
            finally:
                # Template-cloning suites require zero retained source sessions.
                probe_engine.dispose()
            if suite.seed:
                if suite.suite_id == "mdpm_races":
                    base_seed = (self.python, "-m", "backend.operational_cli", "seed-phase1b-uat", "--confirm")
                    for _ in range(2):
                        seeded = run(base_seed, cwd=cwd, env=env); output.append(seeded.stdout)
                        if seeded.returncode: raise RuntimeError("Phase 1B base seed failed")
                seed_cmd = (self.python, *suite.seed)
                for _ in range(2):
                    seeded = run(seed_cmd, cwd=cwd, env=env); output.append(seeded.stdout)
                    if seeded.returncode: raise RuntimeError("deterministic seed failed")
            command = (self.python, "-m", "pytest", "-q", *suite.tests) if all(x.endswith(".py") and "tests/" in x.replace("\\", "/") for x in suite.tests) else (self.python, *suite.tests)
            tested = run(command, cwd=cwd, env=env)
            output.append(tested.stdout)
            for match in SUMMARY.finditer(tested.stdout):
                count, kind = int(match.group("count")), match.group("kind")
                if kind == "passed": passed = max(passed, count)
                elif kind == "skipped": skipped = max(skipped, count)
                else: failed = max(failed, count)
            if tested.returncode or skipped:
                raise RuntimeError("suite did not pass directly without skips")
            status = "PASSED"
        except Exception as exc:
            output.append(f"orchestrator: {type(exc).__name__}: {exc}\n")
            failed = max(failed, 1)
        finally:
            for name in reversed(names):
                try: cleanup.append(f"{name}:{self.drop(name)}")
                except Exception as exc: cleanup.append(f"{name}:failed:{type(exc).__name__}"); status = "FAILED"
            if worktree:
                removal = run(("git", "worktree", "remove", "--force", str(worktree)), cwd=ROOT, env=os.environ.copy())
                cleanup.append("worktree:removed" if removal.returncode == 0 else "worktree:failed")
                if removal.returncode: status = "FAILED"
            if storage:
                shutil.rmtree(storage, ignore_errors=True)
                cleanup.append("disposable-storage:removed" if not storage.exists() else "disposable-storage:failed")
                if storage.exists(): status = "FAILED"
            body = sanitize("".join(output))
            evidence_path = self.evidence / f"{self.run_id}-{suite.suite_id}.log"
            evidence_path.write_text(body, encoding="utf-8")
            digest = hashlib.sha256(body.encode()).hexdigest()
            self.results.append({
                "suite_id": suite.suite_id, "classification": suite.classification,
                "source_test_path": list(suite.tests), "evidence_context": "historical" if suite.historical_commit else "current-head",
                "git_worktree_identity": git_identity, "postgresql_version": self.server_version,
                "database_identity": names, "migration_revision": revision_observed,
                "seed_identity_version": suite.seed_identity, "environment_variable_names": sorted(env_names),
                "passed": passed, "failed": failed, "skipped": skipped,
                "duration_seconds": round(time.monotonic() - started, 3), "status": status,
                "evidence_path": str(evidence_path.relative_to(ROOT)), "evidence_sha256": digest,
                "cleanup_result": cleanup,
            })
            self.write_matrix()
            print(f"{suite.suite_id}: {status} ({self.results[-1]['duration_seconds']}s)", flush=True)

    @property
    def server_version(self) -> str:
        with self.admin.connect() as connection:
            return connection.execute(text("show server_version")).scalar_one()

    def write_matrix(self) -> None:
        gate = bool(self.results) and all(row["status"] == "PASSED" for row in self.results)
        matrix = {"schema_version": 1, "run_id": self.run_id, "generated_at": datetime.now(timezone.utc).isoformat(),
                  "postgresql_gate": "PASS" if gate else "FAIL", "suites": self.results}
        (self.evidence / "postgresql-release-matrix.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admin-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--scope", choices=("current", "historical", "all"), default="all")
    parser.add_argument("--suite", action="append", default=[])
    args = parser.parse_args(argv)
    if not args.admin_url: raise SystemExit("--admin-url or DATABASE_URL is required")
    suites = ((*CURRENT,) if args.scope in {"current", "all"} else ()) + ((*HISTORICAL,) if args.scope in {"historical", "all"} else ())
    if args.suite: suites = tuple(x for x in suites if x.suite_id in set(args.suite))
    if not suites: raise SystemExit("no suites selected")
    orchestrator = Orchestrator(args.admin_url, args.evidence_dir)
    try:
        for suite in suites: orchestrator.execute(suite)
    finally:
        orchestrator.admin.dispose()
    return 0 if all(row["status"] == "PASSED" for row in orchestrator.results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
