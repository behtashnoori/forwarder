"""Certify ADR-038 Phase 1 on one disposable loopback PostgreSQL database."""
from __future__ import annotations

import os
from uuid import UUID, uuid4

from alembic import command
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade

PREDECESSOR = "20260901_document_catalog_runs"
REVISION = "20260902_shipment_request_public_id"
ENVIRONMENT = "SHIPMENT_REQUEST_IDENTITY_CERT_DATABASE_URL"


def _canonical_uuid4(value: str) -> bool:
    parsed = UUID(value)
    return parsed.version == 4 and value == str(parsed)


url = make_url(os.environ[ENVIRONMENT])
if url.get_backend_name() != "postgresql" or url.host not in {"127.0.0.1", "localhost", "::1"}:
    raise SystemExit("Refusing: certification requires disposable loopback PostgreSQL")

rendered = url.render_as_string(hide_password=False)
config = alembic_config(rendered)
prepare_version_table_for_upgrade(rendered, config)
command.upgrade(config, PREDECESSOR)
engine = create_engine(url)

legacy_rows = [
    (99101, "SR000101", 98101),
    (99102, "SR-ABC123", 98102),
]
with engine.begin() as connection:
    now = connection.execute(text("SELECT CURRENT_TIMESTAMP")).scalar_one()
    for organization_id in (98101, 98102):
        connection.execute(text(
            "INSERT INTO operational_organization "
            "(id, public_id, name, is_active, created_at) "
            "VALUES (:id, :public_id, :name, true, :now)"
        ), {
            "id": organization_id,
            "public_id": str(uuid4()),
            "name": f"ADR038 certification {organization_id}",
            "now": now,
        })
    for request_id, tracking_code, organization_id in legacy_rows:
        connection.execute(text(
            "INSERT INTO shipment_request "
            "(id, shipping_type, contact_phone, created_at, ready_at, "
            "status_request_status, status, tracking_code, ownership_scope, operational_organization_id) "
            "VALUES (:id, 'domestic', :phone, :now, :now, 'new', 'new', "
            ":tracking_code, 'TENANT', :organization_id)"
        ), {
            "id": request_id,
            "phone": f"09{request_id:09d}"[-11:],
            "now": now,
            "tracking_code": tracking_code,
            "organization_id": organization_id,
        })

command.upgrade(config, REVISION)
with engine.connect() as connection:
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == REVISION
    columns = {column["name"]: column for column in inspect(connection).get_columns("shipment_request")}
    assert columns["public_id"]["nullable"] is True
    unique_constraints = inspect(connection).get_unique_constraints("shipment_request")
    assert any(
        item["name"] == "uq_shipment_request_public_id"
        and item["column_names"] == ["public_id"]
        for item in unique_constraints
    )
    rows = connection.execute(text(
        "SELECT id, tracking_code, public_id, operational_organization_id "
        "FROM shipment_request WHERE id IN (99101, 99102) ORDER BY id"
    )).mappings().all()
    assert len(rows) == 2
    assert [row["tracking_code"] for row in rows] == ["SR000101", "SR-ABC123"]
    assert [row["operational_organization_id"] for row in rows] == [98101, 98102]
    assert len({row["public_id"] for row in rows}) == 2
    assert all(_canonical_uuid4(row["public_id"]) for row in rows)
    assert all(row["public_id"] not in {str(row["id"]), row["tracking_code"]} for row in rows)
    first_values = {row["id"]: row["public_id"] for row in rows}

command.downgrade(config, PREDECESSOR)
with engine.connect() as connection:
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == PREDECESSOR
    assert "public_id" not in {column["name"] for column in inspect(connection).get_columns("shipment_request")}
    assert connection.execute(text(
        "SELECT tracking_code FROM shipment_request WHERE id IN (99101, 99102) ORDER BY id"
    )).scalars().all() == ["SR000101", "SR-ABC123"]

command.upgrade(config, REVISION)
with engine.connect() as connection:
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == REVISION
    rows = connection.execute(text(
        "SELECT id, public_id FROM shipment_request WHERE id IN (99101, 99102) ORDER BY id"
    )).mappings().all()
    assert all(_canonical_uuid4(row["public_id"]) for row in rows)
    assert len({row["public_id"] for row in rows}) == 2
    # A destructive pre-adoption downgrade legitimately discards unused IDs;
    # re-upgrade must create fresh safe identities, never deterministic values.
    assert all(row["public_id"] != first_values[row["id"]] for row in rows)

engine.dispose()
print(
    "shipment-request-public-id-postgres-gate=PASS "
    f"predecessor={PREDECESSOR} revision={REVISION} rows={len(legacy_rows)}"
)
