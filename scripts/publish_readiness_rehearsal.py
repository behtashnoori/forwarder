"""Disposable end-to-end publish-readiness rehearsal for the frozen Forwarder RC."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import create_app
from backend.auth import auth_manager
from backend.cargo_models import CargoCatalogItem, ShipmentCargoItem
from backend.extensions import db
from backend.external_reference_models import (
    ExternalReferenceType,
    OperationalShipmentExternalReference,
)
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.migration_runtime import alembic_config, prepare_version_table_for_upgrade
from backend.models import (
    CargoType,
    CaseDocumentFile,
    CaseDocumentRequirement,
    Country,
    Customer,
    DocumentDefinition,
    ExpertUser,
    ShipmentRequest,
    UnitOfMeasure,
)
from backend.operational_cli import seed_phase1b_uat
from backend.operational_models import (
    ExecutionUnit,
    OperationalEvent,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
)

from alembic import command


HEAD = "20260903_external_operational_references"
TABLES = (
    "operational_organization", "operational_membership", "expert_user",
    "shipment_request", "project", "operational_shipment", "execution_unit",
    "operational_event", "shipment_cargo_item", "logistics_point",
    "case_document_file", "operational_shipment_external_reference",
)


def _run(command_line: list[str], environment: dict[str, str]) -> None:
    completed = subprocess.run(
        command_line, cwd=ROOT, env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"command failed: {Path(command_line[0]).name}")


def _postgres_binary(name: str) -> str:
    located = shutil.which(name)
    if located:
        return located
    candidate = Path("C:/Program Files/PostgreSQL/18/bin") / f"{name}.exe"
    if candidate.is_file():
        return str(candidate)
    raise RuntimeError(f"required PostgreSQL tool is unavailable: {name}")


def _safe_name(prefix: str, run_id: str) -> str:
    name = f"{prefix}_{run_id}".lower()
    if not name.startswith(("forwarder_rehearsal_", "forwarder_phase1b_uat_")) or len(name) > 63:
        raise RuntimeError("unsafe disposable database name")
    return name


def _manifest(url: str) -> dict[str, object]:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            revision = connection.execute(text("select version_num from alembic_version")).scalar_one()
            counts = {
                table: connection.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one()
                for table in TABLES
            }
            identities = {}
            for table in (
                "operational_organization", "shipment_request", "project",
                "operational_shipment", "execution_unit", "case_document_file",
                "operational_shipment_external_reference",
            ):
                identities[table] = connection.execute(
                    text(f'SELECT public_id::text FROM "{table}" ORDER BY public_id')
                ).scalars().all()
            tracking_codes = connection.execute(
                text("select tracking_code from shipment_request where tracking_code is not null order by tracking_code")
            ).scalars().all()
            relationships = {
                "request_project": connection.execute(text(
                    "select count(*) from shipment_request where project_id is not null"
                )).scalar_one(),
                "shipment_project": connection.execute(text(
                    "select count(*) from operational_shipment where project_id is not null"
                )).scalar_one(),
                "unit_shipment": connection.execute(text(
                    "select count(*) from execution_unit where operational_shipment_id is not null"
                )).scalar_one(),
                "document_request": connection.execute(text(
                    "select count(*) from case_document_file where shipment_request_id is not null"
                )).scalar_one(),
            }
            payload = {
                "revision": revision, "counts": counts, "identities": identities,
                "tracking_codes": tracking_codes, "relationships": relationships,
            }
            digest = hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode("utf-8")
            ).hexdigest()
            return {**payload, "sha256": digest}
    finally:
        engine.dispose()


def _seed(url: str) -> dict[str, str]:
    os.environ.update({"DATABASE_URL": url, "APP_ENV": "uat"})
    app = create_app({"SQLALCHEMY_DATABASE_URI": url}, skip_startup=True)
    with app.app_context():
        seed_phase1b_uat(app, "disposable-local-rehearsal-only")
        org = OperationalOrganization.query.filter_by(
            name="[PHASE1B-UAT] Organization A"
        ).one()
        other_org = OperationalOrganization.query.filter_by(
            name="[PHASE1B-UAT] Organization B"
        ).one()
        actor = ExpertUser.query.filter_by(username="phase1b_uat_admin").one()
        outsider = ExpertUser.query.filter_by(username="phase1b_uat_org_b_admin").one()
        request = ShipmentRequest.query.filter_by(contact_phone="09000000201").one()
        shipment = OperationalShipment.query.filter_by(organization_id=org.id).one()
        customer = Customer(
            first_name="Rehearsal", last_name="Customer", status="active",
            ownership_scope="TENANT", operational_organization_id=org.id,
        )
        db.session.add(customer)
        db.session.flush()
        project = Project(
            organization_id=org.id, primary_customer_id=customer.id,
            project_code="PUBLISH-REHEARSAL", tracking_code="publish-rehearsal-project",
            created_by_user_id=actor.id,
        )
        db.session.add(project)
        db.session.flush()
        request.customer_id = customer.id
        request.project_id = project.id
        request.tracking_code = request.tracking_code or "PUBLISH-REHEARSAL-REQUEST"
        shipment.customer_id = customer.id
        shipment.project_id = project.id
        unit = ExecutionUnit(
            project_id=project.id, operational_shipment_id=shipment.id,
            unit_code="PUBLISH-UNIT-1", unit_type="truck",
            lifecycle_status="in_progress", latest_checkpoint="Rehearsal checkpoint",
            created_by_user_id=actor.id,
        )
        db.session.add(unit)
        db.session.flush()
        event = OperationalEvent(
            project_id=project.id, execution_unit_id=unit.id,
            event_type="checkpoint", checkpoint_text="Rehearsal checkpoint",
            occurred_at=datetime(2026, 8, 21, 4, 0, tzinfo=timezone.utc),
            actor_user_id=actor.id,
            idempotency_key="publish-rehearsal-event", request_hash="a" * 64,
        )
        db.session.add(event)

        cargo_type = CargoType.query.filter_by(immutable_code="PUBLISH_GENERAL").one_or_none()
        if cargo_type is None:
            cargo_type = CargoType(
                immutable_code="PUBLISH_GENERAL", fa_name="کالای تمرینی",
                en_name="Rehearsal cargo", display_order=999, is_active=True,
            )
            db.session.add(cargo_type)
        uom = UnitOfMeasure.query.filter_by(immutable_code="PUBLISH_EA").one_or_none()
        if uom is None:
            uom = UnitOfMeasure(
                immutable_code="PUBLISH_EA", fa_name="عدد", en_name="Each",
                symbol="ea", measurement_dimension="COUNT", display_order=999,
                is_active=True,
            )
            db.session.add(uom)
        db.session.flush()
        catalog = CargoCatalogItem(
            organization_id=org.id, immutable_code="PUBLISH-CARGO",
            fa_name="کالای تمرینی", en_name="Rehearsal cargo",
            cargo_type=cargo_type, default_uom=uom,
            created_by=actor.id, updated_by=actor.id,
        )
        db.session.add(catalog)
        db.session.flush()
        db.session.add(ShipmentCargoItem(
            operational_shipment_id=shipment.id, line_number=1,
            catalog_item=catalog, cargo_type=cargo_type, quantity="2", uom=uom,
            display_name_snapshot="Rehearsal cargo",
            cargo_type_code_snapshot=cargo_type.immutable_code,
            cargo_type_fa_snapshot=cargo_type.fa_name,
            cargo_type_en_snapshot=cargo_type.en_name,
            uom_code_snapshot=uom.immutable_code, uom_symbol_snapshot=uom.symbol,
            created_by=actor.id, updated_by=actor.id,
        ))

        country = Country.query.first()
        point_type = LogisticsPointType(
            immutable_code="PUBLISH_WAREHOUSE", fa_name="انبار تمرینی",
            en_name="Rehearsal warehouse", display_order=999,
            created_by=actor.id, updated_by=actor.id,
        )
        db.session.add(point_type)
        db.session.flush()
        db.session.add(LogisticsPoint(
            organization_id=org.id, immutable_code="PUBLISH-POINT",
            logistics_point_type_id=point_type.id, fa_name="نقطه تمرینی",
            normalized_name="نقطه تمرینی", en_name="Rehearsal point",
            country_id=country.id, geography_key=f"country:{country.id}",
            created_by=actor.id, updated_by=actor.id,
        ))

        definition = DocumentDefinition(
            code="PUBLISH_REHEARSAL_DOC", title="Publish rehearsal document",
            allowed_formats='["pdf"]', max_file_size_bytes=1000,
        )
        db.session.add(definition)
        db.session.flush()
        requirement = CaseDocumentRequirement(
            operational_organization_id=org.id, shipment_request_id=request.id,
            source_definition_id=definition.id,
            source_definition_code=definition.code, source_definition_revision=1,
            title=definition.title, is_required=True, allowed_formats='["pdf"]',
            max_file_size_bytes=1000, max_active_file_count=1, sort_order=999,
        )
        db.session.add(requirement)
        db.session.flush()
        document = CaseDocumentFile(
            operational_organization_id=org.id, shipment_request_id=request.id,
            case_requirement_id=requirement.id, is_miscellaneous=False,
            original_filename="rehearsal.pdf", safe_download_filename="rehearsal.pdf",
            storage_key="publish-rehearsal/rehearsal.pdf", canonical_extension="pdf",
            detected_mime_type="application/pdf", file_size_bytes=1,
            sha256_hash="b" * 64, version_number=1, uploaded_by=actor.id,
        )
        db.session.add(document)
        db.session.flush()
        reference_type = ExternalReferenceType(
            code="BILL_OF_LADING_NUMBER", name_fa="شماره بارنامه دریایی",
            name_en="Bill of Lading Number", lifecycle_status="ACTIVE",
            search_policy="PREFIX", uniqueness_scope="OWNER",
            source_authority="UN/CEFACT", provenance_reference="UN/EDIFACT 1153 BM",
            allows_operational_shipment=True, allows_execution_unit=False,
            created_by_user_id=actor.id, updated_by_user_id=actor.id,
        )
        db.session.add(reference_type)
        db.session.flush()
        db.session.add(OperationalShipmentExternalReference(
            organization_id=org.id, operational_shipment_id=shipment.id,
            external_reference_type_id=reference_type.id,
            raw_value="PUBLISH-BL-001", normalized_value="PUBLISH-BL-001",
            evidence_document_file_id=document.id, evidence_version=1,
            created_by_user_id=actor.id, updated_by_user_id=actor.id,
        ))
        membership = OperationalMembership.query.filter_by(
            organization_id=org.id, user_id=actor.id
        ).one()
        membership.permissions = sorted(set(membership.permissions or []) | {
            "cargo.read", "logistics_point.read", "execution_unit.read",
        })
        db.session.commit()
        return {
            "actor": str(actor.id), "outsider": str(outsider.id),
            "request": request.public_id, "project": project.public_id,
            "shipment": shipment.public_id, "unit": unit.public_id,
            "catalog": catalog.public_id, "other_org": str(other_org.id),
        }


def _smoke(url: str, identities: dict[str, str]) -> dict[str, int]:
    os.environ.update({"DATABASE_URL": url, "APP_ENV": "uat"})
    app = create_app({"SQLALCHEMY_DATABASE_URI": url}, skip_startup=True)
    with app.app_context():
        actor_token = auth_manager.generate_tokens(int(identities["actor"]))["access_token"]
        outsider_token = auth_manager.generate_tokens(int(identities["outsider"]))["access_token"]
    client = app.test_client()
    owner = {"Authorization": f"Bearer {actor_token}"}
    outsider = {"Authorization": f"Bearer {outsider_token}"}
    results = {
        "health": client.get("/api/health").status_code,
        "readiness": client.get("/api/health/ready").status_code,
        "request_list": client.get("/api/expert/requests", headers=owner).status_code,
        "request_detail": client.get(f"/api/expert/requests/{identities['request']}", headers=owner).status_code,
        "shipment": client.get(f"/api/operational-shipments/{identities['shipment']}", headers=owner).status_code,
        "cross_tenant": client.get(f"/api/operational-shipments/{identities['shipment']}", headers=outsider).status_code,
        "cargo": client.get(f"/api/internal/operational-shipments/{identities['shipment']}/cargo-items", headers=owner).status_code,
        "external_references": client.get(f"/api/internal/operational-shipments/{identities['shipment']}/external-references", headers=owner).status_code,
    }
    if any(code != 200 for name, code in results.items() if name != "cross_tenant"):
        raise RuntimeError(f"smoke failure: {results}")
    if results["cross_tenant"] not in {403, 404}:
        raise RuntimeError(f"cross-tenant smoke failure: {results['cross_tenant']}")
    return results


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    base = make_url(os.environ["DATABASE_URL"])
    if base.get_backend_name() != "postgresql" or base.host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("rehearsal requires loopback PostgreSQL")
    run_id = "20260821" + uuid4().hex[:8]
    target_name = _safe_name("forwarder_phase1b_uat_rehearsal", run_id)
    restore_name = _safe_name("forwarder_rehearsal_restore", run_id)
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    backup = ROOT / ".codex" / f"{run_id}-publish-rehearsal.dump"
    backup.parent.mkdir(exist_ok=True)
    result: dict[str, object] = {"run_id": run_id, "candidate_head": os.popen("git rev-parse HEAD").read().strip()}
    names = (target_name, restore_name)

    def drop(name: str) -> None:
        with admin.connect() as connection:
            connection.execute(text(
                "select pg_terminate_backend(pid) from pg_stat_activity where datname=:name and pid<>pg_backend_pid()"
            ), {"name": name})
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))

    def create(name: str) -> str:
        drop(name)
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}" ENCODING \'UTF8\''))
        return base.set(database=name).render_as_string(hide_password=False)

    started = time.monotonic()
    try:
        target_url = create(target_name)
        cfg = alembic_config(target_url)
        prepare_version_table_for_upgrade(target_url, cfg)
        migration_started = time.monotonic()
        command.upgrade(cfg, "head")
        result["migration_seconds"] = round(time.monotonic() - migration_started, 3)
        identities = _seed(target_url)
        before = _manifest(target_url)
        if before["revision"] != HEAD:
            raise RuntimeError("unexpected migration head")
        result["initial_manifest"] = before
        result["initial_smoke"] = _smoke(target_url, identities)

        environment = os.environ.copy()
        environment["PGPASSWORD"] = base.password or ""
        dump = _postgres_binary("pg_dump")
        restore = _postgres_binary("pg_restore")
        _run([dump, "-Fc", "-h", base.host or "127.0.0.1", "-p", str(base.port or 5432),
              "-U", base.username or "postgres", "-d", target_name, "-f", str(backup)], environment)
        _run([restore, "--list", str(backup)], environment)
        result["backup_size_bytes"] = backup.stat().st_size
        result["backup_sha256"] = hashlib.sha256(backup.read_bytes()).hexdigest()

        restore_url = create(restore_name)
        _run([restore, "--no-owner", "--no-privileges", "-h", base.host or "127.0.0.1",
              "-p", str(base.port or 5432), "-U", base.username or "postgres",
              "-d", restore_name, str(backup)], environment)
        restored = _manifest(restore_url)
        if restored != before:
            raise RuntimeError("restored integrity manifest differs")
        result["restore_manifest"] = restored
        result["restore_smoke"] = _smoke(restore_url, identities)

        # Simulate target loss and prove database/application recovery from backup.
        drop(target_name)
        target_url = create(target_name)
        _run([restore, "--no-owner", "--no-privileges", "-h", base.host or "127.0.0.1",
              "-p", str(base.port or 5432), "-U", base.username or "postgres",
              "-d", target_name, str(backup)], environment)
        recovered = _manifest(target_url)
        if recovered != before:
            raise RuntimeError("disaster recovery manifest differs")
        result["recovery_smoke"] = _smoke(target_url, identities)

        # Re-deployability: explicit migration reapplication must converge without mutation.
        cfg = alembic_config(target_url)
        prepare_version_table_for_upgrade(target_url, cfg)
        command.upgrade(cfg, "head")
        redeployed = _manifest(target_url)
        if redeployed != before:
            raise RuntimeError("redeployment changed representative data")
        result["redeploy_smoke"] = _smoke(target_url, identities)
        result["recovery_strategy"] = "application/config rollback plus certified pg_restore; no blind Alembic downgrade"
        result["status"] = "PASS"
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        for name in names:
            drop(name)
        admin.dispose()
        if backup.exists():
            backup.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
