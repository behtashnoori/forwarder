"""Focused P3-01 backend contract, authorization, and migration evidence."""

from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa

from backend import create_app
from backend.cargo_models import CargoCatalogItem, ShipmentCargoItem
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import (
    CargoType,
    Customer,
    ExpertUser,
    PackagingType,
    TransportEquipmentType,
    TransportMeansType,
    UnitOfMeasure,
)
from backend.operational_models import (
    OperationalAudit,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
)
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
)
from backend.services.auth_session_service import create_session_tokens


PREVIOUS = "20260929_operational_monitoring_reliability"
HEAD = "20260930_phase3_reference_catalog"
REPOSITORY_HEAD = "20261002_phase3_branched_route"
BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def reference_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "phase3-reference-catalog",
        }
    )
    with app.app_context():
        org_a = OperationalOrganization(name="Reference Org A")
        org_b = OperationalOrganization(name="Reference Org B")
        platform = ExpertUser(
            username="reference-platform",
            password_hash="unused",
            full_name="Platform Admin",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        admin_a = ExpertUser(
            username="reference-admin-a",
            password_hash="unused",
            full_name="Organization Admin A",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        admin_b = ExpertUser(
            username="reference-admin-b",
            password_hash="unused",
            full_name="Organization Admin B",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        expert = ExpertUser(
            username="reference-expert-a",
            password_hash="unused",
            full_name="Expert A",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        db.session.add_all([org_a, org_b, platform, admin_a, admin_b, expert])
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org_a.id,
                    user_id=admin_a.id,
                    permissions=[],
                ),
                OperationalMembership(
                    organization_id=org_b.id,
                    user_id=admin_b.id,
                    permissions=[],
                ),
                OperationalMembership(
                    organization_id=org_a.id,
                    user_id=expert.id,
                    permissions=[
                        "operational_shipment.read",
                        "operational_shipment.create",
                    ],
                ),
            ]
        )
        cargo_type = CargoType(
            immutable_code="P3_GENERAL",
            fa_name="کالای عمومی",
            en_name="General cargo",
            display_order=1,
            is_active=True,
        )
        unselected_cargo_type = CargoType(
            immutable_code="P3_UNSELECTED",
            fa_name="انتخاب‌نشده",
            en_name="Unselected",
            display_order=2,
            is_active=True,
        )
        uom = UnitOfMeasure(
            immutable_code="P3_EA",
            fa_name="عدد",
            en_name="Each",
            display_order=1,
            is_active=True,
            symbol="ea",
            measurement_dimension="COUNT",
        )
        unselected_uom = UnitOfMeasure(
            immutable_code="P3_KG",
            fa_name="کیلوگرم",
            en_name="Kilogram",
            display_order=2,
            is_active=True,
            symbol="kg",
            measurement_dimension="WEIGHT",
        )
        inactive_packaging = PackagingType(
            immutable_code="P3_INACTIVE_PACKAGE",
            fa_name="بسته‌بندی غیرفعال",
            en_name="Inactive packaging",
            is_active=False,
        )
        db.session.add_all(
            [cargo_type, unselected_cargo_type, uom, unselected_uom, inactive_packaging]
        )
        db.session.commit()

        users = {
            "platform": platform,
            "admin_a": admin_a,
            "admin_b": admin_b,
            "expert": expert,
        }
        tokens = {
            name: create_session_tokens(user.id)["access_token"]
            for name, user in users.items()
        }
        yield app, {
            "org_a": org_a.id,
            "org_b": org_b.id,
            "users": {name: user.id for name, user in users.items()},
            "tokens": tokens,
            "cargo_type": cargo_type.public_id,
            "unselected_cargo_type": unselected_cargo_type.public_id,
            "uom": uom.public_id,
            "unselected_uom": unselected_uom.public_id,
            "inactive_packaging": inactive_packaging.public_id,
        }
        db.session.remove()
        db.drop_all()


def test_new_central_families_are_explicit_platform_admin_resources(reference_app):
    app, ctx = reference_app
    client = app.test_client()
    assert PackagingType.query.count() == 1
    assert TransportMeansType.query.count() == 0
    assert TransportEquipmentType.query.count() == 0

    payloads = {
        "packaging-types": "P3_BOX",
        "transport-means-types": "P3_TRUCK",
        "transport-equipment-types": "P3_CONTAINER",
    }
    for resource, code in payloads.items():
        response = client.post(
            f"/api/admin/master-data/{resource}",
            headers=_headers(ctx["tokens"]["platform"]),
            json={
                "immutable_code": code,
                "fa_name": "نام فارسی",
                "en_name": "English name",
                "display_order": 3,
            },
        )
        assert response.status_code == 201, response.get_json()
        assert response.get_json()["item"]["immutable_code"] == code

    forbidden = client.post(
        "/api/admin/master-data/packaging-types",
        headers=_headers(ctx["tokens"]["admin_a"]),
        json={
            "immutable_code": "ORG_ONLY",
            "fa_name": "سازمانی",
            "en_name": "Organization only",
        },
    )
    assert forbidden.status_code == 403
    assert client.post(
        "/api/admin/master-data/packaging-types",
        headers=_headers(ctx["tokens"]["expert"]),
        json={"immutable_code": "EXPERT", "fa_name": "الف", "en_name": "Expert"},
    ).status_code == 403
    assert PackagingType.query.filter_by(immutable_code="ORG_ONLY").first() is None


def test_activation_lifecycle_tenant_roles_direct_identity_lock_and_audit(reference_app):
    app, ctx = reference_app
    client = app.test_client()
    base = "/api/admin/organization-reference-catalog/cargo-types"
    admin_a = _headers(ctx["tokens"]["admin_a"])

    initial = client.get(base, headers=admin_a)
    assert initial.status_code == 200
    item = next(
        row for row in initial.get_json()["items"]
        if row["public_id"] == ctx["cargo_type"]
    )
    assert item["code"] == "P3_GENERAL"
    assert item["organization_active"] is False
    assert item["selectable"] is False
    assert item["activation_public_id"] is None
    assert item["activation_version"] is None
    assert item["origin"] == "CENTRAL_SYSTEM"
    assert "id" not in item and "immutable_code" not in item

    created = client.post(
        f"{base}/{ctx['cargo_type']}/activate", headers=admin_a, json={}
    )
    assert created.status_code == 201, created.get_json()
    activated = created.get_json()["item"]
    assert activated["organization_active"] is True
    assert activated["selectable"] is True
    assert activated["activation_version"] == 1

    stale = client.post(
        f"{base}/{ctx['cargo_type']}/deactivate",
        headers=admin_a,
        json={"version": 0},
    )
    assert stale.status_code == 409
    assert stale.get_json()["error"]["code"] == "VERSION_CONFLICT"

    deactivated = client.post(
        f"{base}/{ctx['cargo_type']}/deactivate",
        headers=admin_a,
        json={"version": 1},
    )
    assert deactivated.status_code == 200
    assert deactivated.get_json()["item"]["activation_version"] == 2
    assert deactivated.get_json()["item"]["organization_active"] is False
    assert OrganizationCargoTypeActivation.query.count() == 1

    reactivated = client.post(
        f"{base}/{ctx['cargo_type']}/activate",
        headers=admin_a,
        json={"version": 2},
    )
    assert reactivated.status_code == 200
    assert reactivated.get_json()["item"]["activation_version"] == 3

    foreign_list = client.get(
        base, headers=_headers(ctx["tokens"]["admin_b"])
    ).get_json()["items"]
    foreign_item = next(
        row for row in foreign_list if row["public_id"] == ctx["cargo_type"]
    )
    assert foreign_item["organization_active"] is False
    assert foreign_item["activation_public_id"] is None

    foreign_config_id = client.post(
        f"{base}/{activated['activation_public_id']}/deactivate",
        headers=_headers(ctx["tokens"]["admin_b"]),
        json={"version": 3},
    )
    assert foreign_config_id.status_code == 404
    assert foreign_config_id.get_json()["error"]["code"] == "REFERENCE_DEFINITION_NOT_FOUND"

    assert client.get(base, headers=_headers(ctx["tokens"]["platform"])).status_code == 403
    assert client.get(base, headers=_headers(ctx["tokens"]["expert"])).status_code == 403
    assert client.post(
        f"{base}/{ctx['cargo_type']}/deactivate",
        headers=_headers(ctx["tokens"]["platform"]),
        json={"version": 3},
    ).status_code == 403

    direct_id = client.post(f"{base}/1/activate", headers=admin_a, json={})
    assert direct_id.status_code == 404
    assert direct_id.get_json()["error"]["code"] == "REFERENCE_DEFINITION_NOT_FOUND"

    with app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=ctx["users"]["admin_a"], organization_id=ctx["org_a"]
        ).one()
        membership.is_active = False
        db.session.commit()
    assert client.get(base, headers=admin_a).status_code == 403
    with app.app_context():
        membership = OperationalMembership.query.filter_by(
            user_id=ctx["users"]["admin_a"], organization_id=ctx["org_a"]
        ).one()
        membership.is_active = True
        db.session.commit()

    inactive = client.post(
        "/api/admin/organization-reference-catalog/packaging-types/"
        f"{ctx['inactive_packaging']}/activate",
        headers=admin_a,
        json={},
    )
    assert inactive.status_code == 409
    assert inactive.get_json()["error"]["code"] == "CENTRAL_REFERENCE_INACTIVE"

    with app.app_context():
        events = OperationalAudit.query.filter_by(
            organization_id=ctx["org_a"],
            entity_type="OrganizationCargoTypeActivation",
        ).order_by(OperationalAudit.id).all()
        assert [event.metadata_json["previous_state"] for event in events] == [
            None,
            "ACTIVE",
            "INACTIVE",
        ]
        assert [event.metadata_json["current_state"] for event in events] == [
            "ACTIVE",
            "INACTIVE",
            "ACTIVE",
        ]
        assert all(
            event.metadata_json["definition_public_id"] == ctx["cargo_type"]
            for event in events
        )


