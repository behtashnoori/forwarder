from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from backend.services.timeline_service import (
    build_workflow_steps_from_status,
    build_workflow_steps_simple_4,
)
from backend.services.utc_timestamp import current_utc_timestamp


def test_timeline_builders_share_request_created_at_contract(monkeypatch):
    value = datetime(2026, 7, 25, 19, 1, 58, 519833)
    request_row = SimpleNamespace(id=1, status="new", created_at=value)
    monkeypatch.setattr("backend.services.timeline_service.get_final_decision_from_logs", lambda _id: None)

    simple = build_workflow_steps_simple_4(request_row, assigned_at=value)
    full = build_workflow_steps_from_status("new", value)

    assert simple[0]["completed_at"] == "2026-07-25T19:01:58.519833Z"
    assert full[0]["completed_at"] == simple[0]["completed_at"]


def test_timeline_request_created_at_none_is_preserved(monkeypatch):
    request_row = SimpleNamespace(id=1, status="new", created_at=None)
    monkeypatch.setattr("backend.services.timeline_service.get_assigned_at", lambda _req: None)
    monkeypatch.setattr("backend.services.timeline_service.get_final_decision_from_logs", lambda _id: None)
    assert build_workflow_steps_simple_4(request_row, assigned_at=None)[0]["completed_at"] is None
    assert build_workflow_steps_from_status("new", None)[0]["completed_at"] is None


def test_timeline_assignment_timestamp_remains_outside_legacy_helper(monkeypatch):
    request_row = SimpleNamespace(
        id=1,
        status="new",
        created_at=datetime(2026, 7, 25, 19, 1, 58),
    )
    assignment = datetime(2026, 7, 25, 20, 2, 3)
    monkeypatch.setattr("backend.services.timeline_service.get_final_decision_from_logs", lambda _id: None)
    steps = build_workflow_steps_simple_4(request_row, assigned_at=assignment)
    assert steps[1]["completed_at"] == "2026-07-25T20:02:03"


def test_ephemeral_timestamp_is_explicit_parseable_utc():
    value = current_utc_timestamp()
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert value.endswith(("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_operational_code_does_not_use_legacy_datetime_helper():
    root = Path(__file__).parents[1]
    sources = [
        (root / "operational_models.py").read_text(encoding="utf-8"),
        (root / "services" / "operational_service.py").read_text(encoding="utf-8"),
        (root / "services" / "route_orchestration_service.py").read_text(encoding="utf-8"),
    ]
    assert all("legacy_datetime" not in source for source in sources)
    aware = datetime(2026, 7, 25, 19, 1, 58, tzinfo=timezone.utc).isoformat()
    assert aware.endswith("+00:00")
