"""FE-2 domain, security, history, FX and abstention contracts."""
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import pytest

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import ExpertQuote, ExpertUser, ServiceType, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment
from backend.economics_models import EconomicAudit, EconomicObservation
from backend.services import economics_service as economics
from backend.services.operational_service import OperationalError

PERMISSIONS=["economics.revenue.view","economics.cost.view","economics.margin.view","economics.estimate.create","economics.commitment.create","economics.actual.create","economics.observation.correct","economics.fx.approve"]

@pytest.fixture()
def app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:","SECRET_KEY":"economics-test"})
    with app.app_context():
        db.create_all();org=OperationalOrganization(name="Economics Org");other=OperationalOrganization(name="Other Org")
        user=ExpertUser(username="econ",password_hash="x",full_name="Economic Operator",role="manager",is_active=True);outsider=ExpertUser(username="econ-other",password_hash="x",full_name="Other",role="manager",is_active=True)
        db.session.add_all([org,other,user,outsider]);db.session.flush();db.session.add_all([OperationalMembership(organization_id=org.id,user_id=user.id,permissions=PERMISSIONS),OperationalMembership(organization_id=other.id,user_id=outsider.id,permissions=PERMISSIONS)])
        service=ServiceType(immutable_code="FREIGHT",fa_name="Freight",en_name="Freight",is_active=True)
        req=ShipmentRequest(shipping_type="domestic",contact_phone="09120000000",status="quoted");db.session.add_all([service,req]);db.session.flush()
        quote=ExpertQuote(shipment_request_id=req.id,amount=120,currency="USD",created_by_expert_id=user.id,customer_response="accepted",responded_at=datetime.now(timezone.utc));db.session.add(quote);db.session.flush()
        shipment=OperationalShipment(organization_id=org.id,shipment_request_id=req.id,accepted_quote_id=quote.id,lifecycle_status="planned",created_by_user_id=user.id);other_req=ShipmentRequest(shipping_type="domestic",contact_phone="09121111111");db.session.add_all([shipment,other_req]);db.session.flush()
        other_quote=ExpertQuote(shipment_request_id=other_req.id,amount=50,currency="USD",created_by_expert_id=outsider.id,customer_response="accepted",responded_at=datetime.now(timezone.utc));db.session.add(other_quote);db.session.flush();other_shipment=OperationalShipment(organization_id=other.id,shipment_request_id=other_req.id,accepted_quote_id=other_quote.id,lifecycle_status="planned",created_by_user_id=outsider.id);db.session.add(other_shipment);db.session.commit()
        app.config["econ"]={"user":{"id":user.id},"outsider":{"id":outsider.id},"shipment":shipment.public_id,"other_shipment":other_shipment.public_id,"service":service.public_id}
        yield app;db.session.remove();db.drop_all()

def command(app,side,stage,amount,currency="USD",key="key"):
    return {"side":side,"stage":stage,"service_public_id":app.config["econ"]["service"],"money":{"amount":amount,"currency":currency},"effective_at":datetime.now(timezone.utc).isoformat(),"authority":"FE-2 test authority","source_type":"MANUAL_TEST","reason":"test fact","idempotency_key":key}

def test_money_exact_validation_and_serialization(app):
    assert economics.money({"amount":"12.340000","currency":"USD"})==(Decimal("12.340000"),"USD")
    with pytest.raises(OperationalError): economics.money({"amount":12.34,"currency":"USD"})
    with pytest.raises(OperationalError): economics.money({"amount":"1","currency":"XXX"})

