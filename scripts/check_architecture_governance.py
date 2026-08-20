"""Read-only structural checks for the Forwarder architecture governance baseline."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_DIR = ROOT / "docs" / "architecture"
ADR_DIR = ROOT / "docs" / "operational" / "adr"
MIGRATION_DIR = ROOT / "backend" / "migrations" / "versions"

REQUIRED_DOCUMENTS = (
    "FORWARDER-ARCHITECTURE-BASELINE.md",
    "ADR-INDEX.md",
    "ADR-TEMPLATE.md",
    "CODEX-DEVELOPMENT-GATE.md",
    "ARCHITECTURE-REVIEW-CHECKLIST.md",
    "LEGACY-CANONICAL-MAP.md",
    "ARCHITECTURE-DRIFT-REPORT.md",
)

CANONICAL_MODEL_FILES = (
    ROOT / "backend" / "operational_models.py",
    ROOT / "backend" / "cargo_models.py",
    ROOT / "backend" / "logistics_network_models.py",
    ROOT / "backend" / "project_configuration_models.py",
    ROOT / "backend" / "mdpm_models.py",
    ROOT / "backend" / "economics_models.py",
    ROOT / "backend" / "oip_models.py",
)

REQUIRED_BASELINE_TERMS = (
    "Project -> OperationalShipment -> ExecutionUnit",
    "No implementation may silently change architecture",
    "timestamp with time zone",
    "TrackingLocationReference",
    "CargoCatalogItem -> ShipmentCargoItem -> OperationalShipment",
    "ArtifactAssociation",
)


@dataclass(frozen=True)
class Failure:
    check: str
    detail: str


def _assignment_value(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                try:
                    return ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    return None
    return None


def check_required_documents() -> list[Failure]:
    failures = []
    for name in REQUIRED_DOCUMENTS:
        path = ARCHITECTURE_DIR / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            failures.append(Failure("required-documents", f"missing or empty: {path.relative_to(ROOT)}"))
    return failures


def check_baseline_contract() -> list[Failure]:
    path = ARCHITECTURE_DIR / "FORWARDER-ARCHITECTURE-BASELINE.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    return [
        Failure("baseline-contract", f"baseline does not state: {term}")
        for term in REQUIRED_BASELINE_TERMS
        if term not in text
    ]


def check_adr_index_coverage() -> list[Failure]:
    index = (ARCHITECTURE_DIR / "ADR-INDEX.md").read_text(encoding="utf-8")
    failures = []
    for path in sorted(ADR_DIR.glob("ADR-*.md")):
        match = re.match(r"ADR-(\d{3})-", path.name)
        if match and f"[{int(match.group(1)):03d}]" not in index:
            failures.append(Failure("adr-index", f"not indexed: {path.relative_to(ROOT)}"))
    allowed = {"PROPOSED", "ACCEPTED", "SUPERSEDED", "DEPRECATED", "REJECTED"}
    for line_number, line in enumerate(index.splitlines(), 1):
        if re.match(r"^\| \[\d{3}\]", line):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 3 and cells[2] not in allowed:
                failures.append(Failure("adr-index", f"line {line_number} has invalid status {cells[2]!r}"))
    return failures


def _is_datetime_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "DateTime"
        or isinstance(func, ast.Name)
        and func.id == "DateTime"
    )


def check_canonical_datetime_columns() -> list[Failure]:
    failures = []
    for path in CANONICAL_MODEL_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_datetime_call(node):
                continue
            timezone_keyword = next((kw.value for kw in node.keywords if kw.arg == "timezone"), None)
            if not isinstance(timezone_keyword, ast.Constant) or timezone_keyword.value is not True:
                failures.append(
                    Failure(
                        "canonical-time",
                        f"{path.relative_to(ROOT)}:{node.lineno} DateTime must declare timezone=True",
                    )
                )
    return failures


def check_operational_terminology() -> list[Failure]:
    failures = []
    for path in sorted((ROOT / "backend").rglob("*.py")):
        if "migrations" in path.parts or "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "ShipmentJob":
                failures.append(Failure("terminology", f"forbidden ShipmentJob class: {path.relative_to(ROOT)}:{node.lineno}"))
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        try:
                            value = ast.literal_eval(node.value)
                        except (ValueError, TypeError):
                            value = None
                        if value == "shipment_job":
                            failures.append(Failure("terminology", f"forbidden shipment_job table: {path.relative_to(ROOT)}:{node.lineno}"))
    return failures


def check_alembic_sole_head() -> list[Failure]:
    revisions: dict[str, Path] = {}
    parents: set[str] = set()
    failures = []
    for path in sorted(MIGRATION_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = _assignment_value(tree, "revision")
        down_revision = _assignment_value(tree, "down_revision")
        if not isinstance(revision, str):
            failures.append(Failure("alembic-head", f"unreadable revision in {path.relative_to(ROOT)}"))
            continue
        if revision in revisions:
            failures.append(Failure("alembic-head", f"duplicate revision {revision}"))
        revisions[revision] = path
        if isinstance(down_revision, str):
            parents.add(down_revision)
        elif isinstance(down_revision, (tuple, list)):
            parents.update(parent for parent in down_revision if isinstance(parent, str))
        elif down_revision is not None:
            failures.append(Failure("alembic-head", f"unreadable down_revision in {path.relative_to(ROOT)}"))
    missing = sorted(parents - revisions.keys())
    if missing:
        failures.append(Failure("alembic-head", f"missing parent revisions: {', '.join(missing)}"))
    heads = sorted(set(revisions) - parents)
    if len(heads) != 1:
        failures.append(Failure("alembic-head", f"expected one static head, found {heads}"))
    return failures


def run_checks() -> list[Failure]:
    checks = (
        check_required_documents,
        check_baseline_contract,
        check_adr_index_coverage,
        check_canonical_datetime_columns,
        check_operational_terminology,
        check_alembic_sole_head,
    )
    return [failure for check in checks for failure in check()]


def main() -> int:
    failures = run_checks()
    if failures:
        for failure in failures:
            print(f"FAIL [{failure.check}] {failure.detail}", file=sys.stderr)
        return 1
    print("Forwarder architecture governance checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
