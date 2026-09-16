"""Synthetic, private, loopback-only fixture for the FWD-07 browser journey."""
from __future__ import annotations
import os, tempfile
from pathlib import Path
from uuid import uuid4
import bcrypt
os.environ.setdefault("APP_ENV", "test")
from backend import create_app
from backend.extensions import db
from backend.models import DocumentDefinition, ExpertUser, ShipmentRequest
from backend.operational_models import OperationalMembership, OperationalOrganization

def main():
    password = os.environ["FWD07_UAT_PASSWORD"]
    root = Path(tempfile.gettempdir()) / "forwarder-fwd07-browser"; root.mkdir(exist_ok=True)
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///" + (root / f"{uuid4().hex}.sqlite").as_posix(), "DOCUMENT_STORAGE_ROOT": str(root / uuid4().hex)}, skip_startup=True)
    with app.app_context():
        db.create_all(); hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        org = OperationalOrganization(name="FWD07 synthetic tenant")
        expert = ExpertUser(username="fwd07-expert", full_name="کارشناس آزمون", password_hash=hashed, role="expert", authority="EXPERT", is_active=True)
        case = ShipmentRequest(ownership_scope="TENANT", operational_organization_id=None, contact_phone="09070000001", tracking_code="SR-FWD07-BROWSER", shipping_type="domestic", status="new", status_request_status="new")
        definition = DocumentDefinition(code="fwd07-proof", title="مدرک فارسی با نام بلند", is_required=True, allowed_formats='["pdf","png"]', max_file_size_bytes=1048576, max_active_file_count=8, sort_order=1, applicability_scope="all")
        db.session.add_all([org, expert]); db.session.flush(); expert_membership = OperationalMembership(organization_id=org.id, user_id=expert.id, is_active=True, permissions=[]); case.operational_organization_id=org.id; case.assigned_to=expert.id
        case.tracking_code = "SR-FWD07-BROWSER-1280"
        mobile_case = ShipmentRequest(ownership_scope="TENANT", operational_organization_id=org.id, assigned_to=expert.id, contact_phone="09070000002", tracking_code="SR-FWD07-BROWSER-390", shipping_type="domestic", status="new", status_request_status="new")
        db.session.add_all([expert_membership, case, mobile_case, definition]); db.session.commit()
    app.run(host="127.0.0.1", port=int(os.getenv("FWD07_UAT_API_PORT", "5057")), use_reloader=False)
if __name__ == "__main__": main()
