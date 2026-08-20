"""ADR-039 V1 domain, tenant, lifecycle, evidence, search, and API tests."""

import pytest

from backend import create_app
from backend.extensions import db
from backend.external_reference_models import (
    ExternalReferenceType,
)
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    Customer,
    DocumentDefinition,
    ExpertQuote,
    ExpertUser,
    ShipmentRequest,
)
from backend.operational_models import (
    ExecutionUnit,
    OperationalMembership,
    OperationalOrganization,
    OperationalShipment,
    Project,
)
from backend.services import external_reference_service as service
from backend.services.operational_service import OperationalError


@pytest.fixture()
def reference_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "external-reference-test",
        }
    )
    with app.app_context():
        org = OperationalOrganization(name="Reference Tenant")
        other = OperationalOrganization(name="Other Tenant")
        user = ExpertUser(
            username="reference-user",
            password_hash="unused",
            full_name="Reference User",
            role="expert",
            is_active=True,
        )
        outsider = ExpertUser(
            username="reference-outsider",
            password_hash="unused",
            full_name="Reference Outsider",
            role="expert",
            is_active=True,
        )
        db.session.add_all([org, other, user, outsider])
        db.session.flush()
        permissions = [
            "operational_shipment.read",
            "operational_shipment.create",
            "execution_unit.read",
            "execution_unit.manage",
        ]
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=org.id, user_id=user.id, permissions=permissions
                ),
                OperationalMembership(
                    organization_id=other.id,
                    user_id=outsider.id,
                    permissions=permissions,
                ),
            ]
        )
        customer = Customer(
            first_name="Reference",
            last_name="Customer",
            phone="09000000000",
            status="active",
        )
        db.session.add(customer)
        db.session.flush()
        project = Project(
            organization_id=org.id,
            primary_customer_id=customer.id,
            project_code="REF-P",
            created_by_user_id=user.id,
        )
        other_project = Project(
            organization_id=other.id,
            primary_customer_id=customer.id,
            project_code="REF-O",
            created_by_user_id=outsider.id,
        )
        db.session.add_all([project, other_project])
        db.session.flush()
        shipment = OperationalShipment(
            organization_id=org.id,
            source_type="direct",
            customer_id=customer.id,
            project_id=project.id,
            created_by_user_id=user.id,
        )
        second = OperationalShipment(
            organization_id=org.id,
            source_type="direct",
            customer_id=customer.id,
            project_id=project.id,
            created_by_user_id=user.id,
        )
        foreign = OperationalShipment(
            organization_id=other.id,
            source_type="direct",
            customer_id=customer.id,
            project_id=other_project.id,
            created_by_user_id=outsider.id,
        )
        db.session.add_all([shipment, second, foreign])
        db.session.flush()
        unit = ExecutionUnit(
            project_id=project.id,
            operational_shipment_id=shipment.id,
            unit_code="U-REF",
            unit_type="truck",
            created_by_user_id=user.id,
        )
        db.session.add(unit)
        types = [
            ExternalReferenceType(
                code="BILL_OF_LADING_NUMBER",
                name_fa="شماره بارنامه دریایی",
                name_en="Bill of Lading Number",
                lifecycle_status="ACTIVE",
                search_policy="PREFIX",
                uniqueness_scope="OWNER",
                source_authority="UN/CEFACT",
                provenance_reference="UN/EDIFACT 1153 BM",
                allows_operational_shipment=True,
                allows_execution_unit=False,
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            ),
            ExternalReferenceType(
                code="AIR_WAYBILL_NUMBER",
                name_fa="شماره راهنامه هوایی",
                name_en="Air Waybill Number",
                lifecycle_status="ACTIVE",
                search_policy="EXACT",
                uniqueness_scope="TENANT",
                source_authority="UN/CEFACT",
                provenance_reference="UN/EDIFACT 1153 AWB",
                allows_operational_shipment=True,
                allows_execution_unit=False,
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            ),
            ExternalReferenceType(
                code="CMR_NUMBER",
                name_fa="شماره سی‌ام‌آر",
                name_en="CMR Number",
                lifecycle_status="ACTIVE",
                search_policy="PREFIX",
                uniqueness_scope="NONE",
                source_authority="UNECE",
                provenance_reference="CMR Convention",
                allows_operational_shipment=True,
                allows_execution_unit=True,
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
            ),
        ]
        db.session.add_all(types)
        db.session.commit()
        app.config["refs"] = {
            "org": org.id,
            "other": other.id,
            "user": user.id,
            "outsider": outsider.id,
            "shipment": shipment.public_id,
            "shipment2": second.public_id,
            "foreign": foreign.public_id,
            "unit": unit.public_id,
        }
    yield app


