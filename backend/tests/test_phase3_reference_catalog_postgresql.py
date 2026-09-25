"""PostgreSQL 18 qualification for the P3-01 reference catalog."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.models import CargoType, ExpertUser, PackagingType
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.organization_reference_catalog_models import OrganizationCargoTypeActivation
from backend.services.auth_session_service import create_session_tokens


POSTGRES_URL = os.environ.get("P3_REFERENCE_CATALOG_POSTGRES_URL", "")
PREVIOUS = "20260929_operational_monitoring_reliability"
HEAD = "20260930_phase3_reference_catalog"

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires explicit P3_REFERENCE_CATALOG_POSTGRES_URL",
)


def _assert_disposable_postgres_18() -> None:
    parsed = make_url(POSTGRES_URL)
    assert parsed.drivername.startswith("postgresql")
    assert parsed.host in {"127.0.0.1", "localhost"}
    assert (parsed.database or "").startswith(
        "forwarder_integrated_cert_p3_reference_catalog_"
    )
    engine = sa.create_engine(POSTGRES_URL)
    try:
        version = engine.connect().execute(sa.text("SHOW server_version_num")).scalar_one()
        assert int(version) >= 180000
    finally:
        engine.dispose()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_postgresql18_roundtrip_api_lock_audit_and_data_guard():
    _assert_disposable_postgres_18()
    config = alembic_config(POSTGRES_URL)
    command.upgrade(config, HEAD)

    engine = sa.create_engine(POSTGRES_URL)
    inspector = sa.inspect(engine)
    expected = {
        "packaging_type",
        "transport_means_type",
        "transport_equipment_type",
        "organization_cargo_type_activation",
        "organization_unit_of_measure_activation",
        "organization_packaging_type_activation",
        "organization_transport_means_type_activation",
        "organization_transport_equipment_type_activation",
    }
    assert expected <= set(inspector.get_table_names())
    with engine.connect() as connection:
        for table in expected:
            assert connection.execute(sa.text(f'SELECT count(*) FROM "{table}"')).scalar_one() == 0

    command.downgrade(config, PREVIOUS)
    assert "packaging_type" not in sa.inspect(engine).get_table_names()
    command.upgrade(config, HEAD)

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": POSTGRES_URL,
            "SECRET_KEY": "p3-reference-postgresql-qualification",
        },
        skip_startup=True,
    )
    with app.app_context():
        organization = OperationalOrganization(name="P3 PostgreSQL Organization")
        admin = ExpertUser(
            username="p3-postgresql-admin",
            password_hash="unused",
            full_name="P3 PostgreSQL Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        cargo_type = CargoType(
            immutable_code="P3_PG_CARGO",
            fa_name="کالای PostgreSQL",
            en_name="PostgreSQL cargo",
            is_active=True,
        )
        packaging = PackagingType(
            immutable_code="P3_PG_PACKAGE",
            fa_name="بسته PostgreSQL",
            en_name="PostgreSQL package",
            is_active=True,
        )
        db.session.add_all([organization, admin, cargo_type, packaging])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=organization.id,
                user_id=admin.id,
                permissions=[],
            )
        )
        db.session.commit()
        token = create_session_tokens(admin.id)["access_token"]
        cargo_public_id = cargo_type.public_id

    endpoint = (
        "/api/admin/organization-reference-catalog/cargo-types/"
        f"{cargo_public_id}"
    )
    def activate_once():
        with app.test_client() as concurrent_client:
            response = concurrent_client.post(
                f"{endpoint}/activate", headers=_headers(token), json={}
            )
            return response.status_code, response.get_json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        activation_results = list(pool.map(lambda _index: activate_once(), range(2)))
    assert sorted(status for status, _body in activation_results) == [201, 409], activation_results
    created_body = next(body for status, body in activation_results if status == 201)
    conflict_body = next(body for status, body in activation_results if status == 409)
    assert created_body["item"]["activation_version"] == 1
    assert conflict_body["error"]["code"] in {
        "REFERENCE_STATE_UNCHANGED",
        "REFERENCE_ACTIVATION_CONFLICT",
    }

    client = app.test_client()

    changed = client.post(
        f"{endpoint}/deactivate", headers=_headers(token), json={"version": 1}
    )
    assert changed.status_code == 200
    assert changed.get_json()["item"]["activation_version"] == 2
    stale = client.post(
        f"{endpoint}/activate", headers=_headers(token), json={"version": 1}
    )
    assert stale.status_code == 409
    assert stale.get_json()["error"]["code"] == "VERSION_CONFLICT"

    with app.app_context():
        activation = OrganizationCargoTypeActivation.query.one()
        assert activation.status == "INACTIVE"
        assert activation.version == 2
        audit_count = db.session.execute(
            sa.text(
                "SELECT count(*) FROM operational_audit "
                "WHERE entity_type = 'OrganizationCargoTypeActivation'"
            )
        ).scalar_one()
        assert audit_count == 2
        db.session.remove()

    with pytest.raises(RuntimeError, match="Downgrade refused"):
        command.downgrade(config, PREVIOUS)

    with app.app_context():
        OrganizationCargoTypeActivation.query.delete()
        PackagingType.query.delete()
        db.session.commit()
        db.session.remove()

    command.downgrade(config, PREVIOUS)
    command.upgrade(config, HEAD)
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
    engine.dispose()
