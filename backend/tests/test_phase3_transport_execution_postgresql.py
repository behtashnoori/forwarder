"""Owned PostgreSQL 18 qualification for P3-04 migration and races."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import (
    Customer,
    CustomerRoleAssignment,
    ExpertUser,
    TransportEquipmentType,
    TransportMeansType,
)
from backend.operational_models import (
    CanonicalLocation,
    ExecutionUnit,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    RouteLeg,
    RoutePlan,
)
from backend.organization_reference_catalog_models import (
    OrganizationTransportEquipmentTypeActivation,
    OrganizationTransportMeansTypeActivation,
)
from backend.services import operational_service as operations
from backend.services import transport_execution_service as executions


POSTGRES_URL = os.environ.get("P3_TRANSPORT_EXECUTION_POSTGRES_URL", "")
PREVIOUS = "20261002_phase3_branched_route"
HEAD = "20261003_phase3_transport_execution"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires explicit P3_TRANSPORT_EXECUTION_POSTGRES_URL",
)


def _assert_owned_postgres_18():
    parsed = make_url(POSTGRES_URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith(
        "forwarder_integrated_cert_p3_04_transport_execution_"
    )
    engine = sa.create_engine(POSTGRES_URL)
    try:
        with engine.connect() as connection:
            assert int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) >= 180000
    finally:
        engine.dispose()


def _legacy_row_at_parent():
    engine = sa.create_engine(POSTGRES_URL)
    with engine.begin() as connection:
        connection.execute(sa.text(
            "INSERT INTO operational_organization "
            "(id, public_id, name, is_active, created_at) VALUES "
            "(900001, '90000000-0000-4000-8000-000000000001', "
            "'P3-04 legacy org', true, CURRENT_TIMESTAMP)"
        ))
        connection.execute(sa.text(
            "INSERT INTO expert_user "
            "(id, username, password_hash, full_name, role, authority, is_active, "
            "can_handle_domestic, can_handle_international, sla_response_work_minutes, created_at) VALUES "
            "(900001, 'p304-legacy-owner', 'unused', 'Legacy Owner', 'expert', "
            "'EXPERT', true, true, true, 120, CURRENT_TIMESTAMP)"
        ))
        connection.execute(sa.text(
            "INSERT INTO execution_unit "
            "(id, public_id, organization_id, unit_code, unit_type, lifecycle_status, "
            "is_active, attention_required, delayed, version, created_by_user_id, "
            "created_at, updated_at) VALUES "
            "(900001, '90000000-0000-4000-8000-000000000002', 900001, "
            "'LEGACY-P304', 'legacy_unknown', 'not_started', true, false, false, 1, "
            "900001, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))
    engine.dispose()


def _seed_runtime(app):
    org_a = OperationalOrganization(name="P3-04 PostgreSQL A")
    org_b = OperationalOrganization(name="P3-04 PostgreSQL B")
    owner = ExpertUser(
        username="p304-pg-owner", password_hash="unused", full_name="Owner",
        role="expert", authority="EXPERT", is_active=True,
    )
    outsider = ExpertUser(
        username="p304-pg-outsider", password_hash="unused", full_name="Outsider",
        role="expert", authority="EXPERT", is_active=True,
    )
    db.session.add_all([org_a, org_b, owner, outsider])
    db.session.flush()
    permissions = [
        "operational_shipment.read", "execution_unit.read",
        "execution_unit.create", "execution_unit.update",
    ]
    db.session.add_all([
        OperationalMembership(
            organization_id=org_a.id, user_id=owner.id, permissions=permissions
        ),
        OperationalMembership(
            organization_id=org_b.id, user_id=outsider.id, permissions=permissions
        ),
    ])
    carrier = Customer(
        operational_organization_id=org_a.id, ownership_scope="TENANT",
        company_name="P3-04 PG Carrier", status="active",
    )
    foreign_carrier = Customer(
        operational_organization_id=org_b.id, ownership_scope="TENANT",
        company_name="P3-04 PG Foreign Carrier", status="active",
    )
    db.session.add_all([carrier, foreign_carrier])
    db.session.flush()
    db.session.add_all([
        CustomerRoleAssignment(
            customer_id=row.id,
            operational_organization_id=row.operational_organization_id,
            role_code="CARRIER",
            is_active=True,
        )
        for row in (carrier, foreign_carrier)
    ])
    truck = TransportMeansType(
        immutable_code="P304_PG_TRUCK", fa_name="کامیون", en_name="Truck",
        is_active=True,
    )
    trailer = TransportEquipmentType(
        immutable_code="P304_PG_TRAILER", fa_name="تریلر", en_name="Trailer",
        is_active=True,
    )
    db.session.add_all([truck, trailer])
    db.session.flush()
    db.session.add_all([
        OrganizationTransportMeansTypeActivation(
            organization_id=org_a.id, transport_means_type_id=truck.id,
            created_by=owner.id, updated_by=owner.id,
        ),
        OrganizationTransportEquipmentTypeActivation(
            organization_id=org_a.id, transport_equipment_type_id=trailer.id,
            created_by=owner.id, updated_by=owner.id,
        ),
    ])
    origin = CanonicalLocation(
        source_type="province", source_id=800001, location_type="province",
        display_name="Origin", country_code="CN",
    )
    destination = CanonicalLocation(
        source_type="province", source_id=800002, location_type="province",
        display_name="Destination", country_code="KZ",
    )
    db.session.add_all([origin, destination])
    db.session.flush()
    shipment = OperationalShipment(
        organization_id=org_a.id, source_type="direct", customer_id=carrier.id,
        lifecycle_status="planned", created_by_user_id=owner.id,
        primary_responsible_expert_id=owner.id,
    )
    db.session.add(shipment)
    db.session.flush()
    plan = RoutePlan(
        operational_shipment_id=shipment.id, revision_number=1,
        status="active", is_active=True, created_by_user_id=owner.id,
    )
    db.session.add(plan)
    db.session.flush()
    leg = RouteLeg(
        route_plan_id=plan.id, sequence_number=1,
        origin_location_id=origin.id, destination_location_id=destination.id,
        origin_snapshot={"display_name": "Origin"},
        destination_snapshot={"display_name": "Destination"},
        transport_mode="road", status="planned",
    )
    db.session.add(leg)
    db.session.commit()
    return {
        "owner": owner.id,
        "outsider": outsider.id,
        "shipment": shipment.public_id,
        "plan": plan.id,
        "leg": leg.id,
        "truck": truck.public_id,
        "trailer": trailer.public_id,
        "carrier": carrier.id,
        "foreign_carrier": foreign_carrier.id,
    }


def _create_payload(ctx, identifier):
    return {
        "transport_means_type_public_id": ctx["truck"],
        "carrier_customer_id": ctx["carrier"],
        "means_identifier": identifier,
        "equipment": [
            {"type_public_id": ctx["trailer"], "identifier": f"T-{identifier}"}
        ],
    }


def _create_worker(app, ctx, barrier, key, identifier):
    with app.app_context():
        barrier.wait()
        try:
            row, created = executions.create(
                ctx["shipment"], ctx["plan"], ctx["leg"],
                _create_payload(ctx, identifier),
                {"id": ctx["owner"]}, key,
            )
            public_id = row.execution_unit.public_id
            db.session.commit()
            return "ok", created, public_id
        except operations.OperationalError as exc:
            db.session.rollback()
            return "error", exc.code, None
        finally:
            db.session.remove()


def _revise_worker(app, ctx, barrier, execution_id, key, identifier):
    with app.app_context():
        barrier.wait()
        try:
            executions.revise(
                ctx["shipment"], ctx["plan"], execution_id,
                {**_create_payload(ctx, identifier), "expected_version": 1},
                {"id": ctx["owner"]}, key,
            )
            db.session.commit()
            return "ok"
        except operations.OperationalError as exc:
            db.session.rollback()
            return exc.code
        finally:
            db.session.remove()


def test_postgresql18_migration_legacy_tenant_constraints_and_concurrency():
    _assert_owned_postgres_18()
    config = alembic_config(POSTGRES_URL)
    command.upgrade(config, PREVIOUS)
    _legacy_row_at_parent()
    command.upgrade(config, HEAD)
    engine = sa.create_engine(POSTGRES_URL)
    inspector = sa.inspect(engine)
    assert {
        "route_stage_execution",
        "execution_transport_revision",
        "execution_transport_equipment_snapshot",
    } <= set(inspector.get_table_names())
    with engine.connect() as connection:
        assert connection.execute(sa.text(
            "SELECT vehicle_reference FROM execution_unit WHERE id=900001"
        )).scalar_one() is None
        assert connection.execute(sa.text(
            "SELECT count(*) FROM execution_transport_revision WHERE execution_unit_id=900001"
        )).scalar_one() == 0
    command.downgrade(config, PREVIOUS)
    with engine.connect() as connection:
        assert connection.execute(sa.text(
            "SELECT unit_type FROM execution_unit WHERE id=900001"
        )).scalar_one() == "legacy_unknown"
    command.upgrade(config, HEAD)
    engine.dispose()

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": POSTGRES_URL,
            "SECRET_KEY": "p3-04-postgresql",
        },
        skip_startup=True,
    )
    with app.app_context():
        ctx = _seed_runtime(app)
        with pytest.raises(operations.OperationalError) as foreign_carrier:
            executions.create(
                ctx["shipment"], ctx["plan"], ctx["leg"],
                {**_create_payload(ctx, "FOREIGN"),
                 "carrier_customer_id": ctx["foreign_carrier"]},
                {"id": ctx["owner"]}, "pg-foreign-carrier",
            )
        assert foreign_carrier.value.code == "TENANT_SCOPE_VIOLATION"
        db.session.rollback()
        with pytest.raises(operations.OperationalError) as foreign_shipment:
            executions.list_for_plan(
                ctx["shipment"], ctx["plan"], {"id": ctx["outsider"]}
            )
        assert foreign_shipment.value.status == 404
        db.session.rollback()

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        distinct = list(pool.map(
            lambda values: _create_worker(app, ctx, barrier, *values),
            [("pg-distinct-1", "PG-1"), ("pg-distinct-2", "PG-2")],
        ))
    assert [result[0] for result in distinct].count("ok") == 2

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replay = list(pool.map(
            lambda _value: _create_worker(
                app, ctx, barrier, "pg-same-key", "PG-SAME"
            ),
            [1, 2],
        ))
    assert sorted(result[1] for result in replay) == [False, True]
    assert len({result[2] for result in replay}) == 1

    with app.app_context():
        target, _ = executions.create(
            ctx["shipment"], ctx["plan"], ctx["leg"],
            _create_payload(ctx, "PG-ORIGINAL"), {"id": ctx["owner"]},
            "pg-revision-target",
        )
        target_id = target.execution_unit.public_id
        db.session.commit()

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        revised = list(pool.map(
            lambda values: _revise_worker(app, ctx, barrier, target_id, *values),
            [("pg-revise-1", "PG-NEW-1"), ("pg-revise-2", "PG-NEW-2")],
        ))
    assert sorted(revised) == ["VERSION_CONFLICT", "ok"]
    with app.app_context():
        assert ExecutionUnit.query.filter_by(
            organization_id=OperationalShipment.query.filter_by(
                public_id=ctx["shipment"]
            ).one().organization_id,
            unit_type="transport_execution",
        ).count() == 4
        db.session.remove()
        db.engine.dispose()

    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(config, PREVIOUS)
    engine = sa.create_engine(POSTGRES_URL)
    with engine.connect() as connection:
        assert connection.execute(sa.text(
            "SELECT version_num FROM alembic_version"
        )).scalar_one() == HEAD
    engine.dispose()