def test_cargo_new_use_requires_org_activation_but_history_remains_readable(reference_app):
    app, ctx = reference_app
    client = app.test_client()
    admin = _headers(ctx["tokens"]["admin_a"])
    expert = _headers(ctx["tokens"]["expert"])
    org_base = "/api/admin/organization-reference-catalog"

    assert client.post(
        f"{org_base}/cargo-types/{ctx['cargo_type']}/activate",
        headers=admin,
        json={},
    ).status_code == 201

    missing_uom = client.post(
        "/api/internal/cargo-catalog",
        headers=admin,
        json={
            "immutable_code": "P3-CATALOG",
            "fa_name": "کالای کاتالوگ",
            "cargo_type_public_id": ctx["cargo_type"],
            "default_uom_public_id": ctx["uom"],
        },
    )
    assert missing_uom.status_code == 409
    assert missing_uom.get_json()["error"] == {
        "code": "ORGANIZATION_REFERENCE_NOT_ACTIVE",
        "message": "این نوع در تعاریف سازمان موجود نیست. برای ادامه، مدیر سازمان باید آن را تعریف یا فعال کند.",
    }

    assert client.post(
        f"{org_base}/units-of-measure/{ctx['uom']}/activate",
        headers=admin,
        json={},
    ).status_code == 201
    created_catalog = client.post(
        "/api/internal/cargo-catalog",
        headers=admin,
        json={
            "immutable_code": "P3-CATALOG",
            "fa_name": "کالای کاتالوگ",
            "cargo_type_public_id": ctx["cargo_type"],
            "default_uom_public_id": ctx["uom"],
        },
    )
    assert created_catalog.status_code == 201, created_catalog.get_json()
    catalog = created_catalog.get_json()["item"]

    options = client.get("/api/internal/cargo-options", headers=expert)
    assert options.status_code == 200
    assert [row["public_id"] for row in options.get_json()["cargo_types"]] == [
        ctx["cargo_type"]
    ]
    assert [row["public_id"] for row in options.get_json()["uoms"]] == [ctx["uom"]]
    assert ctx["unselected_cargo_type"] not in {
        row["public_id"] for row in options.get_json()["cargo_types"]
    }
    assert ctx["unselected_uom"] not in {
        row["public_id"] for row in options.get_json()["uoms"]
    }

    with app.app_context():
        customer = Customer(
            operational_organization_id=ctx["org_a"],
            ownership_scope="TENANT",
            company_name="Reference Customer",
            status="active",
        )
        db.session.add(customer)
        db.session.flush()
        shipment = OperationalShipment(
            organization_id=ctx["org_a"],
            source_type="direct",
            customer_id=customer.id,
            created_by_user_id=ctx["users"]["expert"],
            primary_responsible_expert_id=ctx["users"]["expert"],
        )
        db.session.add(shipment)
        db.session.commit()
        shipment_public_id = shipment.public_id

    created_line = client.post(
        f"/api/internal/operational-shipments/{shipment_public_id}/cargo-items",
        headers=expert,
        json={
            "line_number": 1,
            "catalog_item_public_id": catalog["public_id"],
            "cargo_type_public_id": ctx["cargo_type"],
            "uom_public_id": ctx["uom"],
            "quantity": "5",
        },
    )
    assert created_line.status_code == 201, created_line.get_json()
    original_snapshot = created_line.get_json()["item"]

    deactivated = client.post(
        f"{org_base}/cargo-types/{ctx['cargo_type']}/deactivate",
        headers=admin,
        json={"version": 1},
    )
    assert deactivated.status_code == 200

    filtered = client.get("/api/internal/cargo-options", headers=expert).get_json()
    assert filtered["cargo_types"] == []
    assert [row["public_id"] for row in filtered["uoms"]] == [ctx["uom"]]

    rejected_catalog = client.post(
        "/api/internal/cargo-catalog",
        headers=admin,
        json={
            "immutable_code": "P3-CATALOG-2",
            "fa_name": "کالای دوم",
            "cargo_type_public_id": ctx["cargo_type"],
        },
    )
    assert rejected_catalog.status_code == 409
    assert rejected_catalog.get_json()["error"]["code"] == "ORGANIZATION_REFERENCE_NOT_ACTIVE"

    rejected_update = client.patch(
        f"/api/internal/cargo-catalog/{catalog['public_id']}",
        headers=admin,
        json={
            "cargo_type_public_id": ctx["cargo_type"],
            "version": catalog["version"],
        },
    )
    assert rejected_update.status_code == 409
    assert rejected_update.get_json()["error"]["code"] == "ORGANIZATION_REFERENCE_NOT_ACTIVE"

    rejected_line = client.post(
        f"/api/internal/operational-shipments/{shipment_public_id}/cargo-items",
        headers=expert,
        json={
            "line_number": 2,
            "cargo_type_public_id": ctx["cargo_type"],
            "uom_public_id": ctx["uom"],
            "quantity": "1",
            "display_name": "کالای دستی",
        },
    )
    assert rejected_line.status_code == 409
    assert rejected_line.get_json()["error"]["code"] == "ORGANIZATION_REFERENCE_NOT_ACTIVE"

    historical = client.get(
        f"/api/internal/operational-shipments/{shipment_public_id}/cargo-items",
        headers=expert,
    )
    assert historical.status_code == 200
    retained = historical.get_json()["items"][0]
    assert retained["public_id"] == original_snapshot["public_id"]
    assert retained["display_name_snapshot"] == original_snapshot["display_name_snapshot"]
    assert retained["cargo_type_code_snapshot"] == "P3_GENERAL"
    assert retained["uom_code_snapshot"] == "P3_EA"
    with app.app_context():
        assert ShipmentCargoItem.query.count() == 1
        assert CargoCatalogItem.query.count() == 1


