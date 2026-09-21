from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "forwarder_uat_release_builder", ROOT / "scripts/build_forwarder_uat_release.py"
)
BUILDER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(BUILDER)


def backend_version() -> str:
    tree = ast.parse((ROOT / "backend/__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("backend.__version__ is absent")


def test_uat_version_identity_matches_authoritative_sources():
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    source = json.loads(
        (ROOT / "release/forwarder-uat-v1.10.0.json").read_text(encoding="utf-8")
    )
    assert package["version"] == backend_version() == BUILDER.VERSION == "1.10.0"
    assert source["new_product_version"] == BUILDER.VERSION
    assert source["previous_product_version"] == BUILDER.PREVIOUS_VERSION
    assert source["release_tag"] == BUILDER.RELEASE_TAG


def test_uat_builder_requires_the_single_governed_database_head():
    _, heads = BUILDER.revision_graph(ROOT / "backend/migrations/versions")
    assert heads == [BUILDER.DATABASE_HEAD]
    assert BUILDER.DATABASE_HEAD == "20260926_fixed_shipment_responsible_expert"


def test_new_release_identity_is_uat_only_and_contains_no_retired_stage_label():
    identities = "\n".join(
        (BUILDER.RELEASE_ID, BUILDER.RELEASE_TAG, f"Forwarder-UAT-v{BUILDER.VERSION}")
    ).lower()
    assert "uat" in identities
    assert "demo" not in identities
    assert "production" not in identities


def test_start_script_fails_closed_to_owned_loopback_uat_database():
    assert "forwarder_uat_" in BUILDER.START
    assert "127.0.0.1" in BUILDER.START
    assert "APP_ENV='uat'" in BUILDER.START
    assert "AUTO_MIGRATE_ON_STARTUP='false'" in BUILDER.START
    assert "backend.migration_cli check" in BUILDER.START


def test_package_verifier_pins_version_tag_and_database_head():
    assert BUILDER.VERSION in BUILDER.VERIFY
    assert BUILDER.RELEASE_TAG in BUILDER.VERIFY
    assert BUILDER.DATABASE_HEAD in BUILDER.VERIFY
    assert "PACKAGE_SOURCE_SHA_VERIFIED=YES" in BUILDER.VERIFY
