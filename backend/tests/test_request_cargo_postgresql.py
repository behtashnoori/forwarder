"""Owned PostgreSQL 18 migration and persistence proof for Request Cargo."""
from __future__ import annotations

import os

from alembic import command
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config, revision_status
from backend.models import CargoType, Province, RequestCargoItem, ShipmentRequest, UnitOfMeasure


HEAD = "20260924_request_cargo_items"
REPOSITORY_HEAD = "20260927_customer_portal_account_lifecycle"
PREVIOUS = "20260923_notification_lifecycle"
CARGO_TYPE_PUBLIC_ID = "a1111111-1111-4111-8111-111111111111"
UOM_PUBLIC_ID = "b2222222-2222-4222-8222-222222222222"


def _url() -> str:
    url = os.environ.get("REQUEST_CARGO_DISPOSABLE_POSTGRES_URL")
    if not url:
        pytest.skip("owned disposable Request Cargo PostgreSQL URL required")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.host == "127.0.0.1"
    assert parsed.database == "forwarder_cargo_build"
    return url


def _payload(**overrides):
    payload = {
        "shipping_type": "domestic",
        "origin_province_id": 1,
        "dest_province_id": 2,
        "contact_phone": "09123456789",
        "transport_method_preference": "forwarder_suggestion",
    }
    payload.update(overrides)
    return payload


def _invalid_insert(engine, sql: str, params: dict):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(sql), params)


