from pathlib import Path

from backend import create_app
from backend.extensions import db
from backend.external_reference_models import ExternalReferenceType
from backend.external_reference_type_package import load_package
from backend.models import ExpertUser
from scripts.external_reference_type_v1_certification import (
    verify_package_database_equivalence,
)


PACKAGE_PATH = (
    Path(__file__).parents[1]
    / "reference_data"
    / "external_references"
    / "external-reference-types-v1.0.0.json"
)


def test_harness_explicit_internal_helper_import_avoids_wildcard_name_error():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {},
        }
    )
    with app.app_context():
        db.create_all()
        actor = ExpertUser(
            username="external-reference-certification-harness",
            password_hash="disabled-test-account",
            full_name="Certification Harness",
            authority="PLATFORM_ADMIN",
            is_active=False,
        )
        db.session.add(actor)
        db.session.flush()
        package = load_package(PACKAGE_PATH)
        for item in package.definitions:
            provenance = item["provenance"]
            db.session.add(
                ExternalReferenceType(
                    code=item["code"],
                    name_fa=item["name_fa"],
                    name_en=item["name_en"],
                    lifecycle_status=item["lifecycle"],
                    normalization_policy=item["normalization_policy"],
                    search_policy=item["search_policy"],
                    uniqueness_scope=item["uniqueness_scope"],
                    masking_policy=item["masking_policy"],
                    source_authority=provenance["source_authority"],
                    provenance_reference=provenance["source_reference"],
                    allows_operational_shipment=(
                        "OPERATIONAL_SHIPMENT" in item["owner_applicability"]
                    ),
                    allows_execution_unit=(
                        "EXECUTION_UNIT" in item["owner_applicability"]
                    ),
                    created_by_user_id=actor.id,
                    updated_by_user_id=actor.id,
                )
            )
        db.session.commit()

        result = verify_package_database_equivalence(package)

        assert result["equivalent"] is True
        assert result["type_count"] == 3
        assert result["unexpected_codes"] == []
        assert result["mismatches"] == {
            "AIR_WAYBILL_NUMBER": [],
            "BILL_OF_LADING_NUMBER": [],
            "CMR_NUMBER": [],
        }