def _user(app, outsider=False):
    return {
        "id": app.config["refs"]["outsider" if outsider else "user"],
        "role": "expert",
    }


def test_owner_applicability_tenant_fence_and_uniqueness(reference_app):
    with reference_app.app_context():
        shipment = service.scoped_shipment(
            reference_app.config["refs"]["shipment"], _user(reference_app), manage=True
        )
        row, created = service.create(
            "shipment",
            shipment,
            shipment.organization_id,
            {"type": "BILL_OF_LADING_NUMBER", "value": " bl  001 "},
            _user(reference_app),
            "bl-create",
        )
        assert (
            created and row.raw_value == "bl  001" and row.normalized_value == "BL 001"
        )
        with pytest.raises(OperationalError) as duplicate:
            service.create(
                "shipment",
                shipment,
                shipment.organization_id,
                {"type": "BILL_OF_LADING_NUMBER", "value": "BL 001"},
                _user(reference_app),
                "bl-duplicate",
            )
        assert duplicate.value.code == "REFERENCE_ALREADY_EXISTS"
        db.session.rollback()
        unit, org = service.scoped_unit(
            reference_app.config["refs"]["unit"], _user(reference_app), manage=True
        )
        with pytest.raises(OperationalError) as incompatible:
            service.create(
                "unit",
                unit,
                org,
                {"type": "BILL_OF_LADING_NUMBER", "value": "BL-U"},
                _user(reference_app),
                "bad-owner",
            )
        assert incompatible.value.code == "REFERENCE_TYPE_NOT_APPLICABLE"
        with pytest.raises(OperationalError) as hidden:
            service.scoped_shipment(
                reference_app.config["refs"]["foreign"],
                _user(reference_app),
                manage=True,
            )
        assert hidden.value.status == 404


def test_unit_none_uniqueness_supersession_cancellation_and_active_projection(
    reference_app,
):
    with reference_app.app_context():
        unit, org = service.scoped_unit(
            reference_app.config["refs"]["unit"], _user(reference_app), manage=True
        )
        first, _ = service.create(
            "unit",
            unit,
            org,
            {"type": "CMR_NUMBER", "value": "CMR-OLD"},
            _user(reference_app),
            "cmr-1",
        )
        duplicate, _ = service.create(
            "unit",
            unit,
            org,
            {"type": "CMR_NUMBER", "value": "CMR-OLD"},
            _user(reference_app),
            "cmr-2",
        )
        assert duplicate.id != first.id
        corrected = service.transition(
            "unit",
            unit.id,
            org,
            first.public_id,
            {
                "expected_revision": 1,
                "value": "CMR-NEW",
                "reason": "Carrier correction",
            },
            _user(reference_app),
            "supersede",
            "cmr-supersede",
        )
        assert corrected.supersedes_reference_id == first.id
        db.session.refresh(first)
        assert first.lifecycle_status == "SUPERSEDED" and first.raw_value == "CMR-OLD"
        cancelled = service.transition(
            "unit",
            unit.id,
            org,
            corrected.public_id,
            {"expected_revision": 1, "reason": "Carrier cancellation"},
            _user(reference_app),
            "cancel",
            "cmr-cancel",
        )
        assert cancelled.lifecycle_status == "CANCELLED"
        assert service.list_for_owner("unit", unit.id, active_only=True) == [
            service.serialize(duplicate)
        ]


def test_tenant_uniqueness_search_and_non_enumeration(reference_app):
    with reference_app.app_context():
        one = service.scoped_shipment(
            reference_app.config["refs"]["shipment"], _user(reference_app), manage=True
        )
        two = service.scoped_shipment(
            reference_app.config["refs"]["shipment2"], _user(reference_app), manage=True
        )
        service.create(
            "shipment",
            one,
            one.organization_id,
            {"type": "AIR_WAYBILL_NUMBER", "value": "123-45678901"},
            _user(reference_app),
            "awb-1",
        )
        with pytest.raises(OperationalError) as tenant_duplicate:
            service.create(
                "shipment",
                two,
                two.organization_id,
                {"type": "AIR_WAYBILL_NUMBER", "value": "123-45678901"},
                _user(reference_app),
                "awb-2",
            )
        assert tenant_duplicate.value.code == "REFERENCE_ALREADY_EXISTS"
        db.session.rollback()
        exact = service.search(
            {"type": "AIR_WAYBILL_NUMBER", "value": "123-45678901", "mode": "exact"},
            _user(reference_app),
        )
        assert exact["data"][0]["owner_public_id"] == one.public_id
        with pytest.raises(OperationalError) as prefix:
            service.search(
                {"type": "AIR_WAYBILL_NUMBER", "value": "123", "mode": "prefix"},
                _user(reference_app),
            )
        assert prefix.value.code == "PREFIX_SEARCH_NOT_ALLOWED"
        assert (
            service.search(
                {"type": "AIR_WAYBILL_NUMBER", "value": "123-45678901"},
                _user(reference_app, outsider=True),
            )["data"]
            == []
        )


