"""Explicit internal commands for operational reconciliation."""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
import bcrypt
from sqlalchemy import text
from sqlalchemy.engine import make_url
from backend import create_app
from backend.extensions import db
from backend.models import ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import CanonicalLocation, Milestone, MilestoneEvent, OperationalAudit, OperationalCheckpoint, OperationalIdempotency, OperationalMembership, OperationalOrganization, OperationalOutbox, OperationalShipment, OperationalWorkItem, RouteDependency, RouteLeg, RoutePlan
from backend.services.operational_service import OperationalError, reconcile_overdue


PHASE1B_PREFIX = "phase1b_uat_"
PHASE1B_DATABASE_PREFIXES = ("forwarder_phase1b_uat", "phase1b_uat")
PHASE1B_NOW = datetime(2030, 1, 15, 12, 0, tzinfo=timezone.utc)
PHASE1B_ALL_PERMISSIONS = [
    "operational_shipment.read", "operational_shipment.create",
    "milestone_event.create", "milestone.verify", "milestone.correct",
    "work_item.read", "work_item.manage", "route_plan.read",
    "route_plan.create", "route_plan.activate", "route_plan.replan",
    "route_leg.manage", "checkpoint.read", "checkpoint.report",
    "checkpoint.verify", "route_exception.read", "route_exception.manage",
]


