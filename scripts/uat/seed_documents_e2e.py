"""Seed the isolated expert-only Documents browser qualification graph."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.extensions import db
from backend.models import (
    DocumentDefinition,
    ExpertUser,
    OrganizationDocumentRequirement,
    ShipmentRequest,
)
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services.user_service import hash_password


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    password = os.environ["FORWARDER_E2E_PASSWORD"]
    manifest_path = Path(os.environ["FORWARDER_E2E_FIXTURE_PATH"]).resolve()
    if "dms1a_documents_build_" not in database_url:
        raise RuntimeError("Refusing non-disposable Documents E2E database")
    app = create_app({"SQLALCHEMY_DATABASE_URI": database_url, "TESTING": True}, skip_startup=True)
    with app.app_context():
        organization = OperationalOrganization(name="[DOC-E2E] Organization")
        owner = ExpertUser(
            username="documents_e2e_owner", password_hash=hash_password(password),
            full_name="[DOC-E2E] Owning Expert", role="expert", authority="EXPERT",
            is_active=True, can_handle_domestic=True, can_handle_international=True,
        )
        peer = ExpertUser(
            username="documents_e2e_peer", password_hash=hash_password(password),
            full_name="[DOC-E2E] Other Expert", role="expert", authority="EXPERT",
            is_active=True, can_handle_domestic=True, can_handle_international=True,
        )
        admin = ExpertUser(
            username="documents_e2e_admin", password_hash=hash_password(password),
            full_name="[DOC-E2E] Organization Admin", role="admin",
            authority="ORGANIZATION_ADMIN", is_active=True,
        )
        db.session.add_all([organization, owner, peer, admin])
        db.session.flush()
        db.session.add_all([
            OperationalMembership(organization_id=organization.id, user_id=owner.id, permissions=[]),
            OperationalMembership(organization_id=organization.id, user_id=peer.id, permissions=[]),
            OperationalMembership(
                organization_id=organization.id, user_id=admin.id,
                permissions=["request.read"],
            ),
        ])
        definition = DocumentDefinition(
            code="documents_browser_multi", title="سند چندفایلی آزمون",
            description="آزمون مرورگری append، جایگزینی هدف‌دار و تاریخچه",
            is_required=True, allowed_formats='["pdf"]',
            max_file_size_bytes=2 * 1024 * 1024, max_active_file_count=8,
            sort_order=-100, applicability_scope="all", is_active=True,
            catalog_lifecycle_status="ACTIVE", source_review_status="VERIFIED",
            created_by=admin.id, updated_by=admin.id,
        )
        db.session.add(definition)
        db.session.flush()
        db.session.add(OrganizationDocumentRequirement(
            organization_id=organization.id, document_definition_id=definition.id,
            requirement_level="REQUIRED", is_active=True,
            created_by=admin.id, updated_by=admin.id,
        ))
        request_row = ShipmentRequest(
            contact_phone="09120000000", customer_first_name="آزمون",
            customer_last_name="اسناد", shipping_type="domestic",
            status="new", status_request_status="new", priority="high",
            cargo_description="[DOC-E2E] Browser evidence",
            assigned_to=owner.id, ownership_scope="TENANT",
            operational_organization_id=organization.id,
            tracking_code="DOC-E2E-001",
        )
        db.session.add(request_row)
        db.session.commit()
        manifest = {
            "request_public_id": request_row.public_id,
            "definition_public_id": definition.public_id,
            "owner_username": owner.username,
            "peer_username": peer.username,
            "admin_username": admin.username,
        }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"seed": "documents-e2e", "request_public_id": manifest["request_public_id"]}))


if __name__ == "__main__":
    main()
