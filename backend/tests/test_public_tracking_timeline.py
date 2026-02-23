"""Tests for 4-step customer timeline (workflow_steps_simple) in public tracking."""
from datetime import datetime, timedelta
import json
import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ShipmentRequest, ExpertConsoleLog
from backend.routes.public_tracking import (
    _workflow_steps_simple_4,
    _get_final_decision_from_logs,
    WORKFLOW_STEP_DEFS_SIMPLE_4,
)


@pytest.fixture
def app_with_tables():
    """App with in-memory DB and tables created."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def client(app_with_tables):
    return app_with_tables.test_client()


def _make_request(app, status="new", created_at=None):
    """Create a minimal ShipmentRequest in the app context."""
    if created_at is None:
        created_at = datetime.utcnow()
    with app.app_context():
        req = ShipmentRequest(
            contact_phone="09121234567",
            shipping_type="domestic",
            status=status,
            created_at=created_at,
        )
        db.session.add(req)
        db.session.commit()
        db.session.refresh(req)
        return req


def _add_status_log(app, shipment_request_id, new_status, created_at=None):
    """Add an ExpertConsoleLog status_change entry."""
    if created_at is None:
        created_at = datetime.utcnow()
    with app.app_context():
        log = ExpertConsoleLog(
            shipment_request_id=shipment_request_id,
            expert_user_id=None,
            action="status_change",
            old_status=None,
            new_status=new_status,
            created_at=created_at,
        )
        db.session.add(log)
        db.session.commit()


def test_workflow_steps_simple_4_definitions():
    """4-step definitions have exactly 4 steps with correct names and base title."""
    assert len(WORKFLOW_STEP_DEFS_SIMPLE_4) == 4
    assert WORKFLOW_STEP_DEFS_SIMPLE_4[0]["name"] == "request_submitted"
    assert WORKFLOW_STEP_DEFS_SIMPLE_4[0]["title"] == "ارسال درخواست"
    assert WORKFLOW_STEP_DEFS_SIMPLE_4[1]["name"] == "expert_assigned"
    assert WORKFLOW_STEP_DEFS_SIMPLE_4[2]["name"] == "in_progress"
    assert WORKFLOW_STEP_DEFS_SIMPLE_4[3]["name"] == "final_decision"
    assert "پذیرش" in WORKFLOW_STEP_DEFS_SIMPLE_4[3]["title"]


def test_workflow_steps_simple_4_in_progress(app_with_tables):
    """Request with status=in_progress: steps 1-3 completed, step 4 pending."""
    app = app_with_tables
    req = _make_request(app, status="in_progress")
    with app.app_context():
        steps = _workflow_steps_simple_4(req)
    assert len(steps) == 4
    assert steps[0]["is_completed"] is True
    assert steps[0]["name"] == "request_submitted"
    assert steps[1]["is_completed"] is True
    assert steps[2]["is_completed"] is True
    assert steps[3]["is_completed"] is False
    assert steps[3]["title"] == "پذیرش / عدم پذیرش"
    assert steps[3]["completed_at"] is None


def test_workflow_steps_simple_4_won(app_with_tables):
    """Request with status=won: step 4 completed with title پذیرش مشتری."""
    app = app_with_tables
    req = _make_request(app, status="won")
    with app.app_context():
        steps = _workflow_steps_simple_4(req)
    assert len(steps) == 4
    assert steps[3]["is_completed"] is True
    assert steps[3]["title"] == "پذیرش مشتری"
    assert steps[3]["completed_at"] is not None


def test_workflow_steps_simple_4_lost(app_with_tables):
    """Request with status=lost: step 4 completed with title عدم پذیرش مشتری."""
    app = app_with_tables
    req = _make_request(app, status="lost")
    with app.app_context():
        steps = _workflow_steps_simple_4(req)
    assert len(steps) == 4
    assert steps[3]["is_completed"] is True
    assert steps[3]["title"] == "عدم پذیرش مشتری"
    assert steps[3]["completed_at"] is not None


def test_workflow_steps_simple_4_closed_without_decision(app_with_tables):
    """Request with status=closed and no won/lost in logs: step 4 pending + meta.warning."""
    app = app_with_tables
    req = _make_request(app, status="closed")
    with app.app_context():
        steps = _workflow_steps_simple_4(req)
    assert len(steps) == 4
    assert steps[3]["is_completed"] is False
    assert steps[3]["title"] == "پذیرش / عدم پذیرش"
    assert "meta" in steps[3]
    assert steps[3]["meta"].get("warning") == "closed_without_decision"


def test_workflow_steps_simple_4_closed_with_prior_won(app_with_tables):
    """Request with status=closed but a prior status_change to won: step 4 completed as پذیرش مشتری."""
    app = app_with_tables
    req = _make_request(app, status="closed")
    _add_status_log(app, req.id, "won")
    with app.app_context():
        steps = _workflow_steps_simple_4(req)
    assert len(steps) == 4
    assert steps[3]["is_completed"] is True
    assert steps[3]["title"] == "پذیرش مشتری"
    assert steps[3]["completed_at"] is not None


def test_workflow_steps_simple_4_closed_with_prior_lost(app_with_tables):
    """Request with status=closed but a prior status_change to lost: step 4 completed as عدم پذیرش مشتری."""
    app = app_with_tables
    req = _make_request(app, status="closed")
    _add_status_log(app, req.id, "lost")
    with app.app_context():
        steps = _workflow_steps_simple_4(req)
    assert len(steps) == 4
    assert steps[3]["is_completed"] is True
    assert steps[3]["title"] == "عدم پذیرش مشتری"


def test_get_final_decision_from_logs_returns_none_when_empty(app_with_tables):
    """_get_final_decision_from_logs returns None when no won/lost log exists."""
    app = app_with_tables
    req = _make_request(app, status="closed")
    with app.app_context():
        result = _get_final_decision_from_logs(req.id)
    assert result is None


def test_get_final_decision_from_logs_returns_most_recent(app_with_tables):
    """_get_final_decision_from_logs returns the most recent won/lost decision."""
    app = app_with_tables
    req = _make_request(app, status="closed")
    base = datetime.utcnow()
    _add_status_log(app, req.id, "lost", created_at=base)
    _add_status_log(app, req.id, "won", created_at=base + timedelta(seconds=10))
    with app.app_context():
        result = _get_final_decision_from_logs(req.id)
    assert result is not None
    assert result["decision"] == "won"
    assert "completed_at" in result


def test_public_tracking_response_includes_workflow_steps_simple(app_with_tables):
    """GET /api/public/track/<id> includes workflow_steps_simple with 4 steps."""
    app = app_with_tables
    req = _make_request(app, status="in_progress")
    with app.app_context():
        rid = req.id
    client = app.test_client()
    r = client.get(f"/api/public/track/{rid}")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert "workflow_steps" in data
    assert "workflow_steps_simple" in data
    simple = data["workflow_steps_simple"]
    assert len(simple) == 4
    assert simple[0]["name"] == "request_submitted"
    assert simple[3]["name"] == "final_decision"