def test_request_cargo_owned_postgresql_lifecycle():
    url = _url()
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))

    config = alembic_config(url)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS
    command.upgrade(config, PREVIOUS)
    assert revision_status(url).current == (PREVIOUS,)

    with engine.begin() as connection:
        sentinel_id = connection.execute(text("""
            INSERT INTO shipment_request
                (contact_phone, ownership_scope, created_at, ready_at, status_request_status,
                 cargo_description, cargo_weight)
            VALUES
                ('09120000099', 'INTAKE', now(), now(), 'new',
                 'pre-migration legacy sentinel', 12.5)
            RETURNING id
        """)).scalar_one()
        before = connection.execute(
            text("SELECT to_jsonb(row) FROM shipment_request row WHERE id=:id"),
            {"id": sentinel_id},
        ).scalar_one()

    command.upgrade(config, HEAD)
    table_names = inspect(engine).get_table_names()
    assert "request_cargo_item" in table_names
    with engine.connect() as connection:
        after = connection.execute(
            text("SELECT to_jsonb(row) FROM shipment_request row WHERE id=:id"),
            {"id": sentinel_id},
        ).scalar_one()
        assert after == before
        assert connection.execute(text("SELECT COUNT(*) FROM request_cargo_item")).scalar_one() == 0

    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("request_cargo_item")}
    assert columns["quantity"]["type"].precision == 18
    assert columns["quantity"]["type"].scale == 6
    assert columns["created_at"]["type"].timezone
    assert {item["name"] for item in inspector.get_indexes("request_cargo_item")} >= {
        "ix_request_cargo_item_request"
    }
    assert {item["name"] for item in inspector.get_unique_constraints("request_cargo_item")} >= {
        "uq_request_cargo_item_public_id",
        "uq_request_cargo_item_request_position",
    }
    assert {item["name"] for item in inspector.get_check_constraints("request_cargo_item")} >= {
        "ck_request_cargo_item_position_positive",
        "ck_request_cargo_item_description_nonblank",
        "ck_request_cargo_item_quantity_positive",
        "ck_request_cargo_item_quantity_uom_pair",
        "ck_request_cargo_item_meaningful",
    }
    foreign_keys = inspector.get_foreign_keys("request_cargo_item")
    assert {item["referred_table"] for item in foreign_keys} == {
        "shipment_request", "cargo_type", "unit_of_measure"
    }
    assert all(item["options"].get("ondelete") == "RESTRICT" for item in foreign_keys)

    # An empty-table downgrade is reversible and preserves the historical sentinel.
    command.downgrade(config, PREVIOUS)
    assert "request_cargo_item" not in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT to_jsonb(row) FROM shipment_request row WHERE id=:id"),
            {"id": sentinel_id},
        ).scalar_one() == before
    command.upgrade(config, HEAD)

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": url,
        "SECRET_KEY": "owned-disposable-request-cargo-proof",
    }, skip_startup=True)
    with app.app_context():
        db.session.add_all([
            Province(id=1, code="RC-ORIGIN", name_fa="مبدأ اثبات", is_active=True),
            Province(id=2, code="RC-DEST", name_fa="مقصد اثبات", is_active=True),
            CargoType(
                public_id=CARGO_TYPE_PUBLIC_ID,
                immutable_code="REQUEST_CARGO_PROOF",
                fa_name="کالای اثبات",
                en_name="Proof cargo",
                display_order=1,
                is_active=True,
            ),
            UnitOfMeasure(
                public_id=UOM_PUBLIC_ID,
                immutable_code="REQUEST_CARGO_KG",
                fa_name="کیلوگرم اثبات",
                en_name="Proof kilogram",
                symbol="kg",
                measurement_dimension="WEIGHT",
                display_order=1,
                is_active=True,
            ),
        ])
        db.session.commit()

    client = app.test_client()
    zero = client.post("/api/shipment-request", json=_payload(cargo_items=[]))
    one = client.post("/api/shipment-request", json=_payload(cargo_items=[
        {"description": "One preserved item"},
    ]))
    multiple = client.post("/api/shipment-request", json=_payload(cargo_items=[
        {"description": "First"},
        {"cargo_type_public_id": CARGO_TYPE_PUBLIC_ID},
        {"quantity": "999999999999.123456", "uom_public_id": UOM_PUBLIC_ID},
    ]))
    assert zero.status_code == one.status_code == multiple.status_code == 201
    assert zero.get_json()["cargo_items"] == []
    assert [item["position"] for item in multiple.get_json()["cargo_items"]] == [1, 2, 3]
    assert multiple.get_json()["cargo_items"][2]["quantity"] == "999999999999.123456"

    with app.app_context():
        zero_row = db.session.get(ShipmentRequest, zero.get_json()["id"])
        one_row = db.session.get(ShipmentRequest, one.get_json()["id"])
        multi_row = db.session.get(ShipmentRequest, multiple.get_json()["id"])
        assert zero_row.request_cargo_items == []
        assert [item.description for item in one_row.request_cargo_items] == ["One preserved item"]
        assert [item.public_id for item in multi_row.request_cargo_items] == [
            item["public_id"] for item in multiple.get_json()["cargo_items"]
        ]
        request_id = multi_row.id
        cargo_type_id = db.session.query(CargoType.id).filter_by(public_id=CARGO_TYPE_PUBLIC_ID).scalar()
        uom_id = db.session.query(UnitOfMeasure.id).filter_by(public_id=UOM_PUBLIC_ID).scalar()
        db.session.remove()

    insert = """
        INSERT INTO request_cargo_item
            (public_id, shipment_request_id, position, cargo_type_id,
             description, quantity, uom_id, created_at)
        VALUES (:public_id, :request_id, :position, :cargo_type_id,
                :description, :quantity, :uom_id, now())
    """
    common = {
        "request_id": request_id,
        "cargo_type_id": cargo_type_id,
        "uom_id": uom_id,
    }
    _invalid_insert(engine, insert, {
        **common, "public_id": "invalid-position", "position": 0,
        "description": "invalid", "quantity": None,
    })
    _invalid_insert(engine, insert, {
        **common, "public_id": "invalid-pair", "position": 4,
        "cargo_type_id": None, "description": None, "quantity": "1.000000",
        "uom_id": None,
    })
    _invalid_insert(engine, insert, {
        **common, "public_id": "invalid-empty", "position": 4,
        "cargo_type_id": None, "description": None, "quantity": None,
        "uom_id": None,
    })
    _invalid_insert(engine, insert, {
        **common, "public_id": "duplicate-position", "position": 1,
        "description": "duplicate", "quantity": None,
    })
    _invalid_insert(engine, "DELETE FROM shipment_request WHERE id=:request_id", {
        "request_id": request_id,
    })

    # The child has no competing tenant key: organization fencing is inherited
    # from, and queried through, its required parent Request.
    with engine.begin() as connection:
        org_one = connection.execute(text("""
            INSERT INTO operational_organization (public_id, name, is_active, created_at)
            VALUES ('request-cargo-org-one', 'Request Cargo Org One', true, now())
            RETURNING id
        """)).scalar_one()
        org_two = connection.execute(text("""
            INSERT INTO operational_organization (public_id, name, is_active, created_at)
            VALUES ('request-cargo-org-two', 'Request Cargo Org Two', true, now())
            RETURNING id
        """)).scalar_one()
        connection.execute(text("""
            UPDATE shipment_request
            SET operational_organization_id=:org_id, ownership_scope='TENANT'
            WHERE id=:request_id
        """), {"org_id": org_one, "request_id": request_id})
        foreign_request_id = connection.execute(text("""
            INSERT INTO shipment_request
                (operational_organization_id, ownership_scope, contact_phone,
                 created_at, ready_at, status_request_status)
            VALUES (:org_id, 'TENANT', '09120000088', now(), now(), 'new')
            RETURNING id
        """), {"org_id": org_two}).scalar_one()
        connection.execute(text(insert), {
            "public_id": "other-tenant-item",
            "request_id": foreign_request_id,
            "position": 1,
            "cargo_type_id": None,
            "description": "Other tenant cargo",
            "quantity": None,
            "uom_id": None,
        })
        scoped_count = connection.execute(text("""
            SELECT COUNT(*)
            FROM request_cargo_item item
            JOIN shipment_request request ON request.id=item.shipment_request_id
            WHERE request.id=:request_id
              AND request.operational_organization_id=:org_id
              AND request.ownership_scope='TENANT'
        """), {"request_id": request_id, "org_id": org_one}).scalar_one()
        cross_tenant_count = connection.execute(text("""
            SELECT COUNT(*)
            FROM request_cargo_item item
            JOIN shipment_request request ON request.id=item.shipment_request_id
            WHERE request.id=:request_id
              AND request.operational_organization_id=:org_id
              AND request.ownership_scope='TENANT'
        """), {"request_id": request_id, "org_id": org_two}).scalar_one()
        assert scoped_count == 3
        assert cross_tenant_count == 0

    # Populated downgrade refuses to destroy Customer evidence and leaves head/data intact.
    with pytest.raises(RuntimeError, match="Request Cargo Item evidence exists"):
        command.downgrade(config, PREVIOUS)
    assert revision_status(url).current == (HEAD,)
    assert revision_status(url).heads == (REPOSITORY_HEAD,)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM request_cargo_item")).scalar_one() == 5
        assert connection.execute(
            text("SELECT to_jsonb(row) FROM shipment_request row WHERE id=:id"),
            {"id": sentinel_id},
        ).scalar_one() == before
    engine.dispose()
