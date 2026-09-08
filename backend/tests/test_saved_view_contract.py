from copy import deepcopy

import pytest

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.saved_view_models import SavedViewRevision
from backend import saved_view_service as service
from backend.services.operational_service import OperationalError


def definition():
    return {"schema_version":"saved-view-definition-v1","semantic_version":"analytics-semantic-v1","surface":"OPERATIONAL_SHIPMENTS","query_definition":{"metric_keys":["SHIPMENT_COUNT"],"dimension_keys":[],"filters":[{"dimension":"SHIPMENT_STATUS","value":"in_progress"}],"time_dimension":"created","limit":20},"presentation":{"columns":["CUSTOMER","ROUTE","PLANNED_TIME"],"sort":{"field":"PLANNED_DEPARTURE","direction":"ASC"},"display_type":"LIST","limit":20}}


@pytest.fixture()
def context():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"saved-view-test"},skip_startup=True)
    with app.app_context():
        db.create_all(); a=ExpertUser(username="sv-a",password_hash="x",full_name="A"); b=ExpertUser(username="sv-b",password_hash="x",full_name="B"); c=ExpertUser(username="sv-c",password_hash="x",full_name="C"); oa=OperationalOrganization(name="A"); ob=OperationalOrganization(name="B")
        db.session.add_all([a,b,c,oa,ob]);db.session.flush();db.session.add_all([OperationalMembership(organization_id=oa.id,user_id=a.id,permissions=["operational_shipment.read","personal_dashboard.read","personal_dashboard.manage"]),OperationalMembership(organization_id=oa.id,user_id=b.id,permissions=["operational_shipment.read","personal_dashboard.read","personal_dashboard.manage"]),OperationalMembership(organization_id=ob.id,user_id=c.id,permissions=["operational_shipment.read","personal_dashboard.read","personal_dashboard.manage"])]);db.session.commit()
        yield {"a":{"id":a.id},"b":{"id":b.id},"c":{"id":c.id}}
        db.session.remove();db.drop_all()


def test_create_list_and_private_boundaries(context):
    created=service.create({"name":"فعال‌ها","definition":definition()},context["a"])
    assert created["version"]==1 and created["visibility"]=="PRIVATE"
    assert service.list_(context["a"])[0]["public_id"]==created["public_id"]
    assert db.session.query(SavedViewRevision).count()==1
    for user in (context["b"],context["c"]):
        with pytest.raises(OperationalError) as denied: service.get(created["public_id"],user)
        assert denied.value.code=="SAVED_VIEW_NOT_FOUND"


def test_revision_noop_conflict_and_lifecycle(context):
    user=context["a"];created=service.create({"name":"فعال‌ها","definition":definition()},user)
    assert service.update(created["public_id"],{"expected_version":1,"name":"فعال‌ها"},user)["version"]==1
    changed=deepcopy(definition());changed["presentation"]["sort"]["direction"]="DESC"
    assert service.update(created["public_id"],{"expected_version":1,"definition":changed},user)["version"]==2
    assert db.session.query(SavedViewRevision).count()==2
    with pytest.raises(OperationalError) as stale: service.update(created["public_id"],{"expected_version":1,"name":"قدیمی"},user)
    assert stale.value.code=="SAVED_VIEW_VERSION_CONFLICT" and db.session.query(SavedViewRevision).count()==2
    assert service.lifecycle(created["public_id"],{"expected_version":2},user,"ARCHIVED")["status"]=="ARCHIVED"
    assert service.list_(user)==[] and db.session.query(SavedViewRevision).count()==2
    assert service.lifecycle(created["public_id"],{"expected_version":2},user,"ACTIVE")["status"]=="ACTIVE"


@pytest.mark.parametrize("mutate",[
 lambda d:d.update(schema_version="wrong"),
 lambda d:d["query_definition"].update(metric_keys=["LEAD_TIME"]),
 lambda d:d["presentation"].update(columns=["internal_id"]),
 lambda d:d["presentation"].update(display_type="CHART"),
])
def test_invalid_definition_has_no_revision(context,mutate):
    bad=definition();mutate(bad)
    with pytest.raises(ValueError):service.create({"name":"bad","definition":bad},context["a"])
    assert db.session.query(SavedViewRevision).count()==0
