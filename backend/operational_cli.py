"""Explicit internal commands for operational reconciliation."""
from __future__ import annotations
import argparse
import os
import sys
from datetime import datetime, timezone
import bcrypt
from sqlalchemy import text
from backend import create_app
from backend.extensions import db
from backend.models import ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import CanonicalLocation, Milestone, MilestoneEvent, OperationalAudit, OperationalIdempotency, OperationalMembership, OperationalOrganization, OperationalOutbox, OperationalShipment, OperationalWorkItem, RouteLeg, RoutePlan
from backend.services.operational_service import OperationalError, reconcile_overdue


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command", required=True)
    reconcile=sub.add_parser("reconcile-overdue"); reconcile.add_argument("--organization-id", type=int, required=True); reconcile.add_argument("--confirm", action="store_true")
    bootstrap=sub.add_parser("bootstrap-organization"); bootstrap.add_argument("--name", required=True); bootstrap.add_argument("--user-id", type=int, required=True); bootstrap.add_argument("--permissions", required=True); bootstrap.add_argument("--confirm", action="store_true")
    scope_quote=sub.add_parser("scope-quote"); scope_quote.add_argument("--quote-id", type=int, required=True); scope_quote.add_argument("--organization-id", type=int, required=True); scope_quote.add_argument("--confirm", action="store_true")
    provision=sub.add_parser("provision-uat"); provision.add_argument("--confirm", action="store_true")
    cleanup=sub.add_parser("cleanup-uat"); cleanup.add_argument("--confirm", action="store_true")
    args=parser.parse_args(argv)
    if not args.confirm:
        print("Refusing operational write without --confirm.", file=sys.stderr); return 2
    if args.command in {"provision-uat","cleanup-uat"} and os.getenv("APP_ENV", "").lower() not in {"test","development"}:
        print("UAT commands are restricted to APP_ENV=test or development.", file=sys.stderr); return 2
    app=create_app(skip_startup=True)
    with app.app_context():
        if args.command == "provision-uat":
            password=os.getenv("FORWARDER_UAT_PASSWORD")
            if not password: print("FORWARDER_UAT_PASSWORD is required.",file=sys.stderr); return 2
            reporter_permissions=["operational_shipment.read","operational_shipment.create","milestone_event.create","work_item.read"]
            verifier_permissions=["operational_shipment.read","milestone.verify","milestone.correct","work_item.read","work_item.manage"]
            org=OperationalOrganization.query.filter_by(name="[PHASE1A-UAT] Organization").one_or_none() or OperationalOrganization(name="[PHASE1A-UAT] Organization")
            db.session.add(org); db.session.flush()
            users=[]
            for suffix,role,perms in (("reporter","expert",reporter_permissions),("verifier","manager",verifier_permissions),("readonly","expert",[]),("outsider","expert",[])):
                password_hash=bcrypt.hashpw(password.encode("utf-8"),bcrypt.gensalt()).decode("utf-8")
                user=ExpertUser.query.filter_by(username=f"phase1a_uat_{suffix}").one_or_none() or ExpertUser(username=f"phase1a_uat_{suffix}",password_hash=password_hash,full_name=f"[PHASE1A-UAT] {suffix.title()}",role=role,is_active=True)
                user.password_hash=password_hash; db.session.add(user); db.session.flush(); users.append(user)
                member_org=org
                if suffix=="outsider":
                    member_org=OperationalOrganization.query.filter_by(name="[PHASE1A-UAT] Other Organization").one_or_none() or OperationalOrganization(name="[PHASE1A-UAT] Other Organization");db.session.add(member_org);db.session.flush()
                membership=OperationalMembership.query.filter_by(organization_id=member_org.id,user_id=user.id).one_or_none() or OperationalMembership(organization_id=member_org.id,user_id=user.id)
                membership.permissions=perms;membership.is_active=True;db.session.add(membership)
            origin=Province.query.filter_by(code="P1AUATO").one_or_none() or Province(name_fa="[PHASE1A-UAT] Origin",code="P1AUATO");dest=Province.query.filter_by(code="P1AUATD").one_or_none() or Province(name_fa="[PHASE1A-UAT] Destination",code="P1AUATD");db.session.add_all([origin,dest]);db.session.flush()
            request_row=ShipmentRequest.query.filter_by(contact_phone="09000000101").one_or_none() or ShipmentRequest(contact_phone="09000000101",customer_first_name="Phase1A",customer_last_name="UAT",status="waiting_for_customer",status_request_status="new",assigned_to=users[0].id);db.session.add(request_row);db.session.flush()
            quote=ExpertQuote.query.filter_by(shipment_request_id=request_row.id,created_by_expert_id=users[0].id).one_or_none() or ExpertQuote(shipment_request_id=request_row.id,amount=100,currency="IRR",created_by_expert_id=users[0].id,created_at=datetime.now(timezone.utc));quote.customer_response="accepted";quote.responded_at=datetime.now(timezone.utc);quote.operational_organization_id=org.id;db.session.add(quote);db.session.commit();print(f"uat provisioned organization={org.id} quote={quote.id} origin={origin.id} destination={dest.id}")
        elif args.command == "cleanup-uat":
            orgs=OperationalOrganization.query.filter(OperationalOrganization.name.like("[PHASE1A-UAT]%")).all();org_ids=[o.id for o in orgs]
            users=ExpertUser.query.filter(ExpertUser.username.like("phase1a_uat_%")).all();user_ids=[u.id for u in users]
            requests=ShipmentRequest.query.filter_by(contact_phone="09000000101").all();request_ids=[r.id for r in requests]
            shipments=OperationalShipment.query.filter(OperationalShipment.organization_id.in_(org_ids)).all();shipment_ids=[s.id for s in shipments]
            plans=RoutePlan.query.filter(RoutePlan.operational_shipment_id.in_(shipment_ids)).all();plan_ids=[p.id for p in plans]
            legs=RouteLeg.query.filter(RouteLeg.route_plan_id.in_(plan_ids)).all();leg_ids=[l.id for l in legs]
            milestones=Milestone.query.filter(Milestone.route_leg_id.in_(leg_ids)).all();milestone_ids=[m.id for m in milestones]
            if milestone_ids:
                is_postgres=db.session.get_bind().dialect.name=="postgresql"
                if is_postgres: db.session.execute(text("ALTER TABLE milestone_event DISABLE TRIGGER trg_milestone_event_append_only"))
                MilestoneEvent.query.filter(MilestoneEvent.milestone_id.in_(milestone_ids)).delete(synchronize_session=False)
                if is_postgres: db.session.execute(text("ALTER TABLE milestone_event ENABLE TRIGGER trg_milestone_event_append_only"))
            if org_ids:
                OperationalWorkItem.query.filter(OperationalWorkItem.organization_id.in_(org_ids)).delete(synchronize_session=False);OperationalAudit.query.filter(OperationalAudit.organization_id.in_(org_ids)).delete(synchronize_session=False);OperationalOutbox.query.filter(OperationalOutbox.organization_id.in_(org_ids)).delete(synchronize_session=False);OperationalIdempotency.query.filter(OperationalIdempotency.organization_id.in_(org_ids)).delete(synchronize_session=False)
            for row in shipments: db.session.delete(row)
            ExpertQuote.query.filter(ExpertQuote.shipment_request_id.in_(request_ids)).delete(synchronize_session=False)
            for row in requests: db.session.delete(row)
            OperationalMembership.query.filter(OperationalMembership.organization_id.in_(org_ids)).delete(synchronize_session=False)
            for row in orgs: db.session.delete(row)
            OperationalMembership.query.filter(OperationalMembership.user_id.in_(user_ids)).delete(synchronize_session=False)
            for row in users: db.session.delete(row)
            CanonicalLocation.query.filter(CanonicalLocation.source_type=="province",CanonicalLocation.source_id.in_([p.id for p in Province.query.filter(Province.code.in_(["P1AUATO","P1AUATD"])).all()])).delete(synchronize_session=False)
            Province.query.filter(Province.code.in_(["P1AUATO","P1AUATD"])).delete(synchronize_session=False)
            db.session.commit();print("uat cleanup completed")
        elif args.command == "reconcile-overdue":
            count=reconcile_overdue(organization_id=args.organization_id); print(f"reconciled organization={args.organization_id} opened={count}")
        elif args.command == "bootstrap-organization":
            if db.session.get(ExpertUser, args.user_id) is None: raise OperationalError("RESOURCE_NOT_FOUND", "User was not found.", 404)
            permissions=sorted({value.strip() for value in args.permissions.split(",") if value.strip()})
            organization=OperationalOrganization(name=args.name.strip()); db.session.add(organization); db.session.flush(); db.session.add(OperationalMembership(organization_id=organization.id,user_id=args.user_id,permissions=permissions)); db.session.commit(); print(f"created organization={organization.id} membership_user={args.user_id}")
        else:
            quote=db.session.get(ExpertQuote,args.quote_id); organization=db.session.get(OperationalOrganization,args.organization_id)
            if quote is None or organization is None: raise OperationalError("RESOURCE_NOT_FOUND", "Quote or organization was not found.", 404)
            quote.operational_organization_id=organization.id; db.session.commit(); print(f"scoped quote={quote.id} organization={organization.id}")
    return 0


def run(argv=None):
    try: return main(argv)
    except OperationalError as exc: print(f"Operational command failed ({exc.code}).", file=sys.stderr); return 1
    except Exception: print("Operational command failed.", file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(run())