def _phase1b_seed_guard(app, database_url=None) -> None:
    environment = os.getenv("APP_ENV", "").strip().lower()
    if environment not in {"test", "uat", "development"}:
        raise OperationalError("UAT_ENVIRONMENT_REJECTED", "Phase 1B seed requires an explicit test/UAT environment.", 403)
    if environment in {"production", "prod"} or app.config.get("ENV") == "production":
        raise OperationalError("UAT_ENVIRONMENT_REJECTED", "Production is not a seed target.", 403)
    url = make_url(str(database_url or db.engine.url))
    if url.get_backend_name() == "sqlite":
        database = url.database or ""
        if not app.config.get("TESTING") or database != ":memory:":
            raise OperationalError("UAT_DATABASE_REJECTED", "SQLite seed targets are limited to in-memory tests.", 403)
        return
    if url.get_backend_name() != "postgresql":
        raise OperationalError("UAT_DATABASE_REJECTED", "Phase 1B seed requires PostgreSQL.", 403)
    if (url.host or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise OperationalError("UAT_DATABASE_REJECTED", "Phase 1B seed database must be loopback-only.", 403)
    if not any((url.database or "").lower().startswith(prefix) for prefix in PHASE1B_DATABASE_PREFIXES):
        raise OperationalError("UAT_DATABASE_REJECTED", "Phase 1B seed database name is not allow-listed.", 403)


def _one_or_create(model, defaults=None, **identity):
    row = model.query.filter_by(**identity).one_or_none()
    if row is None:
        row = model(**identity, **(defaults or {}))
        db.session.add(row)
        db.session.flush()
    return row


def seed_phase1b_uat(app, password: str) -> dict:
    """Create the synthetic Phase 1B UAT graph in one idempotent transaction."""
    _phase1b_seed_guard(app)
    try:
        org_a = _one_or_create(OperationalOrganization, name="[PHASE1B-UAT] Organization A")
        org_b = _one_or_create(OperationalOrganization, name="[PHASE1B-UAT] Organization B")
        roles = (
            ("admin", org_a, PHASE1B_ALL_PERMISSIONS, True, "manager"),
            ("operations", org_a, PHASE1B_ALL_PERMISSIONS, True, "manager"),
            ("reporter", org_a, ["operational_shipment.read", "milestone_event.create", "route_plan.read", "checkpoint.read", "checkpoint.report", "route_exception.read", "work_item.read"], True, "expert"),
            ("verifier", org_a, ["operational_shipment.read", "milestone.verify", "milestone.correct", "route_plan.read", "checkpoint.read", "checkpoint.verify", "route_exception.read", "work_item.read"], True, "manager"),
            ("readonly", org_a, ["operational_shipment.read", "route_plan.read", "checkpoint.read", "route_exception.read", "work_item.read"], True, "expert"),
            ("no_permission", org_a, [], True, "expert"),
            ("inactive", org_a, PHASE1B_ALL_PERMISSIONS, False, "expert"),
            ("org_b_admin", org_b, PHASE1B_ALL_PERMISSIONS, True, "manager"),
        )
        users = {}
        for suffix, organization, permissions, active_member, role in roles:
            username = f"{PHASE1B_PREFIX}{suffix}"
            user = ExpertUser.query.filter_by(username=username).one_or_none()
            if user is None:
                user = ExpertUser(
                    username=username,
                    password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                    full_name=f"[PHASE1B-UAT] {suffix.replace('_', ' ').title()}",
                    role=role, is_active=True,
                )
                db.session.add(user); db.session.flush()
            membership = _one_or_create(OperationalMembership, organization_id=organization.id, user_id=user.id)
            membership.permissions = list(permissions)
            membership.is_active = active_member
            users[suffix] = user

        provinces = []
        for index in range(1, 5):
            province = _one_or_create(
                Province,
                defaults={"name_fa": f"[PHASE1B-UAT] Location {index}"},
                code=f"P1BU{index}",
            )
            location = _one_or_create(
                CanonicalLocation,
                defaults={"location_type": "province", "display_name": f"[PHASE1B-UAT] Location {index}", "country_code": "TST"},
                source_type="province", source_id=province.id,
            )
            provinces.append(location)

        shipments = []
        for org_key, organization, creator, phone in (
            ("A", org_a, users["admin"], "09000000201"),
            ("B", org_b, users["org_b_admin"], "09000000202"),
        ):
            request_row = _one_or_create(
                ShipmentRequest,
                defaults={"customer_first_name": "Synthetic", "customer_last_name": f"UAT {org_key}",
                          "status": "waiting_for_customer", "status_request_status": "new", "assigned_to": creator.id},
                contact_phone=phone,
            )
            quote = ExpertQuote.query.filter_by(shipment_request_id=request_row.id, created_by_expert_id=creator.id).one_or_none()
            if quote is None:
                quote = ExpertQuote(shipment_request_id=request_row.id, amount=1000, currency="TST",
                                    created_by_expert_id=creator.id, created_at=PHASE1B_NOW,
                                    customer_response="accepted", responded_at=PHASE1B_NOW,
                                    operational_organization_id=organization.id)
                db.session.add(quote); db.session.flush()
            shipment = _one_or_create(
                OperationalShipment,
                defaults={"organization_id": organization.id, "shipment_request_id": request_row.id,
                          "lifecycle_status": "in_progress", "created_by_user_id": creator.id},
                accepted_quote_id=quote.id,
            )
            plan = _one_or_create(
                RoutePlan,
                defaults={"status": "active", "is_active": True, "effective_at": PHASE1B_NOW,
                          "created_by_user_id": creator.id},
                operational_shipment_id=shipment.id, revision_number=1,
            )
            legs = []
            for sequence in range(1, 4):
                departure = PHASE1B_NOW + timedelta(days=(sequence - 1) * 2)
                leg = _one_or_create(
                    RouteLeg,
                    defaults={"origin_location_id": provinces[sequence - 1].id,
                              "destination_location_id": provinces[sequence].id,
                              "origin_snapshot": {"display_name": provinces[sequence - 1].display_name},
                              "destination_snapshot": {"display_name": provinces[sequence].display_name},
                              "transport_mode": ("road", "rail", "sea")[sequence - 1],
                              "planned_departure": departure, "planned_arrival": departure + timedelta(days=1),
                              "status": "completed" if sequence == 1 else "planned",
                              "actual_departure": departure if sequence == 1 else None,
                              "actual_arrival": departure + timedelta(days=1) if sequence == 1 else None},
                    route_plan_id=plan.id, sequence_number=sequence,
                )
                legs.append(leg)
            checkpoints = []
            checkpoint_specs = (
                (1, 1, "origin_loading"), (2, 1, "export_customs"),
                (3, 2, "transit_border_entry"), (4, 2, "transit_border_exit"),
                (5, 3, "import_customs"), (6, 3, "final_delivery"),
            )
            for sequence, leg_number, checkpoint_type in checkpoint_specs:
                planned = PHASE1B_NOW + timedelta(hours=12 * (sequence - 1))
                completed = org_key == "A" and sequence <= 2
                checkpoint = _one_or_create(
                    OperationalCheckpoint,
                    defaults={"route_leg_id": legs[leg_number - 1].id, "checkpoint_type": checkpoint_type,
                              "canonical_location_id": provinces[min(leg_number, 3)].id,
                              "planned_arrival_at": planned, "planned_departure_at": planned + timedelta(hours=2),
                              "actual_arrival_at": planned if completed else None,
                              "actual_departure_at": planned + timedelta(hours=2) if completed else None,
                              "status": "completed" if completed else ("blocked" if sequence == 5 else "planned"),
                              "verification_state": "verified" if completed else "planned",
                              "responsible_party": "[PHASE1B-UAT] Synthetic Operator",
                              "created_by_user_id": creator.id},
                    route_plan_id=plan.id, sequence_number=sequence,
                )
                checkpoints.append(checkpoint)
                for offset, milestone_type in enumerate(("checkpoint_arrival", "checkpoint_processing_complete", "checkpoint_departure")):
                    milestone = _one_or_create(
                        Milestone,
                        defaults={"organization_id": shipment.organization_id,
                                  "operational_shipment_id": shipment.id,
                                  "route_plan_id": plan.id, "planned_at": planned + timedelta(hours=offset),
                                  "occurred_at": planned + timedelta(hours=offset) if completed else None,
                                  "verification_state": "verified" if completed else "planned"},
                        checkpoint_id=checkpoint.id, milestone_type=milestone_type,
                    )
                    if completed:
                        reported = _one_or_create(
                            MilestoneEvent,
                            defaults={
                                "organization_id": shipment.organization_id,
                                "event_type": "reported",
                                "occurred_at": planned + timedelta(hours=offset),
                                "recorded_at": planned + timedelta(hours=offset),
                                "actor_user_id": users["reporter"].id,
                                "request_hash": "0" * 64,
                            },
                            milestone_id=milestone.id,
                            idempotency_key=f"phase1b-uat-report-{sequence}-{offset}",
                        )
                        _one_or_create(
                            MilestoneEvent,
                            defaults={
                                "organization_id": shipment.organization_id,
                                "event_type": "verified",
                                "occurred_at": planned + timedelta(hours=offset),
                                "recorded_at": planned + timedelta(hours=offset, minutes=5),
                                "actor_user_id": users["verifier"].id,
                                "supersedes_event_id": reported.id,
                                "request_hash": "1" * 64,
                            },
                            milestone_id=milestone.id,
                            idempotency_key=f"phase1b-uat-verify-{sequence}-{offset}",
                        )
            # Includes a chain (1->2->3), fan-out (2->3,2->4), and fan-in (3->5,4->5).
            for predecessor, successor in ((1, 2), (2, 3), (2, 4), (3, 5), (4, 5), (5, 6)):
                _one_or_create(RouteDependency, route_plan_id=plan.id,
                               predecessor_checkpoint_id=checkpoints[predecessor - 1].id,
                               successor_checkpoint_id=checkpoints[successor - 1].id,
                               dependency_type="finish_to_start")
            if org_key == "A":
                for work_type, checkpoint, reason in (
                    ("CHECKPOINT_OVERDUE", checkpoints[3], "[PHASE1B-UAT] Overdue checkpoint."),
                    ("ROUTE_DEPENDENCY_BLOCKED", checkpoints[4], "[PHASE1B-UAT] Dependency-blocked checkpoint."),
                ):
                    _one_or_create(
                        OperationalWorkItem,
                        defaults={"organization_id": organization.id, "operational_shipment_id": shipment.id,
                                  "severity": "warning", "detected_at": PHASE1B_NOW,
                                  "due_at": PHASE1B_NOW - timedelta(hours=1),
                                  "reason": reason, "status": "open"},
                        route_plan_id=plan.id, checkpoint_id=checkpoint.id, work_type=work_type,
                    )
            shipments.append(shipment)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return {
        "organizations": 2, "users": len(users), "shipments": len(shipments),
        "route_plans": 2, "route_legs": 6, "checkpoints": 12,
        "dependencies": 12, "milestones": 36, "milestone_events": 12,
        "open_work_items": 2,
    }


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command", required=True)
    reconcile=sub.add_parser("reconcile-overdue"); reconcile.add_argument("--organization-id", type=int, required=True); reconcile.add_argument("--confirm", action="store_true")
    bootstrap=sub.add_parser("bootstrap-organization"); bootstrap.add_argument("--name", required=True); bootstrap.add_argument("--user-id", type=int, required=True); bootstrap.add_argument("--permissions", required=True); bootstrap.add_argument("--confirm", action="store_true")
    scope_quote=sub.add_parser("scope-quote"); scope_quote.add_argument("--quote-id", type=int, required=True); scope_quote.add_argument("--organization-id", type=int, required=True); scope_quote.add_argument("--confirm", action="store_true")
    provision=sub.add_parser("provision-uat"); provision.add_argument("--confirm", action="store_true")
    phase1b=sub.add_parser("seed-phase1b-uat"); phase1b.add_argument("--confirm", action="store_true")
    cleanup=sub.add_parser("cleanup-uat"); cleanup.add_argument("--confirm", action="store_true")
    args=parser.parse_args(argv)
    if not args.confirm:
        print("Refusing operational write without --confirm.", file=sys.stderr); return 2
    if args.command in {"provision-uat","cleanup-uat"} and os.getenv("APP_ENV", "").lower() not in {"test","development"}:
        print("UAT commands are restricted to APP_ENV=test or development.", file=sys.stderr); return 2
    app=create_app(skip_startup=True)
    with app.app_context():
        if args.command == "seed-phase1b-uat":
            password=os.getenv("FORWARDER_UAT_PASSWORD")
            if not password:
                print("FORWARDER_UAT_PASSWORD is required.", file=sys.stderr); return 2
            summary=seed_phase1b_uat(app, password)
            print(json.dumps({"command": "seed-phase1b-uat", "result": "ready", **summary}, sort_keys=True))
        elif args.command == "provision-uat":
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
