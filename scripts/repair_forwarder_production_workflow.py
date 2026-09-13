"""Transactional, data-only production reconciliation for one Expert workflow."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from sqlalchemy import or_, select
from backend import create_app
from backend.extensions import db
from backend.external_reference_models import ExternalReferenceType
from backend.external_reference_type_package import _expected_row, load_package
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership

PERMISSIONS = ("execution_unit.create", "execution_unit.update")
SUPPORTED_CODES = ("BILL_OF_LADING_NUMBER", "AIR_WAYBILL_NUMBER", "CMR_NUMBER")
PACKAGE_PATH = Path(__file__).parents[1] / "backend" / "reference_data" / "external_references" / "external-reference-types-v1.0.0.json"

def _membership(m, u):
    perms = sorted({x for x in m.permissions if isinstance(x, str) and x})
    return {"membership_id":m.id,"organization_id":m.organization_id,"user":{"id":u.id,"username":u.username,"email":u.email,"role":u.role},"current_permissions":perms,"missing_permissions":[x for x in PERMISSIONS if x not in perms]}

def _reference(row, expected):
    if row is None: return {"status":"MISSING","current_values":None,"governed_expected_values":expected,"action":"CREATE"}
    current={k:getattr(row,k) for k in expected}; safe={"lifecycle_status","allows_operational_shipment","allows_execution_unit"}
    conflicts=sorted(k for k,v in expected.items() if current[k]!=v and k not in safe)
    return {"status":"EXISTS","current_values":current,"governed_expected_values":expected,"action":"CONFLICT_STOP" if conflicts else ("UPDATE" if current!=expected else "NO_CHANGE"),"conflicting_fields":conflicts}

def _selected(identifier):
    if not identifier or not identifier.strip(): return []
    value=identifier.strip(); clauses=[ExpertUser.username==value,ExpertUser.email==value]
    if value.isdigit(): clauses.append(ExpertUser.id==int(value))
    return db.session.execute(select(OperationalMembership,ExpertUser).join(ExpertUser,ExpertUser.id==OperationalMembership.user_id).where(OperationalMembership.is_active.is_(True),ExpertUser.is_active.is_(True),ExpertUser.role=="expert",or_(*clauses)).order_by(OperationalMembership.id)).all()

def _plan(m, u):
    package=load_package(PACKAGE_PATH); expected={x["code"]:_expected_row(x) for x in package.definitions}
    rows={x.code:x for x in ExternalReferenceType.query.filter(ExternalReferenceType.code.in_(SUPPORTED_CODES)).all()}
    refs={code:_reference(rows.get(code),expected[code]) for code in SUPPORTED_CODES}; missing=[x for x in PERMISSIONS if x not in m.permissions]
    return {"selected_expert":_membership(m,u),"reference_plan":refs,"permission_plan":{x:"ADD" if x in missing else "PRESENT" for x in PERMISSIONS},"UNRELATED_MEMBERSHIPS_TOUCHED":0,"UNRELATED_REFERENCE_TYPES_TOUCHED":0,"MEMBERSHIP_RECONCILIATION_REQUIRED":"YES" if missing else "NO","REFERENCE_DATA_CONFIGURATION_REQUIRED":"YES" if any(x["action"]!="NO_CHANGE" for x in refs.values()) else "NO","conflict":any(x["action"]=="CONFLICT_STOP" for x in refs.values())}

def run(*, user_identifier: str | None, execute: bool) -> tuple[int, dict[str, Any]]:
    matches=_selected(user_identifier)
    if not user_identifier: return 2,{"result":"USER_SELECTION_REQUIRED"}
    if len(matches)!=1: return 2,{"result":"NO_ELIGIBLE_EXPERT_MEMBERSHIP" if not matches else "AMBIGUOUS_EXPERT_MEMBERSHIP","user_identifier":user_identifier}
    m,u=matches[0]; plan=_plan(m,u)
    if plan["conflict"]: return 2,{"result":"REFERENCE_DEFINITION_CONFLICT_STOP","mode":"execute" if execute else "validate","plan":plan}
    if not execute: return 0,{"result":"VALIDATED","mode":"validate","plan":plan}
    # Planning is read-only but SQLAlchemy opens a transaction for its queries.
    # End it before the one and only mutation transaction starts.
    db.session.rollback()
    try:
        with db.session.begin():
            m=db.session.execute(select(OperationalMembership).where(OperationalMembership.id==m.id).with_for_update()).scalar_one()
            rows={x.code:x for x in db.session.execute(select(ExternalReferenceType).where(ExternalReferenceType.code.in_(SUPPORTED_CODES)).with_for_update()).scalars()}
            package=load_package(PACKAGE_PATH); expected={x["code"]:_expected_row(x) for x in package.definitions}
            recheck={code:_reference(rows.get(code),expected[code]) for code in SUPPORTED_CODES}
            if any(x["action"]=="CONFLICT_STOP" for x in recheck.values()): raise RuntimeError("governed conflict during locked recheck")
            before=list(m.permissions); m.permissions=before+[x for x in PERMISSIONS if x not in before]
            for code in SUPPORTED_CODES:
                if code not in rows: db.session.add(ExternalReferenceType(**expected[code],revision=1,created_by_user_id=u.id,updated_by_user_id=u.id))
                else:
                    for field in ("lifecycle_status","allows_operational_shipment","allows_execution_unit"): setattr(rows[code],field,expected[code][field])
                    rows[code].updated_by_user_id=u.id
        return 0,{"result":"REPAIRED","mode":"execute","after":_plan(m,u),"permissions_added":[x for x in PERMISSIONS if x not in before],"UNRELATED_MEMBERSHIPS_TOUCHED":0,"UNRELATED_REFERENCE_TYPES_TOUCHED":0}
    except Exception as exc:
        db.session.rollback(); return 2,{"result":"REPAIR_ROLLED_BACK","error":type(exc).__name__}

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--user-identifier",required=True); p.add_argument("--environment-file",type=Path); mode=p.add_mutually_exclusive_group(required=True); mode.add_argument("--validate-only",action="store_true"); mode.add_argument("--execute",action="store_true"); p.add_argument("--confirm-repair"); a=p.parse_args(argv)
    if a.execute and a.confirm_repair!="REPAIR": p.error("--execute requires --confirm-repair REPAIR")
    if a.environment_file:
        if not a.environment_file.is_file(): p.error("production environment file was not found")
        load_dotenv(a.environment_file,override=True)
        if os.environ.get("APP_ENV","").lower() not in {"production","prod"}: p.error("environment file must identify Production")
    app=create_app(skip_startup=True)
    with app.app_context(): code,report=run(user_identifier=a.user_identifier,execute=a.execute)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True,default=str,indent=2)); return code
if __name__=="__main__": raise SystemExit(main())
