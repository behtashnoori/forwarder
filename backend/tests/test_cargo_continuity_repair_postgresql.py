"""PostgreSQL 18 concurrency proof for the governed Cargo repair."""

from concurrent.futures import ThreadPoolExecutor
import json
import os

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import cargo_continuity_repair_cli as repair_cli
from backend.cargo_models import ShipmentCargoItem
from backend.extensions import db
from backend.operational_models import (
    OperationalAudit,
    OperationalIdempotency,
    OperationalOutbox,
    RouteCargoDestination,
)
from backend.services.cargo_continuity_repair_service import (
    IDEMPOTENCY_OPERATION,
    REPAIR_ACTION,
    apply_repair,
    plan_repair,
)
from backend.tests.test_cargo_continuity_repair import (
    ADMIN_USERNAME,
    TRACKING_CODE,
    repair_app,  # noqa: F401 - imported fixture for indirect parametrization
)


URL = os.environ.get("CARGO_CONTINUITY_REPAIR_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(
    not URL, reason="requires explicit owned CARGO_CONTINUITY_REPAIR_POSTGRES_URL"
)


@pytest.mark.parametrize("repair_app", [URL], indirect=True)
def test_postgresql18_concurrent_apply_is_atomic_and_idempotent(
    repair_app,  # noqa: F811
    monkeypatch,
    capsys,
):
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith("forwarder_cargo_continuity_repair_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(
            connection.execute(sa.text("SHOW server_version_num")).scalar_one()
        ) < 190000
        assert connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one() == "20261013_structured_route_progress_eta"

    app, context = repair_app
    with app.app_context():
        plan = plan_repair(
            context["shipment_public_id"],
            ADMIN_USERNAME,
            TRACKING_CODE,
            context["cargo_public_id"],
            context["source_cargo_public_id"],
            context["plan_id"],
            context["leg_id"],
        )
        assert plan["eligibility"] == "YES"
        fingerprint = plan["plan_fingerprint"]
        db.session.rollback()

    def apply_once(_attempt):
        with app.app_context():
            try:
                return apply_repair(
                    context["shipment_public_id"],
                    ADMIN_USERNAME,
                    operator=ADMIN_USERNAME,
                    approval_reference="ADR-072/postgresql-concurrency-proof",
                    expected_plan_fingerprint=fingerprint,
                    expected_request_tracking_code=TRACKING_CODE,
                    expected_cargo_public_id=context["cargo_public_id"],
                    expected_source_request_cargo_public_id=context[
                        "source_cargo_public_id"
                    ],
                    expected_route_plan_id=context["plan_id"],
                    expected_terminal_route_leg_id=context["leg_id"],
                )["apply_result"]
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(apply_once, ("Operator A", "Operator B")))

    assert sorted(outcomes) == ["CHANGED", "UNCHANGED"]
    monkeypatch.setattr(repair_cli, "create_app", lambda **_kwargs: app)
    cli_exit = repair_cli.main(
        [
            "apply",
            "--shipment",
            context["shipment_public_id"],
            "--actor-username",
            ADMIN_USERNAME,
            "--expected-request-tracking-code",
            TRACKING_CODE,
            "--expected-cargo-public-id",
            context["cargo_public_id"],
            "--expected-source-request-cargo-public-id",
            context["source_cargo_public_id"],
            "--expected-route-plan-id",
            str(context["plan_id"]),
            "--expected-terminal-route-leg-id",
            str(context["leg_id"]),
            "--expected-database-name",
            parsed.database,
            "--operator",
            ADMIN_USERNAME,
            "--approval-reference",
            "ADR-072/postgresql-cli-replay",
            "--expected-plan-fingerprint",
            fingerprint,
            "--confirm",
        ]
    )
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_exit == 0
    assert cli_payload["apply_result"] == "UNCHANGED"
    with app.app_context():
        cargo = db.session.get(ShipmentCargoItem, context["cargo_id"])
        assert cargo.source_shipment_request_id == context["request_id"]
        assert cargo.source_request_cargo_item_id == context["source_cargo_id"]
        assert str(cargo.requested_quantity) == "100.000000"
        assert cargo.updated_at == context["preserved_updated_at"]
        assert db.session.scalar(
            db.select(db.func.count())
            .select_from(RouteCargoDestination)
            .where(RouteCargoDestination.shipment_cargo_item_id == cargo.id)
        ) == 1
        assert db.session.scalar(
            db.select(db.func.count())
            .select_from(OperationalAudit)
            .where(
                OperationalAudit.entity_type == "ShipmentCargoItem",
                OperationalAudit.entity_id == cargo.id,
                OperationalAudit.action == REPAIR_ACTION,
            )
        ) == 1
        assert db.session.scalar(
            db.select(db.func.count())
            .select_from(OperationalOutbox)
            .where(
                OperationalOutbox.aggregate_type == "ShipmentCargoItem",
                OperationalOutbox.aggregate_id == cargo.id,
                OperationalOutbox.event_type == "cargo_continuity.repaired",
            )
        ) == 1
        assert db.session.scalar(
            db.select(db.func.count())
            .select_from(OperationalIdempotency)
            .where(
                OperationalIdempotency.operation == IDEMPOTENCY_OPERATION,
                OperationalIdempotency.command_resource_id == context["shipment_id"],
            )
        ) == 1
    engine.dispose()
