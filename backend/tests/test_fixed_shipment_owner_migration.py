"""Static graph and safety contracts for ADR-047 owner reconciliation."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from backend.operational_models import OperationalShipment


MIGRATION_REVISION = "20260926_fixed_shipment_responsible_expert"
REPOSITORY_HEAD = "20261006_customer_entitlement"
PREVIOUS = "20260925_quote_communication"
MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20260926_fixed_shipment_owner.py"
)


def test_fixed_owner_migration_is_linear_fail_closed_and_never_uses_request_assignee():
    source = MIGRATION.read_text(encoding="utf-8")
    assert f'revision = "{MIGRATION_REVISION}"' in source
    assert f'down_revision = "{PREVIOUS}"' in source
    assert "primary_responsible_expert_id" in source
    assert "nullable=False" in source
    assert "PERSISTED_OWNER_CONFLICT" in source
    assert "DIRECT_OWNER_MISSING" in source
    assert "INVALID_ACCEPTED_QUOTE_ISSUER" in source
    assert "adjudication required" in source
    assert "ShipmentRequest.assigned_to" not in source
    assert "assigned_to" not in source
    assert "OperationalShipment responsible Expert is immutable" in source

    config = Config(str(Path(__file__).parents[1] / "migrations" / "alembic.ini"))
    config.set_main_option(
        "script_location", str(Path(__file__).parents[1] / "migrations")
    )
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(MIGRATION_REVISION).down_revision == PREVIOUS
    assert script.get_bases() == ["20240917_initial_schema"]


def test_runtime_model_requires_one_persisted_owner():
    column = OperationalShipment.__table__.c.primary_responsible_expert_id
    assert column.nullable is False
    assert column.foreign_keys
