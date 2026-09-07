"""Acceptance freeze for independent Saved View Dashboard TABLE snapshots."""
from copy import deepcopy

import pytest

from backend import dashboard_service, saved_view_service
from backend.analytics import service as analytics
from backend.extensions import db
from backend.saved_view_models import SavedViewRevision
from backend.services.operational_service import OperationalError
from backend.tests.test_saved_view_contract import context
from backend.tests.test_saved_view_rowset_alignment import _v2


def _dashboard(user):
    return dashboard_service.clone("operations-control-tower", user, "Snapshot target")


def _snapshot(source, dashboard, user):
    return saved_view_service.dashboard_snapshot(source["public_id"], {"target_dashboard_public_id": dashboard["public_id"], "expected_dashboard_version": dashboard["version"]}, user)


def test_snapshot_copies_exact_rowset_and_is_independent(context):
    source = saved_view_service.create({"name":"عملیاتی","definition":_v2()}, context["a"])
    target = _dashboard(context["a"])
    result = _snapshot(source, target, context["a"])
    widget = next(w for w in result["definition"]["widgets"] if w["widget_id"] == result["created_widget_id"])
    runtime = saved_view_service.get(source["public_id"], context["a"])["runtime_definition"]
    assert widget["widget_type"] == "TABLE" and widget["query"] == runtime["query_definition"]
    assert widget["provenance"] == {"source_type":"SAVED_VIEW","source_public_id":source["public_id"],"source_version":1,"source_name_snapshot":"عملیاتی"}
    assert result["version"] == target["version"] + 1
    assert db.session.query(SavedViewRevision).count() == 1
    changed = deepcopy(_v2("completed")); saved_view_service.update(source["public_id"], {"expected_version":1,"definition":changed}, context["a"])
    saved_view_service.lifecycle(source["public_id"], {"expected_version":2}, context["a"], "ARCHIVED")
    reloaded = dashboard_service.get(target["public_id"], context["a"])
    same = next(w for w in reloaded["definition"]["widgets"] if w["widget_id"] == widget["widget_id"])
    assert same["query"] == runtime["query_definition"] and same["provenance"] == widget["provenance"]
    # The copied query executes directly through Analytics, with no Saved View lookup.
    assert analytics.query(same["query"], context["a"])["result_kind"] == "ROWSET"


def test_snapshot_security_concurrency_and_provenance_controls(context):
    source = saved_view_service.create({"name":"امن","definition":_v2()}, context["a"])
    own, other, foreign = _dashboard(context["a"]), _dashboard(context["b"]), _dashboard(context["c"])
    for actor, view_id, dashboard in ((context["b"], source["public_id"], own), (context["c"], source["public_id"], own), (context["a"], source["public_id"], other), (context["a"], source["public_id"], foreign)):
        with pytest.raises(OperationalError) as denied:
            saved_view_service.dashboard_snapshot(view_id, {"target_dashboard_public_id":dashboard["public_id"],"expected_dashboard_version":dashboard["version"],"source_version":999,"provenance":{"source_type":"FORGED"}}, actor)
        assert denied.value.code in {"SAVED_VIEW_NOT_FOUND", "DASHBOARD_NOT_FOUND"}
    with pytest.raises(OperationalError) as conflict:
        saved_view_service.dashboard_snapshot(source["public_id"], {"target_dashboard_public_id":own["public_id"],"expected_dashboard_version":999}, context["a"])
    assert conflict.value.code == "DASHBOARD_VERSION_CONFLICT"
    snapshot = _snapshot(source, own, context["a"])
    forged = deepcopy(snapshot["definition"]); forged["widgets"][-1]["provenance"]["source_version"] = 99
    with pytest.raises(OperationalError) as immutable:
        dashboard_service.update(own["public_id"], {"expected_version":snapshot["version"],"definition":forged}, context["a"])
    assert immutable.value.code == "DASHBOARD_WIDGET_PROVENANCE_IMMUTABLE"
