"""Certify the approved Global Logistics Point importer on disposable PostgreSQL 18."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--admin-url", default=os.getenv("DATABASE_URL"), required=False
    )
    args = parser.parse_args(argv)
    if not args.admin_url:
        raise SystemExit("--admin-url or DATABASE_URL is required")
    base = make_url(args.admin_url)
    if base.get_backend_name() != "postgresql" or base.host not in {
        "127.0.0.1",
        "localhost",
    }:
        raise SystemExit("refusing: loopback PostgreSQL is required")
    name = "global_point_importer_cert_" + uuid4().hex[:12]
    if not re.fullmatch(r"global_point_importer_cert_[0-9a-f]{12}", name):
        raise SystemExit("unsafe disposable database name")
    admin_url = base.set(database="postgres")
    target_url = base.set(database=name)
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    quoted = admin.dialect.identifier_preparer.quote(name)
    with admin.connect() as connection:
        version = connection.execute(text("SHOW server_version_num")).scalar_one()
        if not str(version).startswith("18"):
            raise SystemExit(f"PostgreSQL 18 required; found {version}")
        connection.execute(text(f"CREATE DATABASE {quoted}"))
    target = create_engine(target_url)
    try:
        rendered = target_url.render_as_string(hide_password=False)
        os.environ.update({"DATABASE_URL": rendered, "APP_ENV": "uat"})
        from alembic import command
        from backend.migration_runtime import (
            alembic_config,
            prepare_version_table_for_upgrade,
        )

        config = alembic_config(rendered)
        prepare_version_table_for_upgrade(rendered, config)
        command.upgrade(config, "20260906_global_logistics_point_materialization")

        from backend import create_app
        from backend.extensions import db
        from backend.global_logistics_point_catalog import (
            apply_catalog,
            load_catalog,
            plan_catalog,
        )
        from backend.global_logistics_point_models import GlobalLogisticsPoint
        from backend.logistics_network_models import LogisticsPointType
        from backend.models import Country, ExpertUser, ReferenceDataSeedRun

        app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": rendered,
                "SECRET_KEY": "disposable-global-importer-cert",
            },
            skip_startup=True,
        )
        with app.app_context():
            actor = ExpertUser(
                id=26,
                username="platformadmin",
                password_hash="x",
                full_name="Platform Admin",
                role="admin",
                authority="PLATFORM_ADMIN",
                is_active=True,
            )
            db.session.add(actor)
            db.session.flush()
            catalog = load_catalog()
            required_countries = sorted(
                {x["runtime_candidate"]["country_code"] for x in catalog.rows}
            )
            existing_countries = {x.code for x in Country.query.all()}
            db.session.add_all(
                [
                    Country(code=code, name_en=code, name_fa=code)
                    for code in required_countries
                    if code not in existing_countries
                ]
            )
            required_types = sorted(
                {x["runtime_candidate"]["point_type_code"] for x in catalog.rows}
            )
            existing_types = {x.immutable_code for x in LogisticsPointType.query.all()}
            db.session.add_all(
                [
                    LogisticsPointType(
                        immutable_code=code,
                        fa_name=code,
                        en_name=code,
                        definition="Disposable certification prerequisite",
                        display_order=index,
                        created_by=actor.id,
                        updated_by=actor.id,
                    )
                    for index, code in enumerate(required_types)
                    if code not in existing_types
                ]
            )
            db.session.commit()
            fresh = plan_catalog(catalog, "uat")
            applied, run = apply_catalog(
                catalog,
                environment="uat",
                operator="platformadmin",
                approval_reference="LOCAL-POSTGRES-18-CERTIFICATION",
                expected_checksum=catalog.checksum,
                user_id=26,
            )
            converged = plan_catalog(catalog, "uat")
            repeated, repeated_run = apply_catalog(
                catalog,
                environment="uat",
                operator="platformadmin",
                approval_reference="LOCAL-POSTGRES-18-CERTIFICATION",
                expected_checksum=catalog.checksum,
                user_id=26,
            )
            assert (
                fresh.created_count,
                fresh.unchanged_count,
                fresh.conflict_count,
            ) == (9, 0, 0)
            assert (
                converged.created_count,
                converged.unchanged_count,
                converged.conflict_count,
            ) == (0, 9, 0)
            assert (
                run.status == repeated_run.status == "succeeded"
                and repeated.created_count == 0
            )
            assert GlobalLogisticsPoint.query.count() == 9
            assert {x.lifecycle_status for x in GlobalLogisticsPoint.query.all()} == {
                "DRAFT"
            }
            assert {
                x.verification_status for x in GlobalLogisticsPoint.query.all()
            } == {"UNVERIFIED"}
            row = GlobalLogisticsPoint.query.filter_by(
                immutable_code="GLP-IR-SARAKHS"
            ).one()
            row.en_name = "Conflict certification"
            db.session.commit()
            conflict, refused = apply_catalog(
                catalog,
                environment="uat",
                operator="platformadmin",
                approval_reference="LOCAL-POSTGRES-18-CERTIFICATION",
                expected_checksum=catalog.checksum,
                user_id=26,
            )
            assert conflict.conflict_count == 1 and refused.status == "refused"
            assert (
                ReferenceDataSeedRun.query.count() == 3
                and GlobalLogisticsPoint.query.count() == 9
            )
            health = app.test_client().get("/api/health")
            readiness = app.test_client().get("/api/health/ready")
            result = {
                "postgresql": version,
                "database": name,
                "migration_head": "20260906_global_logistics_point_materialization",
                "fresh_plan": fresh.as_dict(),
                "apply_status": run.status,
                "parent_count": 9,
                "post_apply_plan": converged.as_dict(),
                "idempotent_status": repeated_run.status,
                "conflict_count": conflict.conflict_count,
                "conflict_status": refused.status,
                "evidence_count": 3,
                "health_status": health.status_code,
                "readiness_status": readiness.status_code,
            }
            print(json.dumps(result, sort_keys=True))
        return 0
    finally:
        target.dispose()
        with admin.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name"
                ),
                {"name": name},
            )
            connection.execute(text(f"DROP DATABASE IF EXISTS {quoted}"))
        admin.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
