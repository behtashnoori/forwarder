from __future__ import annotations

import pytest

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.models import (
    CaseDocumentFile,
    CaseDocumentRequirement,
    Country,
    DocumentCatalogAuditEvent,
    DocumentDefinition,
    ExpertUser,
    OrganizationDocumentRequirement,
)
from backend.mdpm_models import ArtifactAssociation, OperationalDocumentRequirement
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.project_configuration_models import ProjectDocumentRequirement


@pytest.fixture()
def catalog_app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "DOCUMENT_STORAGE_ROOT": str(tmp_path / "docs"),
        }
    )
    with app.app_context():
        platform = ExpertUser(
            username="catalog-platform",
            password_hash="x",
            full_name="Platform",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        organization_admin = ExpertUser(
            username="catalog-org",
            password_hash="x",
            full_name="Org",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        organization = OperationalOrganization(name="Catalog Test Organization")
        country = Country(code="IRN", name_en="Iran", name_fa="ایران", is_active=True)
        db.session.add_all([platform, organization_admin, organization, country])
        db.session.flush()
        db.session.add(
            OperationalMembership(
                organization_id=organization.id,
                user_id=organization_admin.id,
                permissions=[],
            )
        )
        definition = DocumentDefinition(
            code="catalog_test_document",
            title="سند قدیمی",
            description="شرح قدیمی",
            is_required=True,
            allowed_formats='["pdf"]',
            max_file_size_bytes=1024,
            max_active_file_count=1,
            applicability_scope="all",
            created_by=platform.id,
            updated_by=platform.id,
        )
        db.session.add(definition)
        db.session.commit()
        state = {
            "platform": auth_manager.generate_tokens(platform.id)["access_token"],
            "organization": auth_manager.generate_tokens(organization_admin.id)[
                "access_token"
            ],
            "public_id": definition.public_id,
            "definition_id": definition.id,
        }
    return app, state


def _headers(token, key=None):
    result = {"Authorization": f"Bearer {token}"}
    if key:
        result["Idempotency-Key"] = key
    return result


def _path(state):
    return f"/api/platform/document-catalog/{state['public_id']}"


def test_legacy_projection_and_platform_authority(catalog_app):
    app, state = catalog_app
    client = app.test_client()
    legacy = client.get(
        "/api/admin/document-definitions", headers=_headers(state["organization"])
    )
    assert legacy.status_code == 200
    item = legacy.get_json()["items"][0]
    assert (
        item["title"] == "سند قدیمی"
        and item["description"] == "شرح قدیمی"
        and item["is_required"] is True
    )
    assert item["name_fa"] is None and item["family_code"] is None
    assert (
        client.patch(
            _path(state),
            headers=_headers(state["organization"], "org-denied"),
            json={"expected_revision": 1},
        ).status_code
        == 403
    )


def test_metadata_relations_search_collision_idempotency_and_non_regression(
    catalog_app,
):
    app, state = catalog_app
    client = app.test_client()
    payload = {
        "expected_revision": 1,
        "name_fa": "بارنامه دریایی",
        "name_en": "Ocean Bill of Lading",
        "description_fa": "شرح فارسی",
        "description_en": "English description",
        "family_code": "TRANSPORT",
        "expiry_applicable": False,
        "organization_overridable": True,
        "source_review_status": "SOURCE_CONFIRMED",
        "aliases": [
            {"locale": "en", "display_value": "B/L", "alias_kind": "ABBREVIATION"},
            {
                "locale": "fa",
                "display_value": "بارنامه دریا",
                "alias_kind": "COMMON_NAME",
                "is_active": False,
            },
        ],
        "jurisdictions": [
            {"kind": "INTERNATIONAL"},
            {"kind": "COUNTRY", "country_code": "IRN"},
        ],
        "modes": ["SEA", "MULTIMODAL"],
        "stages": ["ORIGIN", "IN_TRANSIT"],
        "business_scopes": ["REQUEST", "OPERATIONAL_SHIPMENT"],
        "provenance": [
            {
                "source_authority_code": "UNECE",
                "source_authority_name": "UNECE",
                "source_title": "UN/EDIFACT code list",
                "source_reference": "https://example.test/source",
                "source_version": "2026",
                "review_status": "SOURCE_CONFIRMED",
                "jurisdiction_key": "INTERNATIONAL",
            },
            {
                "source_authority_code": "IRICA",
                "source_authority_name": "Iran Customs",
                "source_title": "Document guidance",
                "review_status": "SOURCE_CONFIRMATION_REQUIRED",
                "jurisdiction_key": "COUNTRY:IRN",
            },
        ],
    }
    response = client.patch(
        _path(state), headers=_headers(state["platform"], "metadata-1"), json=payload
    )
    assert response.status_code == 200
    item = response.get_json()
    assert item["revision"] == 2 and item["modes"] == ["MULTIMODAL", "SEA"]
    assert len(item["provenance"]) == 2 and any(
        x["country_code"] == "IRN" for x in item["jurisdictions"]
    )
    replay = client.patch(
        _path(state), headers=_headers(state["platform"], "metadata-1"), json=payload
    )
    assert replay.status_code == 200 and replay.get_json()["revision"] == 2
    assert (
        client.get(
            "/api/platform/document-catalog?q=b%2Fl",
            headers=_headers(state["platform"]),
        ).get_json()["items"][0]["public_id"]
        == state["public_id"]
    )
    assert (
        client.get(
            "/api/platform/document-catalog?q=Ocean",
            headers=_headers(state["platform"]),
        ).get_json()["items"][0]["public_id"]
        == state["public_id"]
    )
    assert (
        client.get(
            "/api/platform/document-catalog?q=بارنامه",
            headers=_headers(state["platform"]),
        ).get_json()["items"][0]["public_id"]
        == state["public_id"]
    )
    with app.app_context():
        assert OrganizationDocumentRequirement.query.count() == 0
        assert ProjectDocumentRequirement.query.count() == 0
        assert CaseDocumentRequirement.query.count() == 0
        assert OperationalDocumentRequirement.query.count() == 0
        assert ArtifactAssociation.query.count() == 0
        assert CaseDocumentFile.query.count() == 0
        assert DocumentCatalogAuditEvent.query.count() == 1


def test_alias_collision_revision_and_family_validation(catalog_app):
    app, state = catalog_app
    client = app.test_client()
    base = {
        "expected_revision": 1,
        "aliases": [{"display_value": "Unique alias", "alias_kind": "COMMON_NAME"}],
    }
    assert (
        client.patch(
            _path(state), headers=_headers(state["platform"], "one"), json=base
        ).status_code
        == 200
    )
    assert (
        client.patch(
            _path(state),
            headers=_headers(state["platform"], "stale"),
            json={"expected_revision": 1, "family_code": "FINANCE"},
        ).status_code
        == 409
    )
    assert (
        client.patch(
            _path(state),
            headers=_headers(state["platform"], "bad-family"),
            json={"expected_revision": 2, "family_code": "OTHER"},
        ).status_code
        == 400
    )
    with app.app_context():
        other = DocumentDefinition(
            code="other_document",
            title="Other",
            allowed_formats='["pdf"]',
            max_file_size_bytes=1024,
            max_active_file_count=1,
        )
        db.session.add(other)
        db.session.commit()
        other_public_id = other.public_id
    collision = client.patch(
        f"/api/platform/document-catalog/{other_public_id}",
        headers=_headers(state["platform"], "collision"),
        json={
            "expected_revision": 1,
            "aliases": [{"display_value": "unique alias", "alias_kind": "COMMON_NAME"}],
        },
    )
    assert collision.status_code == 409


def test_lifecycle_activation_gate_and_deprecation(catalog_app):
    app, state = catalog_app
    client = app.test_client()
    assert (
        client.post(
            _path(state) + "/lifecycle",
            headers=_headers(state["platform"], "unsafe"),
            json={"expected_revision": 1, "target_status": "ACTIVE"},
        ).status_code
        == 409
    )
    metadata = {
        "expected_revision": 1,
        "name_fa": "سند",
        "name_en": "Document",
        "family_code": "COMMERCIAL",
        "source_review_status": "SOURCE_CONFIRMED",
        "jurisdictions": [{"kind": "GLOBAL"}],
        "provenance": [
            {
                "source_authority_code": "AUTH",
                "source_authority_name": "Authority",
                "source_title": "Official source",
                "review_status": "SOURCE_CONFIRMED",
                "jurisdiction_key": "GLOBAL",
            }
        ],
    }
    assert (
        client.patch(
            _path(state),
            headers=_headers(state["platform"], "activation-metadata"),
            json=metadata,
        ).status_code
        == 200
    )
    revision = 2
    for target, key in (
        ("REVIEWED", "reviewed"),
        ("SOURCE_CONFIRMED", "confirmed"),
        ("ACTIVE", "active"),
        ("DEPRECATED", "deprecated"),
    ):
        response = client.post(
            _path(state) + "/lifecycle",
            headers=_headers(state["platform"], key),
            json={
                "expected_revision": revision,
                "target_status": target,
                "approval_reference": "ADR-036",
            },
        )
        assert response.status_code == 200
        revision += 1
    assert response.get_json()["catalog_lifecycle_status"] == "DEPRECATED"
    assert response.get_json()["is_active"] is False
    with app.app_context():
        assert OrganizationDocumentRequirement.query.count() == 0
