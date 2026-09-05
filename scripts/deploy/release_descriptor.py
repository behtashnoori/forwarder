"""Immutable, non-production release descriptor validation."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

REQUIRED = {"release_id","application_source_sha","rc_zip_sha256","alembic_head","runtime_id","runtime_sha256","deployment_package_id","previous_release_id","previous_application_source_sha","qualification"}
LIVE_FORBIDDEN = {"database_name","listener_pid","iis_physical_path","scheduled_task_path","runtime_executable_path"}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path: Path) -> dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    missing=REQUIRED-set(data)
    if missing or LIVE_FORBIDDEN & set(data):
        raise ValueError(f"invalid release descriptor; missing={sorted(missing)} forbidden={sorted(LIVE_FORBIDDEN & set(data))}")
    for name in ("application_source_sha","rc_zip_sha256","runtime_sha256","previous_application_source_sha"):
        if len(data[name]) != 64 or any(c not in "0123456789abcdef" for c in data[name]):
            raise ValueError(f"invalid {name}")
    return data
