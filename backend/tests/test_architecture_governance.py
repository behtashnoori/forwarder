"""Architecture-governance checks must stay executable in the normal backend suite."""

from scripts.check_architecture_governance import run_checks


def test_architecture_governance_contracts():
    failures = run_checks()
    assert failures == [], "\n".join(
        f"[{failure.check}] {failure.detail}" for failure in failures
    )