def test_stages_history_correction_actual_accumulation_and_projection(app):
    with app.app_context():
        ctx=app.config["econ"];s,u=ctx["shipment"],ctx["user"]
        revenue=economics.create_line(s,command(app,"REVENUE","ESTIMATE","100",key="rev-est"),u)["line"]
        economics.append_observation(s,revenue["public_id"],dict(command(app,"REVENUE","COMMITMENT","120",key="rev-commit"),stage="COMMITMENT"),u)
        cost=economics.create_line(s,command(app,"COST","ESTIMATE","70",key="cost-est"),u)["line"]
        actual=economics.append_observation(s,cost["public_id"],dict(command(app,"COST","ACTUAL","60",key="cost-a1"),stage="ACTUAL"),u)["observation"]
        economics.append_observation(s,cost["public_id"],dict(command(app,"COST","ACTUAL","10",key="cost-a2"),stage="ACTUAL"),u)
        fixed=economics.correct(s,actual["public_id"],{"correction_type":"SUPERSESSION","expected_version":1,"money":{"amount":"65","currency":"USD"},"effective_at":datetime.now(timezone.utc).isoformat(),"authority":"cost controller","reason":"correct supplier amount","source_type":"CORRECTION","idempotency_key":"fix-a1"},u)
        assert fixed["observation"]["money"]["amount"]=="65.000000"
        projection=economics.projection(s,u)
        assert projection["stages"]["COMMITMENT"]["completeness"]=="INCOMPLETE"
        assert projection["stages"]["ACTUAL"]["cost"]["amount"]=="75.000000"
        assert EconomicObservation.query.count()==6 and EconomicAudit.query.count()==6

def test_idempotency_changed_replay_and_tenant_scope(app):
    with app.app_context():
        ctx=app.config["econ"];payload=command(app,"COST","ESTIMATE","9",key="same")
        first=economics.create_line(ctx["shipment"],payload,ctx["user"]);second=economics.create_line(ctx["shipment"],payload,ctx["user"])
        assert first["line"]["public_id"]==second["line"]["public_id"] and second["replayed"]
        with pytest.raises(OperationalError) as conflict:economics.create_line(ctx["shipment"],dict(payload,money={"amount":"10","currency":"USD"}),ctx["user"])
        assert conflict.value.status==409
        with pytest.raises(OperationalError) as hidden:economics.list_lines(ctx["other_shipment"],ctx["user"])
        assert hidden.value.status==404

def test_cost_and_margin_visibility_are_independently_enforced(app):
    with app.app_context():
        ctx=app.config["econ"]
        economics.create_line(ctx["shipment"],command(app,"REVENUE","ESTIMATE","100","USD","visibility-revenue"),ctx["user"])
        economics.create_line(ctx["shipment"],command(app,"COST","ESTIMATE","70","USD","visibility-cost"),ctx["user"])
        membership=OperationalMembership.query.filter_by(user_id=ctx["user"]["id"]).one()

        full=economics.projection(ctx["shipment"],ctx["user"])["stages"]["ESTIMATE"]
        assert full["margin"]["amount"]=="30.000000"

        membership.permissions=[p for p in membership.permissions if p!="economics.margin.view"]
        db.session.commit()
        margin_hidden=economics.projection(ctx["shipment"],ctx["user"])["stages"]["ESTIMATE"]
        assert margin_hidden["revenue"]["amount"]=="100.000000"
        assert margin_hidden["cost"]["amount"]=="70.000000"
        assert margin_hidden["margin"] is None
        assert margin_hidden["margin_percentage"] is None
        assert "MARGIN_VISIBILITY_RESTRICTED" in margin_hidden["missing_inputs"]

        membership.permissions=[p for p in membership.permissions if p!="economics.cost.view"]
        db.session.commit()
        cost_and_margin_hidden=economics.projection(ctx["shipment"],ctx["user"])["stages"]["ESTIMATE"]
        assert cost_and_margin_hidden["revenue"]["amount"]=="100.000000"
        assert cost_and_margin_hidden["cost"] is None
        assert cost_and_margin_hidden["margin"] is None
        assert cost_and_margin_hidden["margin_percentage"] is None
        assert {"COST_VISIBILITY_RESTRICTED","MARGIN_VISIBILITY_RESTRICTED"}.issubset(cost_and_margin_hidden["missing_inputs"])