def _migration_parent_schema(url):
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    sa.Table(
        "operational_organization", metadata, sa.Column("id", BIGINT, primary_key=True)
    )
    sa.Table("expert_user", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("cargo_type", metadata, sa.Column("id", BIGINT, primary_key=True))
    sa.Table("unit_of_measure", metadata, sa.Column("id", BIGINT, primary_key=True))
    metadata.create_all(engine)
    return engine


def test_phase3_migration_is_single_head_seed_free_roundtrip_and_guarded(tmp_path):
    config = alembic_config("sqlite://")
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == [REPOSITORY_HEAD]
    assert script.get_revision(HEAD).down_revision == PREVIOUS

    source = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260930_phase3_reference_catalog.py"
    ).read_text(encoding="utf-8")
    assert "INSERT INTO" not in source
    assert "bulk_insert" not in source
    assert "Downgrade refused" in source

    url = f"sqlite:///{(tmp_path / 'p3-reference-roundtrip.db').as_posix()}"
    engine = _migration_parent_schema(url)
    config = alembic_config(url)
    command.stamp(config, PREVIOUS)
    command.upgrade(config, HEAD)
    tables = set(sa.inspect(engine).get_table_names())
    assert {
        "packaging_type",
        "transport_means_type",
        "transport_equipment_type",
        "organization_cargo_type_activation",
        "organization_unit_of_measure_activation",
        "organization_packaging_type_activation",
        "organization_transport_means_type_activation",
        "organization_transport_equipment_type_activation",
    } <= tables
    command.downgrade(config, PREVIOUS)
    assert "packaging_type" not in sa.inspect(engine).get_table_names()
    command.upgrade(config, HEAD)
    assert "packaging_type" in sa.inspect(engine).get_table_names()
    engine.dispose()

    guarded_url = f"sqlite:///{(tmp_path / 'p3-reference-guard.db').as_posix()}"
    guarded_engine = _migration_parent_schema(guarded_url)
    guarded_config = alembic_config(guarded_url)
    command.stamp(guarded_config, PREVIOUS)
    command.upgrade(guarded_config, HEAD)
    with guarded_engine.begin() as connection:
        connection.execute(sa.text("INSERT INTO operational_organization (id) VALUES (1)"))
        connection.execute(sa.text("INSERT INTO expert_user (id) VALUES (1)"))
        connection.execute(sa.text("INSERT INTO cargo_type (id) VALUES (1)"))
        connection.execute(
            sa.text(
                "INSERT INTO organization_cargo_type_activation "
                "(id, public_id, organization_id, cargo_type_id, status, version, "
                "created_at, updated_at, created_by, updated_by) VALUES "
                "(1, '11111111-1111-4111-8111-111111111111', 1, 1, 'ACTIVE', 1, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1, 1)"
            )
        )
    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(guarded_config, PREVIOUS)
    guarded_engine.dispose()
