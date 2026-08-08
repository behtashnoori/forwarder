"""Seed synthetic OIP browser UAT data into an explicit disposable gate DB."""
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.engine import make_url
import bcrypt

from backend import create_app
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.services import oip_service as oip

url=os.environ["DATABASE_URL"];parsed=make_url(url)
assert parsed.host in {"127.0.0.1","localhost"} and "oip2_gate" in (parsed.database or "")
app=create_app({"SQLALCHEMY_DATABASE_URI":url,"TESTING":True,"SECRET_KEY":"oip-uat-seed"},skip_startup=True)
with app.app_context():
    user=ExpertUser.query.filter_by(username="oip_uat_operator").one_or_none()
    if not user:
        org=OperationalOrganization(name="OIP-2 Synthetic Browser UAT")
        user=ExpertUser(username="oip_uat_operator",password_hash=bcrypt.hashpw(b"OipUat-2026!",bcrypt.gensalt()).decode(),full_name="OIP UAT Operator",role="admin",is_active=True)
        db.session.add_all([org,user]);db.session.flush();db.session.add(OperationalMembership(organization_id=org.id,user_id=user.id,permissions=["oip.read","oip.manage","oip.reconcile"]));db.session.commit()
    user.password_hash=bcrypt.hashpw(b"OipUat-2026!",bcrypt.gensalt()).decode()
    org=OperationalMembership.query.filter_by(user_id=user.id).one().organization_id;now=datetime.now(timezone.utc)
    for index,typ in enumerate(oip.POLICIES,1):
        evaluation={"status":"CONFIGURED","policy_version":1,"scope":"ENTERPRISE","authority":"synthetic UAT"} if oip.POLICIES[typ]["configured"]=="GOVERNED" else None
        oip.observe(organization_id=org,situation_type=typ,subject_type="SHIPMENT",subject_public_id=f"uat-shipment-{index:02d}-opaque",dimensions={"uat_family":typ},source_domain="SYNTHETIC_UAT",source_type="AuthoritativeSyntheticFact",source_public_id=f"uat-source-{index:02d}-opaque",source_version="1",occurred_at=now-timedelta(hours=2),due_at=now-timedelta(hours=1),severity="HIGH",urgency="HIGH",active=True,source_watermark=f"uat:{typ}:1",calculated_at=now,evidence={"kind":"synthetic_uat","public_id":f"uat-source-{index:02d}-opaque"},policy_evaluation=evaluation)
    db.session.commit();print("seeded=7 username=oip_uat_operator password=OipUat-2026!")