def test_exact_document_version_and_lineage(reference_app):
    with reference_app.app_context():
        ids = reference_app.config["refs"]
        shipment = service.scoped_shipment(
            ids["shipment"], _user(reference_app), manage=True
        )
        request = ShipmentRequest(
            contact_phone="09000000001",
            status="new",
            status_request_status="new",
            ownership_scope="TENANT",
            operational_organization_id=ids["org"],
        )
        definition = DocumentDefinition(
            code="BILL_OF_LADING_TEST",
            title="B/L",
            allowed_formats='["pdf"]',
            max_file_size_bytes=1000,
        )
        db.session.add_all([request, definition])
        db.session.flush()
        quote = ExpertQuote(
            shipment_request_id=request.id,
            amount=1,
            currency="IRR",
            created_by_expert_id=ids["user"],
            customer_response="accepted",
            operational_organization_id=ids["org"],
        )
        db.session.add(quote)
        db.session.flush()
        shipment.source_type = "accepted_quote"
        shipment.customer_id = None
        shipment.shipment_request_id = request.id
        shipment.accepted_quote_id = quote.id
        requirement = CaseDocumentRequirement(
            operational_organization_id=ids["org"],
            shipment_request_id=request.id,
            source_definition_id=definition.id,
            source_definition_code="BILL_OF_LADING",
            source_definition_revision=1,
            title="B/L",
            is_required=False,
            allowed_formats='["pdf"]',
            max_file_size_bytes=1000,
            max_active_file_count=1,
            sort_order=1,
        )
        db.session.add(requirement)
        db.session.flush()
        file = CaseDocumentFile(
            operational_organization_id=ids["org"],
            shipment_request_id=request.id,
            case_requirement_id=requirement.id,
            is_miscellaneous=False,
            original_filename="bill.pdf",
            safe_download_filename="bill.pdf",
            storage_key="reference-test/bill.pdf",
            canonical_extension="pdf",
            detected_mime_type="application/pdf",
            file_size_bytes=1,
            sha256_hash="0" * 64,
            version_number=3,
            uploaded_by=ids["user"],
        )
        db.session.add(file)
        db.session.commit()
        row, _ = service.create(
            "shipment",
            shipment,
            ids["org"],
            {
                "type": "BILL_OF_LADING_NUMBER",
                "value": "EVIDENCE-BL",
                "evidence_document_public_id": file.public_id,
                "evidence_version": 3,
            },
            _user(reference_app),
            "evidence",
        )
        assert row.evidence_document_file_id == file.id and row.evidence_version == 3
        with pytest.raises(OperationalError) as wrong_version:
            service.create(
                "shipment",
                shipment,
                ids["org"],
                {
                    "type": "BILL_OF_LADING_NUMBER",
                    "value": "OTHER-BL",
                    "evidence_document_public_id": file.public_id,
                    "evidence_version": 2,
                },
                _user(reference_app),
                "wrong-version",
            )
        assert wrong_version.value.code == "EVIDENCE_VERSION_MISMATCH"


def test_api_surface_is_internal_and_body_organization_is_ignored(reference_app):
    rules = {
        str(rule)
        for rule in reference_app.url_map.iter_rules()
        if "external-reference" in str(rule)
    }
    assert rules and all(path.startswith("/api/internal/") for path in rules)
    assert not any(path.startswith(("/api/public", "/api/customer")) for path in rules)
    with reference_app.app_context():
        shipment = service.scoped_shipment(
            reference_app.config["refs"]["shipment"], _user(reference_app), manage=True
        )
        row, _ = service.create(
            "shipment",
            shipment,
            shipment.organization_id,
            {
                "type": "BILL_OF_LADING_NUMBER",
                "value": "BODY-ORG",
                "organization_id": reference_app.config["refs"]["other"],
            },
            _user(reference_app),
            "body-org",
        )
        assert row.organization_id == reference_app.config["refs"]["org"]
