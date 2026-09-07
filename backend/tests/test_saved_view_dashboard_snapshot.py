"""Acceptance freeze for independent Saved View Dashboard TABLE snapshots."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from backend import dashboard_service, saved_view_service
from backend.analytics import service as analytics
from backend.extensions import db
from backend.operational_models import CanonicalLocation, OperationalShipment, RouteLeg, RoutePlan
from backend.saved_view_models import SavedView, SavedViewRevision
from backend.services import project_access_authorization
from backend.services.operational_service import OperationalError
from backend.tests.test_saved_view_contract import context
from backend.tests.test_saved_view_rowset_alignment import _v2
from backend.tests.test_project_access_foundation import access_app


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


def test_snapshot_widget_uses_current_project_authorization_after_revocation(access_app):
    """A copied ROWSET stays immutable while its Shipment authorization is live."""
    _app, x = access_app
    expert, admin = x["users"]["ea"], x["users"]["aa"]
    project = x["a1"]
    project_only = x["shipment"]
    direct = OperationalShipment(
        organization_id=project.organization_id,
        project_id=project.id,
        source_type="direct",
        customer_id=project.primary_customer_id,
        lifecycle_status="planned",
        created_by_user_id=expert.id,
        primary_responsible_expert_id=expert.id,
    )
    origin = CanonicalLocation(
        source_type="province", source_id=9001, location_type="province", display_name="Origin"
    )
    destination = CanonicalLocation(
        source_type="province", source_id=9002, location_type="province", display_name="Destination"
    )
    db.session.add_all([direct, origin, destination])
    db.session.flush()
    departure = datetime(2041, 1, 1, 8, tzinfo=timezone.utc)
    for shipment, offset in ((project_only, 0), (direct, 1)):
        plan = RoutePlan(
            operational_shipment_id=shipment.id, revision=1, is_active=True, created_by_user_id=admin.id
        )
        db.session.add(plan)
        db.session.flush()
        db.session.add(RouteLeg(
            route_plan_id=plan.id, sequence_number=1,
            origin_location_id=origin.id, destination_location_id=destination.id,
            origin_snapshot={"display_name": "Origin"},
            destination_snapshot={"display_name": "Destination"},
            transport_mode="road", planned_departure=departure + timedelta(hours=offset),
            planned_arrival=departure + timedelta(hours=offset + 1),
        ))
    db.session.commit()

    grant = project_access_authorization.add_assignment(
        project.public_id, {"username": expert.username}, {"id": admin.id}
    )
    actor = {"id": expert.id}
    source = saved_view_service.create(
        {"name": "Live project scope", "definition": _v2("planned")}, actor
    )
    target = _dashboard(actor)
    snapshot = _snapshot(source, target, actor)
    widget = next(
        item for item in snapshot["definition"]["widgets"] if item["widget_id"] == snapshot["created_widget_id"]
    )
    query_before, provenance_before = deepcopy(widget["query"]), deepcopy(widget["provenance"])
    source_before = saved_view_service.get(source["public_id"], actor)
    dashboard_before = deepcopy(snapshot["definition"])

    assert [row["shipment_public_id"] for row in analytics.query(
        source_before["runtime_definition"]["query_definition"], actor
    )["rows"]] == [project_only.public_id, direct.public_id]
    assert [row["shipment_public_id"] for row in analytics.query(query_before, actor)["rows"]] == [
        project_only.public_id, direct.public_id
    ]
    assert provenance_before == {
        "source_type": "SAVED_VIEW", "source_public_id": source["public_id"],
        "source_version": 1, "source_name_snapshot": "Live project scope",
    }
    persisted_widget = json.dumps(widget, sort_keys=True).lower()
    assert "projectaccess" not in persisted_widget and "project_access" not in persisted_widget
    assert project_only.public_id not in persisted_widget and direct.public_id not in persisted_widget

    assert project_access_authorization.revoke_assignment(
        project.public_id, grant["public_id"], {"id": admin.id}
    )["revoked"] is True

    reloaded = dashboard_service.get(target["public_id"], actor)
    same_widget = next(
        item for item in reloaded["definition"]["widgets"] if item["widget_id"] == widget["widget_id"]
    )
    assert [row["shipment_public_id"] for row in analytics.query(same_widget["query"], actor)["rows"]] == [
        direct.public_id
    ]
    assert same_widget["query"] == query_before
    assert same_widget["provenance"] == provenance_before
    assert reloaded["definition"] == dashboard_before and reloaded["version"] == snapshot["version"]
    source_after = saved_view_service.get(source["public_id"], actor)
    assert source_after["definition"] == source_before["definition"]
    assert source_after["version"] == source_before["version"]
    view_id = db.session.scalar(db.select(SavedView.id).where(SavedView.public_id == source["public_id"]))
    assert db.session.query(SavedViewRevision).filter_by(saved_view_id=view_id).count() == 1
