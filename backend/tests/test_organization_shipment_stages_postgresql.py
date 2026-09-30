"""Owned PostgreSQL 18 proof for Organization Shipment stages and closure."""
from datetime import timedelta
from uuid import uuid4
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.cargo_models import ShipmentCargoItem
from backend.closure_models import BLOCKER_CRITERIA, WARNING_CRITERIA
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import CargoType, ExpertUser, UnitOfMeasure
from backend.operational_models import OperationalMembership, OperationalShipment, utcnow
from backend.services import closure_service, delivery_service, shipment_stage_service, unified_shipment_history
from backend.services.operational_service import OperationalError
from backend.shipment_stage_models import CANONICAL_STAGE_CODES, ShipmentOperationalStageEvent
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime


URL = os.environ.get("ORG_SHIPMENT_STAGES_POSTGRES_URL", "")
HEAD = "20261015_org_shipment_stages"
pytestmark = pytest.mark.skipif(not URL, reason="requires explicit owned ORG_SHIPMENT_STAGES_POSTGRES_URL")


def test_postgresql18_migration_guards_and_exact_closure_contract():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_integrated_cert_org_stages_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    config = alembic_config(URL)
    command.upgrade(config, HEAD)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL, "SECRET_KEY": "org-stage-pg"}, skip_startup=True)

    with app.app_context():
        ctx = _seed_runtime(app)
        owner_membership = OperationalMembership.query.filter_by(user_id=ctx["owner"]).one()
        owner_membership.permissions = [*owner_membership.permissions, "operational_shipment.create"]
        shipment = OperationalShipment.query.filter_by(public_id=ctx["shipment"]).one()
        admin = ExpertUser(
            username="org-stage-pg-admin", password_hash="unused", full_name="Stage Admin",
            role="manager", authority="ORGANIZATION_ADMIN", is_active=True,
        )
        db.session.add(admin); db.session.flush()
        db.session.add(OperationalMembership(
            organization_id=shipment.organization_id, user_id=admin.id,
            permissions=["operational_shipment.read"],
        ))
        cargo_type = CargoType(
            immutable_code="ORG_STAGE_PG_CARGO", fa_name="کالای آزمون", en_name="Stage Cargo", is_active=True,
        )
        uom = UnitOfMeasure(
            immutable_code="ORG_STAGE_PG_UNIT", fa_name="عدد", en_name="Unit", symbol="u",
            measurement_dimension="COUNT", is_active=True,
        )
        db.session.add_all([cargo_type, uom]); db.session.flush()
        cargo = ShipmentCargoItem(
            operational_shipment_id=shipment.id, line_number=1,
            cargo_owner_customer_id=ctx["carrier"], cargo_type_id=cargo_type.id, uom_id=uom.id,
            quantity=100, planned_quantity=100, actual_quantity=None, display_name_snapshot="Stage Cargo",
            cargo_type_code_snapshot=cargo_type.immutable_code, cargo_type_fa_snapshot=cargo_type.fa_name,
            cargo_type_en_snapshot=cargo_type.en_name, uom_code_snapshot=uom.immutable_code,
            uom_symbol_snapshot=uom.symbol, created_by=ctx["owner"], updated_by=ctx["owner"],
        )
        db.session.add(cargo); db.session.commit()
        ctx.update(admin=admin.id, cargo=cargo.public_id, uom=uom.public_id, shipment_id=shipment.id)

        admin_user = {"id": ctx["admin"], "role": "manager"}
        owner_user = {"id": ctx["owner"], "role": "expert"}
        version, created = shipment_stage_service.save_configuration(
            admin_user,
            {
                "expected_version": 0,
                "effective_from": (utcnow() - timedelta(days=1)).isoformat(),
                "stages": [
                    {
                        "code": code,
                        "display_name_fa": shipment_stage_service.CANONICAL_NAMES_FA[code],
                        "sequence": index,
                        "active": True,
                        "required_for_completion": True,
                    }
                    for index, code in enumerate(CANONICAL_STAGE_CODES, 1)
                ],
            },
            "pg-stage-policy",
        )
        db.session.commit()
        assert created and version.version == 1
        assert shipment_stage_service.read(ctx["shipment"], owner_user)["project_required"] is False
        assert shipment.project_id is None

        criteria = [
            {"scope": "GENERAL", "code": code, "mandatory": True} for code in BLOCKER_CRITERIA
        ] + [
            {"scope": "GENERAL", "code": code, "mandatory": False} for code in WARNING_CRITERIA
        ]
        closure_service.save_policy(
            admin_user,
            {"expected_version": 0, "effective_from": (utcnow() - timedelta(days=1)).isoformat(), "criteria": criteria},
            "pg-closure-policy",
        )
        db.session.commit()

        delivery, created = delivery_service.create(
            ctx["shipment"], owner_user,
            {
                "cargo_public_id": ctx["cargo"], "quantity": "95", "uom_public_id": ctx["uom"],
                "destination_text": "مقصد آزمون", "occurred_at": (utcnow() - timedelta(hours=2)).isoformat(),
                "expected_version": 0, "is_final": True,
            },
            "pg-final-delivery",
        )
        db.session.commit()
        assert created and delivery.is_final
        with pytest.raises(OperationalError) as duplicate:
            delivery_service.create(
                ctx["shipment"], owner_user,
                {
                    "cargo_public_id": ctx["cargo"], "quantity": "1", "uom_public_id": ctx["uom"],
                    "destination_text": "مقصد دوم", "occurred_at": (utcnow() - timedelta(hours=1)).isoformat(),
                    "expected_version": 0, "is_final": True,
                },
                "pg-duplicate-final",
            )
        assert duplicate.value.code == "FINAL_DELIVERY_EXISTS"
        db.session.rollback()

        stages = shipment_stage_service.read(ctx["shipment"], owner_user)
        base = shipment_stage_service.times.aware(shipment.created_at)
        for index, stage in enumerate(stages["stages"]):
            for offset, event_type in ((0, "STARTED"), (1, "COMPLETED")):
                shipment_stage_service.record_event(
                    ctx["shipment"], stage["public_id"], owner_user,
                    {
                        "event_type": event_type,
                        "occurred_at": (base + timedelta(microseconds=index * 2 + offset + 1)).isoformat(),
                        "expected_policy_version_public_id": version.public_id,
                    },
                    f"pg-stage-{index}-{event_type.lower()}",
                )
                db.session.commit()

        event_id = ShipmentOperationalStageEvent.query.order_by(ShipmentOperationalStageEvent.id).first().id
        with pytest.raises(sa.exc.DBAPIError, match="immutable"):
            db.session.execute(sa.text(
                "UPDATE shipment_operational_stage_event SET occurred_at=occurred_at + interval '1 second' WHERE id=:id"
            ), {"id": event_id})
            db.session.commit()
        db.session.rollback()

        shipment.lifecycle_status = "completed"
        db.session.commit()
        assessment = closure_service.assess(shipment)
        items = {item["code"]: item for item in assessment["items"]}
        assert all(items[code]["state"] == "PASS" for code in BLOCKER_CRITERIA)
        assert items["ACTUAL_CARGO_UNKNOWN"]["state"] == "FAIL"
        assert items["DELIVERED_DIFFERS_FROM_PLANNED"]["state"] == "FAIL"
        assert assessment["normal_ready"] is True
        decision, created = closure_service.close(
            ctx["shipment"], owner_user,
            {
                "kind": "NORMAL", "reason": None, "expected_shipment_version": shipment.version,
                "policy_version_public_id": assessment["policy"]["public_id"],
                "assessment_fingerprint": assessment["fingerprint"],
            },
            "pg-normal-close",
        )
        db.session.commit()
        assert created and decision.kind == "NORMAL" and shipment.lifecycle_status == "closed"
        history = unified_shipment_history.history(shipment, per_page=100, user=owner_user)
        assert len([item for item in history["items"] if item["category"] == "OPERATIONAL_STAGE"]) == 10
        assert any(item["category"] == "CLOSURE" for item in history["items"])
        with pytest.raises(OperationalError):
            shipment_stage_service.read(ctx["shipment"], {"id": ctx["outsider"], "role": "expert"})

    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        assert connection.execute(sa.text("SELECT count(*) FROM organization_shipment_stage_definition")).scalar_one() == 5
        assert connection.execute(sa.text("SELECT count(*) FROM shipment_operational_stage_event")).scalar_one() == 10
        assert connection.execute(sa.text("SELECT count(*) FROM shipment_closure_decision")).scalar_one() == 1
    engine.dispose()

