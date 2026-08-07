"""Focused Release 1.9.0 bounded operational execution contracts."""

from datetime import datetime, timedelta, timezone
import re
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import event as sqlalchemy_event
from backend import create_app
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, ShipmentRequest
from backend.operational_models import (
    DelayReason,
    ExceptionReason,
    Milestone,
    MilestoneEvent,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
    RoutePlan,
)
from backend.project_configuration_models import (
    MilestoneType,
    ProjectMilestoneDefinition,
)
from backend.services import operational_execution_service as svc


@pytest.fixture()
def execution_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "execution-190",
        }
    )
    with app.app_context():
        org = OperationalOrganization(name="Execution Org")
        other = OperationalOrganization(name="Other Org")
        operator = ExpertUser(
            username="execution-operator",
            password_hash="x",
            full_name="Operator",
            role="admin",
            is_active=True,
        )
        verifier = ExpertUser(
            username="execution-verifier",
            password_hash="x",
            full_name="Verifier",
            role="admin",
            is_active=True,
        )
        outsider = ExpertUser(
            username="execution-outsider",
            password_hash="x",
            full_name="Outsider",
            role="admin",
            is_active=True,
        )
        customer = Customer(first_name="Execution", last_name="Customer")
        db.session.add_all([org, other, operator, verifier, outsider, customer])
        db.session.flush()
        permissions = [
            "operational_execution.read",
            "operational_execution.manage",
            "operational_event.create",
            "operational_event.correct",
            "operational_event.verify",
            "delay_reason.manage",
            "exception_reason.manage",
        ]
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id, user_id=operator.id, permissions=permissions
                ),
                OperationalMembership(
                    organization_id=org.id, user_id=verifier.id, permissions=permissions
                ),
                OperationalMembership(
                    organization_id=other.id,
                    user_id=outsider.id,
                    permissions=permissions,
                ),
            ]
        )
        project = Project(
            organization_id=org.id,
            primary_customer_id=customer.id,
            project_code="EXEC",
            tracking_code="exec-project",
            created_by_user_id=operator.id,
        )
        request = ShipmentRequest(
            contact_phone="09000000001",
            status="waiting_for_customer",
            status_request_status="new",
            assigned_to=operator.id,
        )
        db.session.add_all([project, request])
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request.id,
            amount=1,
            currency="IRR",
            created_by_expert_id=operator.id,
            created_at=datetime.now(timezone.utc),
            customer_response="accepted",
            responded_at=datetime.now(timezone.utc),
            operational_organization_id=org.id,
        )
        db.session.add(quote)
        db.session.flush()
        shipment = OperationalShipment(
            organization_id=org.id,
            project_id=project.id,
            shipment_request_id=request.id,
            accepted_quote_id=quote.id,
            created_by_user_id=operator.id,
        )
        milestone_type = MilestoneType(
            immutable_code="CUSTOMS_CLEARANCE",
            fa_name="ترخیص",
            en_name="Customs clearance",
            display_order=1,
            created_by=operator.id,
            updated_by=operator.id,
        )
        db.session.add_all([shipment, milestone_type])
        db.session.flush()
        definition = ProjectMilestoneDefinition(
            project_id=project.id,
            milestone_type_id=milestone_type.id,
            sequence=1,
            is_required=True,
            target_duration_value=2,
            warning_duration_value=3,
            duration_unit="HOUR",
            created_by=operator.id,
            updated_by=operator.id,
        )
        db.session.add(definition)
        db.session.commit()
        app.config["ctx"] = {
            "shipment": shipment.public_id,
            "operator": operator.id,
            "verifier": verifier.id,
            "outsider": outsider.id,
        }
        yield app
        db.session.remove()
        db.drop_all()


def actor(app, key="operator"):
    return {"id": app.config["ctx"][key], "role": "admin"}


def test_preview_confirm_idempotency_and_no_project_mutation(execution_app):
    with execution_app.app_context():
        shipment = OperationalShipment.query.filter_by(
            public_id=execution_app.config["ctx"]["shipment"]
        ).one()
        project_version = db.session.get(Project, shipment.project_id).version
        preview = svc.initialization_preview(shipment.public_id, actor(execution_app))
        assert preview["confirmation_allowed"] and preview["initialized"] is False
        rows, created = svc.initialize(
            shipment.public_id, {"expected_shipment_version": 1}, actor(execution_app)
        )
        assert created and len(rows) == 1 and rows[0].lifecycle_status == "PENDING"
        assert rows[0].route_plan_id is None
        projection = svc.milestone_projection(rows[0])
        assert projection["route_plan_public_id"] is None
        assert "route_plan_id" not in projection
        replay, recreated = svc.initialize(
            shipment.public_id, {"expected_shipment_version": 2}, actor(execution_app)
        )
        assert not recreated and replay[0].id == rows[0].id
        assert (
            db.session.get(Project, shipment.project_id).version == project_version
            and MilestoneEvent.query.filter_by(event_type="INITIALIZED").count() == 1
        )


