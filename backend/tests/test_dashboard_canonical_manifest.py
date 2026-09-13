import hashlib
import json
import os

from backend.dashboard_service import _MANIFEST_PATH, system_dashboard


def test_system_manifest_is_valid_and_path_independent():
    previous = os.getcwd()
    try:
        os.chdir(os.path.abspath(os.sep))
        manifest = system_dashboard("operations-control-tower")
    finally:
        os.chdir(previous)
    assert _MANIFEST_PATH.is_file()
    assert manifest["definition"]["widgets"][-1]["drilldown"]["enabled"] is False
    assert manifest["dashboard_schema_version"] == "dashboard-definition-v1"


def test_frozen_control_tower_parity_hash():
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    normalized = json.dumps(manifest["definition"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(normalized).hexdigest() == "550a5bce4128c850ea500391177e88446f26ee88dda5e369082081cf1e9aec25"
