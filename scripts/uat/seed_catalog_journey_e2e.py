"""Extend the disposable Shared Transport fixture with one catalog master item.

The operational cargo line is deliberately *not* seeded: the browser journey
creates it through the product UI.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.cargo_models import CargoCatalogItem
from backend.extensions import db
from backend.models import CargoType, ExpertUser, UnitOfMeasure
from backend.operational_models import Project
from backend.organization_reference_catalog_models import (
    OrganizationCargoTypeActivation,
    OrganizationUnitOfMeasureActivation,
)
from scripts.uat.seed_shared_transport_e2e import main as seed_shared_transport


def main() -> None:
    seed_shared_transport()
    manifest = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(manifest.read_text(encoding="utf-8"))
    app = create_app()
    with app.app_context():
        project = Project.query.filter_by(public_id=fixture["project_a"]).one()
        user = ExpertUser.query.filter_by(username="shared_transport_e2e_operator").one()
        cargo_type = CargoType.query.filter_by(is_active=True).order_by(CargoType.id).first()
        uom = UnitOfMeasure.query.filter_by(is_active=True).order_by(UnitOfMeasure.id).first()
        if not cargo_type or not uom:
            raise RuntimeError("catalog journey requires active cargo type and UOM")
        db.session.add_all(
            [
                OrganizationCargoTypeActivation(
                    organization_id=project.organization_id,
                    cargo_type_id=cargo_type.id,
                    status="ACTIVE",
                    created_by=user.id,
                    updated_by=user.id,
                ),
                OrganizationUnitOfMeasureActivation(
                    organization_id=project.organization_id,
                    unit_of_measure_id=uom.id,
                    status="ACTIVE",
                    created_by=user.id,
                    updated_by=user.id,
                ),
            ]
        )
        catalog = CargoCatalogItem(
            organization_id=project.organization_id,
            immutable_code="CATALOG-JOURNEY-001",
            fa_name="[CATALOG-JOURNEY] کالای عملیاتی",
            en_name="Catalog Journey Operational Cargo",
            cargo_type_id=cargo_type.id,
            default_uom_id=uom.id,
            description="Disposable browser qualification catalog master.",
            created_by=user.id,
            updated_by=user.id,
        )
        db.session.add(catalog)
        db.session.commit()
        fixture.update({
            "catalog_item": catalog.public_id,
            "catalog_code": catalog.immutable_code,
            "catalog_name": catalog.fa_name,
            "uom": uom.public_id,
        })
        manifest.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
