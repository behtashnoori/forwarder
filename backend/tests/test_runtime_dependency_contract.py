from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_DRIVER = "psycopg2-binary==2.9.11"


def _declared_requirements(path: Path) -> set[str]:
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_postgresql_runtime_driver_is_exactly_declared():
    assert EXPECTED_DRIVER in _declared_requirements(ROOT / "requirements.txt")
    assert EXPECTED_DRIVER in _declared_requirements(ROOT / "backend" / "requirements.txt")
