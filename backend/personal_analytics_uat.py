"""Synthetic, idempotent Personal Analytics UAT fixture graph.

This module is deliberately separate from historical Phase 1B fixtures.  It
never discovers a target: callers must explicitly select an allow-listed test,
UAT, or approved staging database before invoking it.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy.engine import make_url

from backend import dashboard_service, saved_view_service
from backend.dashboard_models import Dashboard
from backend.extensions import db
from backend.models import Customer, ExpertQuote, ExpertUser, Province, ShipmentRequest
from backend.operational_models import (CanonicalLocation, OperationalMembership,
    OperationalOrganization, OperationalShipment, Project, ProjectAccess, RouteLeg,
    RoutePlan)
from backend.saved_view_models import SavedView
from backend.services.operational_service import OperationalError

PREFIX = "personal_analytics_uat_"
DATABASE_PREFIXES = (
    "forwarder_personal_analytics_uat",
    "forwarder_integrated_cert_personal_analytics_",
    "forwarder_staging_",
)
NOW = datetime(2041, 1, 1, 8, tzinfo=timezone.utc)
READ = ["operational_shipment.read", "personal_dashboard.manage", "personal_dashboard.read"]
DASHBOARD_ONLY = ["personal_dashboard.manage", "personal_dashboard.read"]
ADMIN = READ + ["project_configuration.manage"]


def _fail(message):
    raise OperationalError("UAT_ENVIRONMENT_REJECTED", message, 403)


def ensure_safe_target(app, database_url=None):
    environment = os.getenv("APP_ENV", "").strip().lower()
    if environment not in {"test", "uat", "staging"} or environment in {"production", "prod"}:
        _fail("Personal Analytics fixtures require APP_ENV=test, uat, or staging.")
    url = make_url(str(database_url or db.engine.url))
    if url.get_backend_name() == "sqlite":
        if not app.config.get("TESTING") or (url.database or "") != ":memory:":
            _fail("SQLite fixtures are limited to in-memory tests.")
        return
    if url.get_backend_name() != "postgresql":
        _fail("Personal Analytics fixtures require PostgreSQL outside tests.")
    name, host = (url.database or "").lower(), (url.host or "").lower()
    if any(marker in name for marker in ("production", "prod", "live")):
        _fail("Production-like database names are forbidden.")
    if not name.startswith(DATABASE_PREFIXES):
        _fail("Database name is not an allow-listed staging/UAT name.")
    loopback = host in {"localhost", "127.0.0.1", "::1"}
    approved = os.getenv("PERSONAL_ANALYTICS_UAT_APPROVED_STAGING", "").upper() == "YES"
    if not loopback and not (environment == "staging" and approved):
        _fail("Non-loopback targets require explicit approved staging identity.")


def _one(model, defaults=None, **identity):
    row = model.query.filter_by(**identity).one_or_none()
    if row is None:
        values = dict(defaults or {}); values.update(identity)
        row = model(**values); db.session.add(row); db.session.flush()
    return row


def _route(shipment, creator, origin, destination, offset):
    plan = _one(RoutePlan, {"status":"active", "is_active":True, "created_by_user_id":creator.id},
                operational_shipment_id=shipment.id, revision_number=1)
    _one(RouteLeg, {
        "origin_location_id":origin.id, "destination_location_id":destination.id,
        "origin_snapshot":{"display_name":origin.display_name},
        "destination_snapshot":{"display_name":destination.display_name}, "transport_mode":"road",
        "planned_departure":NOW + timedelta(hours=offset),
        "planned_arrival":NOW + timedelta(hours=offset + 1), "status":"planned",
    }, route_plan_id=plan.id, sequence_number=1)


def _definition():
    return {"schema_version":"saved-view-definition-v2", "semantic_version":"analytics-semantic-v2",
      "surface":"OPERATIONAL_SHIPMENTS", "query_definition":{"query_kind":"ROWSET",
      "semantic_version":"analytics-semantic-v2", "population":"SHIPMENTS",
      "columns":["CUSTOMER","ROUTE","PLANNED_TIME","PROJECT","MILESTONE","OPEN_WORK_ITEMS","SHIPMENT_STATUS"],
      "filters":[{"dimension":"SHIPMENT_STATUS","value":"planned"}],
      "operational_window":{"from":"2041-01-01T00:00:00+00:00","to":"2041-01-02T00:00:00+00:00"},
      "sort":{"field":"PLANNED_DEPARTURE","direction":"ASC"}, "limit":20},
      "presentation":{"display_type":"LIST"}}


def provision(app, password: str):
    """Provision only fixture-owned records, atomically and idempotently."""
    ensure_safe_target(app)
    if not password:
        _fail("A synthetic UAT password is required.")
    try:
        org_a = _one(OperationalOrganization, {"name":"[PA-UAT] Organization A"}, name="[PA-UAT] Organization A")
        org_b = _one(OperationalOrganization, {"name":"[PA-UAT] Organization B"}, name="[PA-UAT] Organization B")
        users = {}
        for key, org, authority, permissions in (
            ("expert_a", org_a, "EXPERT", READ), ("expert_b", org_a, "EXPERT", READ),
            ("expert_b_org", org_b, "EXPERT", READ),
            ("dashboard_only", org_a, "EXPERT", DASHBOARD_ONLY),
            ("admin_a", org_a, "ORGANIZATION_ADMIN", ADMIN), ("admin_b", org_b, "ORGANIZATION_ADMIN", ADMIN),
        ):
            password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            user = _one(ExpertUser, {"password_hash":password_hash, "full_name":f"[PA-UAT] {key}", "role":"expert", "authority":authority, "is_active":True}, username=PREFIX + key)
            user.password_hash = password_hash
            user.authority = authority; user.is_active = True
            membership = _one(OperationalMembership, {"permissions":permissions, "is_active":True}, organization_id=org.id, user_id=user.id)
            membership.permissions, membership.is_active = permissions, True; users[key] = user
        customer_a = _one(Customer, {"first_name":"Synthetic", "last_name":"Personal Analytics A", "status":"active", "operational_organization_id":org_a.id, "ownership_scope":"TENANT"}, phone="09000000991")
        customer_b = _one(Customer, {"first_name":"Synthetic", "last_name":"Personal Analytics B", "status":"active", "operational_organization_id":org_b.id, "ownership_scope":"TENANT"}, phone="09000000993")
        provinces = []
        for suffix in ("O", "D"):
            province = _one(Province, {"name_fa":f"[PA-UAT] {suffix}"}, code="PAU" + suffix)
            provinces.append(_one(CanonicalLocation, {"location_type":"province", "display_name":f"[PA-UAT] {suffix}"}, source_type="province", source_id=province.id))
        projects = {
            "a1": _one(Project, {"primary_customer_id":customer_a.id, "created_by_user_id":users["admin_a"].id}, organization_id=org_a.id, project_code="PA-UAT-A1"),
            "a2": _one(Project, {"primary_customer_id":customer_a.id, "created_by_user_id":users["admin_a"].id}, organization_id=org_a.id, project_code="PA-UAT-A2"),
            "b1": _one(Project, {"primary_customer_id":customer_b.id, "created_by_user_id":users["admin_b"].id}, organization_id=org_b.id, project_code="PA-UAT-B1"),
        }
        for user, project, admin in ((users["expert_a"], projects["a1"], users["admin_a"]), (users["expert_b"], projects["a2"], users["admin_a"])):
            _one(ProjectAccess, {"created_by_user_id":admin.id}, organization_id=project.organization_id, project_id=project.id, user_id=user.id)
        def direct(code, org, project, responsible, creator):
            return _one(OperationalShipment, {"organization_id":org.id, "project_id":project.id, "source_type":"direct", "customer_id":project.primary_customer_id, "lifecycle_status":"planned", "created_by_user_id":creator.id, "primary_responsible_expert_id":responsible.id}, public_id="00000000-0000-0000-0000-00000000" + code)
        shipments = {
            "project_only": direct("1001", org_a, projects["a1"], users["expert_b"], users["admin_a"]),
            "direct": direct("1002", org_a, projects["a1"], users["expert_a"], users["expert_a"]),
            "unauthorized": direct("1003", org_a, projects["a2"], users["expert_b"], users["admin_a"]),
            "cross_org": direct("1004", org_b, projects["b1"], users["expert_b_org"], users["admin_b"]),
        }
        request = _one(ShipmentRequest, {"status":"waiting_for_customer", "status_request_status":"new", "assigned_to":users["expert_a"].id, "customer_id":customer_a.id, "operational_organization_id":org_a.id, "ownership_scope":"TENANT"}, contact_phone="09000000992")
        quote = _one(ExpertQuote, {"amount":1000, "currency":"TST", "created_by_expert_id":users["expert_a"].id, "customer_response":"accepted", "operational_organization_id":org_a.id}, shipment_request_id=request.id, created_by_expert_id=users["expert_a"].id)
        shipments["request"] = _one(OperationalShipment, {"organization_id":org_a.id, "project_id":projects["a2"].id, "source_type":"accepted_quote", "shipment_request_id":request.id, "accepted_quote_id":quote.id, "lifecycle_status":"planned", "created_by_user_id":users["expert_a"].id, "primary_responsible_expert_id":users["expert_a"].id}, public_id="00000000-0000-0000-0000-000000001005")
        for offset, shipment in enumerate(shipments.values()): _route(shipment, users["admin_a"] if shipment.organization_id == org_a.id else users["admin_b"], provinces[0], provinces[1], offset)
        actor = {"id":users["expert_a"].id}
        view_row = SavedView.query.filter_by(organization_id=org_a.id, owner_user_id=users["expert_a"].id, name="[PA-UAT] Expert A shipments").one_or_none()
        view = saved_view_service.serialize(view_row) if view_row else saved_view_service.create({"name":"[PA-UAT] Expert A shipments", "definition":_definition()}, actor)
        dashboard_row = Dashboard.query.filter_by(organization_id=org_a.id, owner_user_id=users["expert_a"].id, name="[PA-UAT] Expert A dashboard").one_or_none()
        dashboard = dashboard_service.serialize(dashboard_row) if dashboard_row else dashboard_service.clone("operations-control-tower", actor, "[PA-UAT] Expert A dashboard")
        db.session.commit()
    except Exception:
        db.session.rollback(); raise
    return {"organizations":2, "users":6, "projects":3, "project_access":2, "shipments":5,
            "saved_view_public_id":view["public_id"], "dashboard_public_id":dashboard["public_id"],
            "shipment_public_ids":{key:value.public_id for key,value in shipments.items()}}
