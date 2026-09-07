"""Saved View v1 compatibility and v2 ROWSET persistence freeze."""
from copy import deepcopy

from backend import saved_view_service as service
from backend.extensions import db
from backend.saved_view_models import SavedView, SavedViewRevision
from backend.tests.test_saved_view_contract import context, definition


def _v2(status="in_progress"):
    return {"schema_version":"saved-view-definition-v2","semantic_version":"analytics-semantic-v2","surface":"OPERATIONAL_SHIPMENTS","query_definition":{"query_kind":"ROWSET","semantic_version":"analytics-semantic-v2","population":"SHIPMENTS","columns":["CUSTOMER","ROUTE","PLANNED_TIME"],"filters":[{"dimension":"SHIPMENT_STATUS","value":status}],"operational_window":{"from":"2041-01-01T00:00:00+00:00","to":"2041-01-02T00:00:00+00:00"},"sort":{"field":"PLANNED_DEPARTURE","direction":"ASC"},"limit":20},"presentation":{"display_type":"LIST"}}


def test_new_v2_rowset_and_legacy_runtime_alignment_are_immutable(context):
    fresh = service.create({"name":"جدید","definition":_v2()}, context["a"])
    assert fresh["definition"]["query_definition"]["query_kind"] == "ROWSET"
    assert fresh["semantic_version"] == "analytics-semantic-v2"
    legacy = service.create({"name":"قدیمی","definition":definition()}, context["a"])
    loaded = service.get(legacy["public_id"], context["a"])
    runtime = loaded["runtime_definition"]
    assert loaded["definition"]["schema_version"] == "saved-view-definition-v1"
    assert runtime["schema_version"] == "saved-view-definition-v2"
    assert runtime["query_definition"]["query_kind"] == "ROWSET"
    assert "SHIPMENT_COUNT" not in runtime["query_definition"]
    assert runtime["query_definition"]["sort"] == legacy["definition"]["presentation"]["sort"]
    assert db.session.query(SavedViewRevision).count() == 2


def test_v1_noop_alignment_then_meaningful_update_creates_one_v2_revision(context):
    legacy = service.create({"name":"قدیمی","definition":definition()}, context["a"])
    aligned = service.get(legacy["public_id"], context["a"])["runtime_definition"]
    assert service.update(legacy["public_id"], {"expected_version":1,"definition":aligned}, context["a"])["version"] == 1
    changed = deepcopy(aligned); changed["query_definition"]["limit"] = 21
    updated = service.update(legacy["public_id"], {"expected_version":1,"definition":changed}, context["a"])
    assert updated["version"] == 2 and updated["definition"]["schema_version"] == "saved-view-definition-v2"
    view_id = db.session.scalar(db.select(SavedView.id).where(SavedView.public_id == legacy["public_id"]))
    revisions = db.session.query(SavedViewRevision).filter_by(saved_view_id=view_id).order_by(SavedViewRevision.revision_number).all()
    assert [row.definition_json["schema_version"] for row in revisions] == ["saved-view-definition-v1", "saved-view-definition-v2"]
