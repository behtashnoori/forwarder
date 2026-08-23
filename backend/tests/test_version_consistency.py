import json
from pathlib import Path

import backend

ROOT = Path(__file__).resolve().parents[2]


def test_governed_source_versions_are_consistent():
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    builder = (ROOT / "scripts" / "build_release_package.py").read_text(
        encoding="utf-8"
    )
    assert package == backend.__version__ == "1.9.5.1"
    assert 'VERSION = "1.9.5.1"' not in builder
    assert 'TAG = "v1.9.5.1"' not in builder
    assert 'p.add_argument("--authorized-commit", required=True)' in builder
    assert 'p.add_argument("--release-label", required=True)' in builder
