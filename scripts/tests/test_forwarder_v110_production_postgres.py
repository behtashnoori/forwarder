"""Disposable PostgreSQL 18 rehearsal for the v1.10.0 Production tooling."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from alembic import command
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.migration_runtime import alembic_config, revision_status
from backend.tests.test_fixed_shipment_owner_postgresql import (
    _accepted_shipment,
    _customer,
    _direct_shipment,
    _expert,
    _organization,
    _request,
    _reset,
)


ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = ROOT / "scripts" / "production" / "v1.10.0" / "sql"
BEFORE = "20260921_shipment_evidence_ownership"
TARGET = "20260926_fixed_shipment_responsible_expert"


def _url() -> str:
    value = os.environ.get("FORWARDER_V110_PRODUCTION_TOOLING_POSTGRES_URL")
    if not value:
        pytest.skip("owned disposable Forwarder v1.10.0 PostgreSQL URL required")
    parsed = make_url(value)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.database == "forwarder_v110_production_tooling"
    return value


def _read_only_query(connection, name: str):
    sql = (SQL_ROOT / name).read_text(encoding="utf-8")
    assert sql.startswith("BEGIN TRANSACTION READ ONLY;\n")
    assert sql.rstrip().endswith("COMMIT;")
    body = sql.split(";", 1)[1].rsplit("COMMIT;", 1)[0].strip()
    connection.execute(text("SET TRANSACTION READ ONLY"))
    return connection.execute(text(body))


def _quote_before_target(connection, organization_id: int, request_id: int, issuer_id: int, response: str = "accepted") -> int:
    return int(connection.execute(
        text(
            "INSERT INTO expert_quote "
            "(shipment_request_id, operational_organization_id, amount, currency, "
            "created_by_expert_id, created_at, customer_response, responded_at) "
            "VALUES (:request_id, :organization_id, 100, 'IRR', :issuer_id, now(), "
            ":response, now()) RETURNING id"
        ),
        {"request_id": request_id, "organization_id": organization_id, "issuer_id": issuer_id, "response": response},
    ).scalar_one())


def _seed_common(connection, label: str):
    organization = _organization(connection, f"v1.10 tooling {label}")
    first = _expert(connection, organization, f"{label}-expert-one")
    second = _expert(connection, organization, f"{label}-expert-two")
    customer = _customer(connection, organization, f"{label} Customer")
    request = _request(connection, organization, customer, second, label)
    return organization, first, second, customer, request


def _classifier_counts(engine) -> dict[str, int]:
    with engine.connect() as connection, connection.begin():
        row = _read_only_query(connection, "adr047-production-classifier.sql").mappings().one()
        return {key: int(value) for key, value in row.items()}


def test_full_five_revision_path_classifier_repair_and_post_assertions() -> None:
    url = _url()
    _reset(url, BEFORE)
    engine = create_engine(url)
    with engine.begin() as connection:
        organization, first, second, customer, request = _seed_common(connection, "success")
        quote = _quote_before_target(connection, organization, request, first)
        _accepted_shipment(connection, organization, request, quote, second, first)
        repair_request = _request(connection, organization, customer, second, "repair")
        repair_quote = _quote_before_target(connection, organization, repair_request, first)
        _accepted_shipment(connection, organization, repair_request, repair_quote, second, None)
        _direct_shipment(connection, organization, customer, first)

    counts = _classifier_counts(engine)
    assert counts == {
        "fixed_owner_already_valid_count": 2,
        "fixed_owner_deterministic_repair_count": 1,
        "fixed_owner_ambiguous_count": 0,
        "fixed_owner_contradiction_count": 0,
        "fixed_owner_other_unresolved_count": 0,
    }
    with engine.connect() as connection, connection.begin():
        compatibility = list(_read_only_query(connection, "migration-compatibility-readonly.sql").mappings())
    assert compatibility and {row["check_state"] for row in compatibility} == {"PASS"}

    command.upgrade(alembic_config(url), TARGET)
    assert revision_status(url).current == (TARGET,)
    with engine.connect() as connection, connection.begin():
        assertions = list(_read_only_query(connection, "post-migration-assertions-readonly.sql").mappings())
    assert assertions and {row["check_state"] for row in assertions} == {"PASS"}
    engine.dispose()


@pytest.mark.parametrize(
    ("scenario", "counter"),
    [
        ("ambiguous_quote_lineage", "fixed_owner_ambiguous_count"),
        ("persisted_owner_contradiction", "fixed_owner_contradiction_count"),
        ("missing_accepted_quote", "fixed_owner_other_unresolved_count"),
        ("invalid_direct_owner", "fixed_owner_other_unresolved_count"),
    ],
)
def test_preflight_classifier_blocks_unsafe_adr047_history(scenario: str, counter: str) -> None:
    url = _url()
    _reset(url, BEFORE)
    engine = create_engine(url)
    with engine.begin() as connection:
        organization, first, second, customer, request = _seed_common(connection, scenario)
        if scenario == "invalid_direct_owner":
            admin = _expert(connection, organization, f"{scenario}-admin", authority="ORGANIZATION_ADMIN")
            _direct_shipment(connection, organization, customer, admin)
        elif scenario == "missing_accepted_quote":
            quote = _quote_before_target(connection, organization, request, first)
            _accepted_shipment(connection, organization, request, quote, second, None)
            # Model an already-corrupt historical orphan without changing the
            # schema.  This is restricted to the owned disposable superuser DB.
            connection.execute(text("SET LOCAL session_replication_role='replica'"))
            connection.execute(text("DELETE FROM expert_quote WHERE id=:quote"), {"quote": quote})
        else:
            quote = _quote_before_target(
                connection, organization, request, first,
                response="declined" if scenario == "ambiguous_quote_lineage" else "accepted",
            )
            owner = second if scenario == "persisted_owner_contradiction" else None
            _accepted_shipment(connection, organization, request, quote, second, owner)

    counts = _classifier_counts(engine)
    assert counts[counter] == 1
    assert sum(counts[name] for name in (
        "fixed_owner_ambiguous_count",
        "fixed_owner_contradiction_count",
        "fixed_owner_other_unresolved_count",
    )) == 1
    assert revision_status(url).current == (BEFORE,)
    engine.dispose()
