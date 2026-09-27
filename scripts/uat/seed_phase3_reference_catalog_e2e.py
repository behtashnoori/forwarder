"""Tailor the shared graph for P3-01 and the Admin foundations journey."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.global_logistics_point_models import GlobalLogisticsPoint, GlobalLogisticsPointMode
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country, ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.organization_profile import apply_profile, load_profile, plan_profile
from backend.reference_data_catalog import apply_catalog, load_catalog, plan_catalog
from backend.services.admin_authorization_service import ORGANIZATION_ADMIN_PERMISSION
from scripts.uat.seed_shared_transport_e2e import (
    PERMISSIONS,
    fixture_user,
    main as seed_shared_transport,
)


def main() -> None:
    previous = os.environ.get("FORWARDER_E2E_PRIMARY_EXPERT")
    os.environ["FORWARDER_E2E_PRIMARY_EXPERT"] = "restricted"
    try:
        seed_shared_transport()
    finally:
        if previous is None:
            os.environ.pop("FORWARDER_E2E_PRIMARY_EXPERT", None)
        else:
            os.environ["FORWARDER_E2E_PRIMARY_EXPERT"] = previous

    fixture_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"])
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    app = create_app(skip_startup=True)
    with app.app_context():
        catalog = load_catalog()
        before = plan_catalog(catalog, "uat")
        if before.created_count <= 0 or before.conflict_count or before.rejected_count:
            raise RuntimeError("Admin foundations fixture requires a clean additive catalog plan")
        applied, run = apply_catalog(
            catalog,
            environment="uat",
            executed_by="owned-admin-foundations-qualification",
            approval_reference="ADMIN-SYSTEM-FOUNDATIONS-HARDENING",
            expected_checksum=catalog.checksum,
        )
        after = plan_catalog(catalog, "uat")
        if run.status != "succeeded" or after.created_count or after.conflict_count or after.rejected_count:
            raise RuntimeError("Reference Catalog V1 did not reach an idempotent state")

        organization = OperationalOrganization.query.filter_by(
            name="[SHARED-E2E] Organization A"
        ).one()
        actor = ExpertUser.query.filter_by(username="shared_transport_e2e_admin").one()
        profile = load_profile(catalog=catalog)
        profile_before = plan_profile(
            profile,
            organization_public_id=organization.public_id,
            actor_username=actor.username,
        )
        profile_applied = apply_profile(
            profile,
            organization_public_id=organization.public_id,
            actor_username=actor.username,
            operator="owned-admin-foundations-qualification",
            approval_reference="ADMIN-SYSTEM-FOUNDATIONS-HARDENING",
            expected_checksum=profile.checksum,
        )
        profile_after = plan_profile(
            profile,
            organization_public_id=organization.public_id,
            actor_username=actor.username,
        )
        if (
            profile_before.created_count <= 0
            or profile_applied.conflict_count
            or profile_after.created_count
            or profile_after.conflict_count
            or profile_after.unchanged_count != profile.planned_count
        ):
            raise RuntimeError("Standard Organization Profile V1 did not reach an idempotent state")

        dual = fixture_user(
            suffix="dual",
            authority="PLATFORM_ADMIN",
            password=os.environ["FORWARDER_E2E_PASSWORD"],
        )
        membership = OperationalMembership.query.filter_by(
            organization_id=organization.id, user_id=dual.id
        ).one_or_none()
        if membership is None:
            membership = OperationalMembership(
                organization_id=organization.id,
                user_id=dual.id,
            )
            db.session.add(membership)
        membership.permissions = sorted(set(PERMISSIONS) | {
            ORGANIZATION_ADMIN_PERMISSION,
            "logistics_point.read",
            "logistics_point.manage",
            "delay_reason.manage",
            "exception_reason.manage",
        })
        membership.is_active = True

        point_type = LogisticsPointType.query.filter_by(
            immutable_code="ADMIN_E2E_WAREHOUSE"
        ).one_or_none()
        if point_type is None:
            point_type = LogisticsPointType(
                immutable_code="ADMIN_E2E_WAREHOUSE",
                fa_name="انبار",
                en_name="Warehouse",
                definition="Owned qualification point type",
                created_by=dual.id,
                updated_by=dual.id,
            )
            db.session.add(point_type)
            db.session.flush()
        country = Country.query.filter_by(code="XZ").one_or_none()
        if country is None:
            country = Country(code="XZ", name_en="Qualification Country", name_fa="کشور آزمون")
            db.session.add(country)
            db.session.flush()
        global_point = GlobalLogisticsPoint.query.filter_by(
            immutable_code="ADMIN-E2E-GLOBAL-WAREHOUSE"
        ).one_or_none()
        if global_point is None:
            global_point = GlobalLogisticsPoint(
                immutable_code="ADMIN-E2E-GLOBAL-WAREHOUSE",
                logistics_point_type_id=point_type.id,
                fa_name="انبار استاندارد آزمون",
                en_name="Qualification Global Warehouse",
                normalized_name="qualification global warehouse",
                country_id=country.id,
                city_name="Qualification City",
                geography_key="XZ:qualification-city",
                facility_identity_key="admin-e2e-global-warehouse",
                lifecycle_status="ACTIVE",
                verification_status="VERIFIED",
                created_by=dual.id,
                updated_by=dual.id,
            )
            global_point.modes.append(GlobalLogisticsPointMode(mode_code="ROAD"))
            db.session.add(global_point)
        db.session.commit()

        fixture["admin_foundations"] = {
            "organization_public_id": organization.public_id,
            "catalog_checksum": catalog.checksum,
            "catalog_first_created": before.created_count,
            "catalog_second_created": after.created_count,
            "profile_checksum": profile.checksum,
            "profile_first_created": profile_before.created_count,
            "profile_second_created": profile_after.created_count,
            "profile_unchanged": profile_after.unchanged_count,
            "global_point_public_id": global_point.public_id,
        }
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")


if __name__ == "__main__":
    main()