def test_transition_block_unblock_terminal_reopen_and_progress(execution_app):
    with execution_app.app_context():
        shipment = OperationalShipment.query.one()
        rows, _ = svc.initialize(
            shipment.public_id, {"expected_shipment_version": 1}, actor(execution_app)
        )
        m = rows[0]
        svc.transition(
            shipment.public_id,
            m.public_id,
            {
                "expected_version": 1,
                "target_status": "BLOCKED",
                "reason": "CUSTOMS_HOLD",
            },
            actor(execution_app),
        )
        assert m.prior_active_status == "PENDING"
        svc.transition(
            shipment.public_id,
            m.public_id,
            {"expected_version": 2, "target_status": "PENDING"},
            actor(execution_app),
        )
        svc.transition(
            shipment.public_id,
            m.public_id,
            {"expected_version": 3, "target_status": "READY"},
            actor(execution_app),
        )
        svc.transition(
            shipment.public_id,
            m.public_id,
            {"expected_version": 4, "target_status": "IN_PROGRESS"},
            actor(execution_app),
        )
        svc.transition(
            shipment.public_id,
            m.public_id,
            {"expected_version": 5, "target_status": "COMPLETED"},
            actor(execution_app),
        )
        assert (
            svc.progress(shipment.public_id, actor(execution_app))[
                "completion_percentage"
            ]
            == 100
        )
        with pytest.raises(svc.OperationalError):
            svc.transition(
                shipment.public_id,
                m.public_id,
                {"expected_version": 6, "target_status": "READY"},
                actor(execution_app),
            )
        svc.reopen(
            shipment.public_id,
            m.public_id,
            {"expected_version": 6, "reason": "Completion corrected"},
            actor(execution_app),
        )
        assert (
            m.lifecycle_status == "READY"
            and MilestoneEvent.query.filter_by(event_type="REOPENED").count() == 1
        )


def test_reason_delay_exception_lifecycle_and_tenant_isolation(execution_app):
    with execution_app.app_context():
        shipment = OperationalShipment.query.one()
        svc.initialize(
            shipment.public_id, {"expected_shipment_version": 1}, actor(execution_app)
        )
        delays = svc.reason_collection(
            "delay",
            actor(execution_app),
            {
                "immutable_code": "PORT_HOLD",
                "fa_name": "توقف بندر",
                "en_name": "Port hold",
            },
        )
        exceptions = svc.reason_collection(
            "exception",
            actor(execution_app),
            {"immutable_code": "DAMAGE", "fa_name": "آسیب", "en_name": "Damage"},
        )
        now = datetime.now(timezone.utc) - timedelta(minutes=5)
        created = svc.condition_collection(
            "delay",
            shipment.public_id,
            actor(execution_app),
            {"reason_public_id": delays[0]["public_id"], "started_at": now.isoformat()},
        )
        assert created[0]["active"]
        resolved = svc.resolve_condition(
            "delay",
            shipment.public_id,
            created[0]["public_id"],
            {"expected_version": 1},
            actor(execution_app),
        )
        assert not resolved["active"] and resolved["duration_seconds"] >= 300
        exc = svc.condition_collection(
            "exception",
            shipment.public_id,
            actor(execution_app),
            {
                "reason_public_id": exceptions[0]["public_id"],
                "occurred_at": now.isoformat(),
            },
        )
        assert (
            exc[0]["active"]
            and svc.progress(shipment.public_id, actor(execution_app))[
                "active_exception_count"
            ]
            == 1
        )
        with pytest.raises(svc.OperationalError) as hidden:
            svc.progress(shipment.public_id, actor(execution_app, "outsider"))
        assert (
            hidden.value.status == 404
            and DelayReason.query.count() == 1
            and ExceptionReason.query.count() == 1
        )


