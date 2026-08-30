"""The ADR-043 pre-cutover command must remain fail-closed for payload integrity."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = ROOT / "docs/operational/evidence/adr-043-controlled-production-deployment-runbook.md"


def test_pre_cutover_gate_verifies_manifest_payload_not_raw_staged_file_count():
    source = RUNBOOK.read_text(encoding="utf-8")
    start = source.index("$manifestPaths=")
    gate = source[start : source.index("$targetFile=", start)]

    for required in (
        "manifest file missing",
        "manifest size mismatch",
        "manifest hash mismatch",
        "staged content hash differs from manifest",
        "non-payload staged file absent from manifest",
        "manifest records are not sorted by canonical path",
        "manifest must not govern itself",
    ):
        assert required in gate

    assert "staged file count differs from manifest inventory" not in gate


def test_pre_cutover_gate_excludes_only_documented_post_staging_materialization():
    source = RUNBOOK.read_text(encoding="utf-8")
    assert "RUNTIME_EXCLUSIONS=.venv/**,**/__pycache__/**,**/*.pyc" in source
    assert "manifest record crosses runtime-materialization boundary" in source
    assert "No other staged extra is accepted." in source
