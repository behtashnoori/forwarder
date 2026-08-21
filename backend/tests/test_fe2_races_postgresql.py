"""FE-2's approved fourteen races on explicit disposable PostgreSQL 18.

The application runs at PostgreSQL's READ COMMITTED default. Shipment and line
row locks serialize economic mutations, the existing transaction advisory lock
serializes idempotency identities, and exact FX/evidence facts are copied into
immutable observation-owned rows in the same transaction as their observation.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
from threading import Barrier
import uuid

import pytest
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.economics_models import EconomicEvidenceAssociation, EconomicLine, EconomicObservation
from backend.models import CaseDocumentFile, ExpertQuote, ExpertUser, ServiceType, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalShipment
from backend.services import economics_service as economics
from backend.services.operational_service import OperationalError


PERMISSIONS = ["economics.revenue.view", "economics.cost.view", "economics.margin.view",
    "economics.estimate.create", "economics.commitment.create", "economics.actual.create",
    "economics.observation.correct", "economics.fx.approve"]


def _url():
    value = os.environ.get("FE2_POSTGRES_URL", "")
    if not value:
        pytest.skip("explicit disposable FE-2 PostgreSQL URL not provided")
    parsed = make_url(value)
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert "forwarder_fe2_gate_" in (parsed.database or "")
    return value


@pytest.fixture()
def pg_app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": _url(), "SECRET_KEY": "fe2-race"}, skip_startup=True)
    token = uuid.uuid4().hex[:10]
    with app.app_context():
        org = OperationalOrganization(name=f"FE2 race {token}")
        other = OperationalOrganization(name=f"FE2 other {token}")
        user = ExpertUser(username=f"fe2-{token}", password_hash="unused", full_name="FE2", role="manager", is_active=True)
        outsider = ExpertUser(username=f"fe2-other-{token}", password_hash="unused", full_name="Other", role="manager", is_active=True)
        db.session.add_all([org, other, user, outsider]); db.session.flush()
        db.session.add_all([OperationalMembership(organization_id=org.id, user_id=user.id, permissions=PERMISSIONS),
            OperationalMembership(organization_id=other.id, user_id=outsider.id, permissions=PERMISSIONS)])
        service = ServiceType(immutable_code=f"FE2-{token}", fa_name="آزمون", en_name="FE2 race", is_active=True)
        req = ShipmentRequest(shipping_type="domestic", contact_phone="09120000000", status="quoted",
                              ownership_scope="TENANT", operational_organization_id=org.id)
        other_req = ShipmentRequest(shipping_type="domestic", contact_phone="09121111111", status="quoted",
                                    ownership_scope="TENANT", operational_organization_id=other.id)
        db.session.add_all([service, req, other_req]); db.session.flush()
        quote = ExpertQuote(shipment_request_id=req.id, amount=100, currency="USD", created_by_expert_id=user.id,
            customer_response="accepted", responded_at=datetime.now(timezone.utc))
        other_quote = ExpertQuote(shipment_request_id=other_req.id, amount=50, currency="USD", created_by_expert_id=outsider.id,
            customer_response="accepted", responded_at=datetime.now(timezone.utc))
        db.session.add_all([quote, other_quote]); db.session.flush()
        shipment = OperationalShipment(organization_id=org.id, shipment_request_id=req.id, accepted_quote_id=quote.id,
            lifecycle_status="planned", created_by_user_id=user.id)
        other_shipment = OperationalShipment(organization_id=other.id, shipment_request_id=other_req.id,
            accepted_quote_id=other_quote.id, lifecycle_status="planned", created_by_user_id=outsider.id)
        evidence = CaseDocumentFile(shipment_request_id=req.id, is_miscellaneous=True, custom_title="FE2 evidence",
            original_filename="evidence.pdf", safe_download_filename="evidence.pdf", storage_key=f"fe2/{token}",
            canonical_extension="pdf", detected_mime_type="application/pdf", file_size_bytes=10,
            sha256_hash="a" * 64, version_number=1, status="active", uploaded_by=user.id)
        db.session.add_all([shipment, other_shipment, evidence]); db.session.commit()
        app.config["race"] = {"user": {"id": user.id}, "outsider": {"id": outsider.id},
            "shipment": shipment.public_id, "other_shipment": other_shipment.public_id,
            "service": service.public_id, "evidence": evidence.public_id}
    yield app
    with app.app_context(): db.session.remove()


def _command(app, side="COST", stage="ESTIMATE", amount="10", key=None, currency="USD"):
    return {"side": side, "stage": stage, "service_public_id": app.config["race"]["service"],
        "money": {"amount": amount, "currency": currency}, "effective_at": datetime.now(timezone.utc).isoformat(),
        "authority": "FE2 race authority", "source_type": "RACE", "reason": "race", "idempotency_key": key or str(uuid.uuid4())}


def _append(app, line, stage, amount="10", key=None, **extra):
    return economics.append_observation(app.config["race"]["shipment"], line,
        {**_command(app, stage=stage, amount=amount, key=key), **extra}, app.config["race"]["user"])


def _correct(app, observation, key=None, amount="11", **extra):
    return economics.correct(app.config["race"]["shipment"], observation,
        {"correction_type": "SUPERSESSION", "expected_version": 1, "money": {"amount": amount, "currency": "USD"},
         "effective_at": datetime.now(timezone.utc).isoformat(), "authority": "FE2 correction", "reason": "race correction",
         "source_type": "CORRECTION", "idempotency_key": key or str(uuid.uuid4()), **extra}, app.config["race"]["user"])


def _pair(app, left, right):
    barrier = Barrier(2)
    def run(fn):
        with app.app_context():
            barrier.wait()
            try: return ("ok", fn())
            except OperationalError as exc: db.session.rollback(); return (exc.code, None)
            finally: db.session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        return [f.result(timeout=20) for f in (pool.submit(run, left), pool.submit(run, right))]


def _seed(app, stage="ESTIMATE", side="COST", amount="10"):
    with app.app_context():
        line = economics.create_line(app.config["race"]["shipment"], _command(app, side, stage, amount), app.config["race"]["user"])["line"]
        return line["public_id"], line["observations"][0]["public_id"]


def test_race_01_duplicate_estimate_creation(pg_app):
    payload = _command(pg_app, key="race01")
    results = _pair(pg_app, lambda: economics.create_line(pg_app.config["race"]["shipment"], payload, pg_app.config["race"]["user"]),
        lambda: economics.create_line(pg_app.config["race"]["shipment"], payload, pg_app.config["race"]["user"]))
    assert [x[0] for x in results] == ["ok", "ok"]
    assert results[0][1]["line"]["public_id"] == results[1][1]["line"]["public_id"]


def test_race_02_estimate_correction_vs_new_estimate(pg_app):
    line, observation = _seed(pg_app)
    results = _pair(pg_app, lambda: _correct(pg_app, observation), lambda: _append(pg_app, line, "ESTIMATE"))
    assert sorted(x[0] for x in results) == ["CORRECTION_REQUIRED", "ok"]


def test_race_03_competing_commitment_writes(pg_app):
    line, _ = _seed(pg_app)
    results = _pair(pg_app, lambda: _append(pg_app, line, "COMMITMENT", "20"), lambda: _append(pg_app, line, "COMMITMENT", "21"))
    assert sorted(x[0] for x in results) == ["CORRECTION_REQUIRED", "ok"]


def test_race_04_commitment_correction_vs_actual_creation(pg_app):
    line, _ = _seed(pg_app)
    with pg_app.app_context(): commitment = _append(pg_app, line, "COMMITMENT")["observation"]["public_id"]
    assert [x[0] for x in _pair(pg_app, lambda: _correct(pg_app, commitment), lambda: _append(pg_app, line, "ACTUAL"))].count("ok") == 2


def test_race_05_actual_creation_vs_actual_correction(pg_app):
    line, actual = _seed(pg_app, "ACTUAL")
    assert [x[0] for x in _pair(pg_app, lambda: _append(pg_app, line, "ACTUAL"), lambda: _correct(pg_app, actual))].count("ok") == 2


def test_race_06_simultaneous_actual_additions(pg_app):
    line, _ = _seed(pg_app)
    assert [x[0] for x in _pair(pg_app, lambda: _append(pg_app, line, "ACTUAL", "7"), lambda: _append(pg_app, line, "ACTUAL", "8"))].count("ok") == 2
    with pg_app.app_context():
        row = EconomicLine.query.filter_by(public_id=line).one()
        assert sorted(str(x.amount) for x in row.observations if x.stage == "ACTUAL") == ["7.000000", "8.000000"]


def test_race_07_economic_line_stale_version_write(pg_app):
    line, _ = _seed(pg_app)
    with pg_app.app_context(), pytest.raises(OperationalError) as exc:
        _append(pg_app, line, "ACTUAL", expected_line_version=0)
    assert exc.value.code == "ECONOMIC_LINE_VERSION_CONFLICT"


def test_race_08_concurrent_fx_creation_and_immutable_observation_binding(pg_app):
    now = datetime.now(timezone.utc).isoformat()
    def fx(rate): return economics.create_fx({"from_currency":"EUR", "to_currency":"USD", "rate":rate,
        "rate_type":"MANUAL_APPROVED", "source":f"source-{rate}", "authority":"treasury", "effective_at":now}, pg_app.config["race"]["user"])
    rates = _pair(pg_app, lambda: fx("2"), lambda: fx("3")); assert [x[0] for x in rates].count("ok") == 2
    chosen = rates[0][1]["public_id"]
    with pg_app.app_context():
        payload = _command(pg_app, currency="EUR"); payload["fx_rate_public_id"] = chosen
        created = economics.create_line(pg_app.config["race"]["shipment"], payload, pg_app.config["race"]["user"])["line"]["observations"][0]
        assert created["fx_binding"]["fx_rate_public_id"] == chosen and created["fx_binding"]["rate"] == "2.000000000000"


def test_race_09_fx_binding_vs_observation_creation(pg_app):
    with pg_app.app_context():
        rate = economics.create_fx({"from_currency":"EUR", "to_currency":"USD", "rate":"2", "rate_type":"MANUAL_APPROVED",
            "source":"base", "authority":"treasury", "effective_at":datetime.now(timezone.utc).isoformat()}, pg_app.config["race"]["user"])
    line, _ = _seed(pg_app)
    payload = {"fx_rate_public_id": rate["public_id"], "money":{"amount":"9", "currency":"EUR"}}
    results = _pair(pg_app, lambda: _append(pg_app, line, "ACTUAL", **payload),
        lambda: economics.create_fx({"from_currency":"EUR", "to_currency":"USD", "rate":"4", "rate_type":"MANUAL_APPROVED",
            "source":"new", "authority":"treasury", "effective_at":datetime.now(timezone.utc).isoformat()}, pg_app.config["race"]["user"]))
    assert [x[0] for x in results].count("ok") == 2 and results[0][1]["observation"]["fx_binding"]["fx_rate_public_id"] == rate["public_id"]


def test_race_10_evidence_bearing_correction_vs_competing_mutation(pg_app):
    _, observation = _seed(pg_app)
    evidence = [{"artifact_public_id": pg_app.config["race"]["evidence"], "artifact_version": 1, "role": "SUPPORTING"}]
    results = _pair(pg_app, lambda: _correct(pg_app, observation, evidence=evidence), lambda: _correct(pg_app, observation, amount="12"))
    assert sorted(x[0] for x in results) == ["ECONOMIC_VERSION_CONFLICT", "ok"]
    with pg_app.app_context():
        associations = EconomicEvidenceAssociation.query.all()
        assert len(associations) in {0, 1}
        if associations: assert associations[0].artifact_public_id == pg_app.config["race"]["evidence"] and associations[0].artifact_version == 1


def test_race_11_projection_read_vs_concurrent_economic_mutation(pg_app):
    line, _ = _seed(pg_app, side="REVENUE", amount="20")
    results = _pair(pg_app, lambda: economics.projection(pg_app.config["race"]["shipment"], pg_app.config["race"]["user"]),
        lambda: _append(pg_app, line, "ACTUAL", "5"))
    assert [x[0] for x in results].count("ok") == 2
    projection = results[0][1]["stages"]
    assert all(not (stage["completeness"] == "COMPLETE" and stage["margin"] is None) for stage in projection.values())


def test_race_12_same_idempotency_key_same_payload(pg_app):
    line, _ = _seed(pg_app); payload = _command(pg_app, stage="ACTUAL", key="race12")
    results = _pair(pg_app, lambda: economics.append_observation(pg_app.config["race"]["shipment"], line, payload, pg_app.config["race"]["user"]),
        lambda: economics.append_observation(pg_app.config["race"]["shipment"], line, payload, pg_app.config["race"]["user"]))
    assert [x[0] for x in results] == ["ok", "ok"] and results[0][1]["observation"]["public_id"] == results[1][1]["observation"]["public_id"]


def test_race_13_same_idempotency_key_changed_payload(pg_app):
    line, _ = _seed(pg_app)
    results = _pair(pg_app, lambda: _append(pg_app, line, "ACTUAL", "7", "race13"), lambda: _append(pg_app, line, "ACTUAL", "8", "race13"))
    assert sorted(x[0] for x in results) == ["IDEMPOTENCY_CONFLICT", "ok"]


def test_race_14_cross_tenant_concurrent_access(pg_app):
    line, _ = _seed(pg_app)
    results = _pair(pg_app, lambda: _append(pg_app, line, "ACTUAL"),
        lambda: economics.list_lines(pg_app.config["race"]["shipment"], pg_app.config["race"]["outsider"]))
    assert sorted(x[0] for x in results) == ["ECONOMIC_SUBJECT_NOT_FOUND", "ok"]