def test_verification_separation_and_one_migration_head(execution_app):
    with execution_app.app_context():
        shipment = OperationalShipment.query.one()
        rows, _ = svc.initialize(
            shipment.public_id, {"expected_shipment_version": 1}, actor(execution_app)
        )
        event = MilestoneEvent.query.filter_by(
            milestone_id=rows[0].id, event_type="INITIALIZED"
        ).one()
        with pytest.raises(svc.OperationalError) as self_verify:
            svc.verify_event(
                shipment.public_id, event.public_id, {}, actor(execution_app)
            )
        assert self_verify.value.code == "SELF_VERIFICATION_FORBIDDEN"
        svc.verify_event(
            shipment.public_id, event.public_id, {}, actor(execution_app, "verifier")
        )
        assert (
            event.verification_state == "verified"
            and MilestoneEvent.query.filter_by(event_type="VERIFIED").count() == 1
        )
    config = Config("backend/migrations/alembic.ini")
    assert ScriptDirectory.from_config(config).get_heads() == [
        "20260812_operational_execution"
    ]


def test_optional_route_plan_mapper_and_same_shipment_constraint(execution_app):
    route_plan = Milestone.__table__.c.route_plan_id
    shipment = Milestone.__table__.c.operational_shipment_id
    organization = Milestone.__table__.c.organization_id
    assert route_plan.nullable is True
    assert shipment.nullable is False and organization.nullable is False
    constraints = {
        constraint.name: constraint
        for constraint in Milestone.__table__.foreign_key_constraints
    }
    scoped = constraints["fk_operational_milestone_plan_shipment"]
    assert [column.name for column in scoped.columns] == [
        "route_plan_id",
        "operational_shipment_id",
    ]
    assert RoutePlan.__table__.c.operational_shipment_id.nullable is False


def test_release_migration_has_nullable_upgrade_and_fail_closed_downgrade():
    source = open(
        "backend/migrations/versions/20260812_operational_execution.py",
        encoding="utf-8",
    ).read()  # noqa: SIM115
    assert '"route_plan_id",\n        existing_type=sa.BigInteger(),\n        nullable=True' in source
    assert "fk_operational_milestone_plan_shipment" in source
    assert "operational milestones without RoutePlan exist" in source
    assert "WHERE route_plan_id IS NULL" in source


def test_opaque_event_create_and_append_only_correction(execution_app):
    with execution_app.app_context():
        shipment = OperationalShipment.query.one()
        rows, _ = svc.initialize(
            shipment.public_id, {"expected_shipment_version": 1}, actor(execution_app)
        )
        effective = datetime.now(timezone.utc) - timedelta(minutes=2)
        original = svc.create_event(
            shipment.public_id,
            rows[0].public_id,
            {"expected_version": 1, "effective_at": effective.isoformat()},
            actor(execution_app),
        )
        corrected = svc.correct_event(
            shipment.public_id,
            original.public_id,
            {
                "expected_version": 2,
                "effective_at": (effective + timedelta(minutes=1)).isoformat(),
                "reason": "Operator corrected occurrence time",
            },
            actor(execution_app),
        )
        assert corrected.supersedes_event_id == original.id
        assert db.session.get(MilestoneEvent, original.id) is original
        assert MilestoneEvent.query.filter_by(milestone_id=rows[0].id).count() == 3

        statements = []
        engine = db.engine

        def capture(_connection, _cursor, statement, _parameters, _context, _many):
            statements.append(statement)

        sqlalchemy_event.listen(engine, "before_cursor_execute", capture)
        try:
            payload = svc.events(shipment.public_id, actor(execution_app))
        finally:
            sqlalchemy_event.remove(engine, "before_cursor_execute", capture)
        assert len(statements) <= 6
        assert len(str(payload).encode("utf-8")) < 16_384


def test_openapi_exact_runtime_path_parity(execution_app):
    document = open("docs/openapi/openapi.yaml", encoding="utf-8").read()  # noqa: SIM115
    assert "  version: 1.9.0" in document
    runtime = {
        rule.rule.replace("<shipment_id>", "{shipment_id}")
        .replace("<milestone_id>", "{milestone_id}")
        .replace("<event_id>", "{event_id}")
        .replace("<public_id>", "{public_id}")
        for rule in execution_app.url_map.iter_rules()
        if rule.endpoint.startswith("operational_execution.")
    }
    assert all(f"  {path}:" in document for path in runtime)
    for schema in (
        "ExecutionMilestone",
        "OperationalReason",
        "OperationalCondition",
        "MilestoneEvent190",
    ):
        assert re.search(
            rf"^    {schema}:\n(?:      .*\n){{0,4}}      additionalProperties: false$",
            document,
            re.MULTILINE,
        )