def test_fx_is_explicit_and_missing_fx_abstains(app):
    with app.app_context():
        ctx=app.config["econ"]; economics.create_line(ctx["shipment"],command(app,"REVENUE","ESTIMATE","100","USD","fx-rev"),ctx["user"])
        cost=command(app,"COST","ESTIMATE","50","EUR","fx-cost")
        economics.create_line(ctx["shipment"],cost,ctx["user"])
        incomplete=economics.projection(ctx["shipment"],ctx["user"],"USD")["stages"]["ESTIMATE"]
        assert incomplete["margin"] is None and "FX_MISSING" in incomplete["missing_inputs"]
        rate=economics.create_fx({"from_currency":"EUR","to_currency":"USD","rate":"2","rate_type":"MANUAL_APPROVED","source":"approved worksheet","authority":"treasury delegate","effective_at":datetime.now(timezone.utc).isoformat()},ctx["user"])
        # A newer fact cannot repair or redirect an observation that lacked provenance.
        assert economics.projection(ctx["shipment"],ctx["user"],"USD")["stages"]["ESTIMATE"]["completeness"] == "INCOMPLETE"
        replacement=command(app,"COST","ACTUAL","50","EUR","fx-cost-bound"); replacement["fx_rate_public_id"]=rate["public_id"]
        line=economics.list_lines(ctx["shipment"],ctx["user"])[1]
        economics.append_observation(ctx["shipment"],line["public_id"],replacement,ctx["user"])
        revenue_actual=command(app,"REVENUE","ACTUAL","100","USD","fx-rev-actual")
        economics.append_observation(ctx["shipment"],economics.list_lines(ctx["shipment"],ctx["user"])[0]["public_id"],revenue_actual,ctx["user"])
        complete=economics.projection(ctx["shipment"],ctx["user"],"USD")["stages"]["ACTUAL"]
        assert complete["margin"]["amount"]=="0.000000" and complete["applied_fx_rate_ids"]==[rate["public_id"]]
        inferred=economics.projection(ctx["shipment"],ctx["user"])["stages"]["ACTUAL"]
        assert inferred["completeness"]=="COMPLETE"
        assert inferred["currency"]=="USD"
        assert inferred["margin"]["amount"]=="0.000000"
        assert inferred["applied_fx_rate_ids"]==[rate["public_id"]]
        before=dict(complete)
        economics.create_fx({"from_currency":"EUR","to_currency":"USD","rate":"3","rate_type":"MANUAL_APPROVED","source":"new worksheet","authority":"treasury delegate","effective_at":datetime.now(timezone.utc).isoformat()},ctx["user"])
        after=economics.projection(ctx["shipment"],ctx["user"],"USD")["stages"]["ACTUAL"]
        assert after == before

def test_quote_requires_explicit_preview_and_confirm(app):
    with app.app_context():
        ctx=app.config["econ"];preview=economics.quote_preview(ctx["shipment"],ctx["user"]);assert preview["confirmation_allowed"]
        result=economics.quote_confirm(ctx["shipment"],{"service_public_id":ctx["service"],"authority":"accepted customer capability response","reason":"authorized commercial acceptance","idempotency_key":"quote-confirm"},ctx["user"])
        assert result["line"]["observations"][0]["stage"]=="COMMITMENT"

def test_api_permissions_and_opaque_identifiers(app):
    with app.app_context():
        ctx=app.config["econ"];token=auth_manager.generate_tokens(ctx["user"]["id"])["access_token"]
    client=app.test_client();response=client.get(f"/api/v2/operational-shipments/{ctx['shipment']}/economics/projection",headers={"Authorization":f"Bearer {token}"})
    assert response.status_code==200 and response.get_json()["data"]["shipment_public_id"]==ctx["shipment"]
    assert client.get("/api/v2/operational-shipments/1/economics/projection",headers={"Authorization":f"Bearer {token}"}).status_code==404

def test_openapi_runtime_path_parity(app):
    document=(Path(__file__).resolve().parents[2]/"docs/openapi/openapi.yaml").read_text(encoding="utf-8")
    runtime={rule.rule.replace("<shipment_id>","{shipment_id}").replace("<line_id>","{line_id}").replace("<observation_id>","{observation_id}").replace("<project_id>","{project_id}") for rule in app.url_map.iter_rules() if "/economics" in rule.rule}
    assert all(f"  {path}:" in document for path in runtime)
