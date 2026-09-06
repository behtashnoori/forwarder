"""Personal dashboard persistence and source-controlled system-dashboard catalog."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from sqlalchemy import select
from backend.extensions import db
from backend.dashboard_models import Dashboard, DashboardRevision
from backend.dashboard_validation import validate
from backend.services.operational_service import organization_for_user, require_permission, OperationalError

_MANIFEST_PATH = Path(__file__).resolve().parents[1] / "contracts" / "dashboard" / "system" / "operations-control-tower.v1.json"

def _catalog():
    """Load and fail closed on the repository contract; never use the process cwd."""
    try:
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        required = {"system_dashboard_id", "system_version", "semantic_version", "dashboard_schema_version", "definition"}
        if not required.issubset(manifest) or not isinstance(manifest["system_version"], int): raise ValueError("missing required manifest fields")
        definition = validate(deepcopy(manifest["definition"]))
        if definition["semantic_version"] != manifest["semantic_version"]: raise ValueError("manifest semantic version differs from definition")
        return manifest | {"definition": definition}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid canonical system dashboard manifest at {_MANIFEST_PATH}: {exc}") from exc

def system_dashboard(system_id):
    manifest = _catalog()
    if system_id != manifest["system_dashboard_id"]: raise OperationalError("SYSTEM_DASHBOARD_NOT_FOUND", "System dashboard not found.", 404)
    return manifest

def _org_user(user): return organization_for_user(int(user["id"])), int(user["id"])
def _get(public_id, user, include_archived=True):
    org, uid = _org_user(user); q = select(Dashboard).where(Dashboard.public_id == public_id, Dashboard.organization_id == org, Dashboard.owner_user_id == uid)
    if not include_archived: q = q.where(Dashboard.status == "ACTIVE")
    row = db.session.scalar(q)
    if not row: raise OperationalError("DASHBOARD_NOT_FOUND", "Dashboard not found.", 404)
    return row
def _revision(row, actor, reason=None): db.session.add(DashboardRevision(dashboard_id=row.id, revision_number=row.version, definition_json=deepcopy(row.definition_json), semantic_version=row.semantic_version, dashboard_schema_version=row.dashboard_schema_version, name_snapshot=row.name, description_snapshot=row.description, changed_by=actor, change_reason=reason))
def serialize(row): return {k: getattr(row, k) for k in ("public_id", "dashboard_type", "name", "description", "visibility", "status", "semantic_version", "dashboard_schema_version", "version", "source_dashboard_public_id", "source_version", "source_type", "cloned_at", "created_at", "updated_at")} | {"definition": row.definition_json}

def clone(system_id, user, name=None):
    require_permission(user, "operational_shipment.read")
    template = system_dashboard(system_id); org, uid = _org_user(user); definition = deepcopy(template["definition"]); now = datetime.now(timezone.utc)
    row = Dashboard(organization_id=org, owner_user_id=uid, name=name or definition["name"], description=definition["description"], semantic_version=template["semantic_version"], dashboard_schema_version=template["dashboard_schema_version"], definition_json=definition, source_dashboard_public_id=template["system_dashboard_id"], source_version=template["system_version"], source_type="SYSTEM", cloned_at=now, created_by=uid, updated_by=uid)
    db.session.add(row); db.session.flush(); _revision(row, uid, "clone"); db.session.commit(); return serialize(row)
def list_(user):
    org, uid = _org_user(user)
    return [serialize(x) for x in db.session.scalars(select(Dashboard).where(Dashboard.organization_id == org, Dashboard.owner_user_id == uid, Dashboard.status == "ACTIVE").order_by(Dashboard.updated_at.desc())).all()]
def get(public_id, user): return serialize(_get(public_id, user))
def update(public_id, payload, user):
    row = _get(public_id, user); expected = payload.get("expected_version")
    if not isinstance(expected, int): raise OperationalError("EXPECTED_VERSION_REQUIRED", "expected_version is required.", 422)
    if expected != row.version: raise OperationalError("DASHBOARD_VERSION_CONFLICT", f"current_version={row.version}; updated_at={row.updated_at.isoformat()}", 409)
    mutable = {"definition", "name", "description"}
    if not mutable.intersection(payload): raise OperationalError("EMPTY_DASHBOARD_PATCH", "At least one mutable dashboard field is required.", 422)
    if "definition" in payload:
        definition = validate(payload["definition"])
        if definition.get("name") != row.definition_json.get("name") or definition.get("description") != row.definition_json.get("description"): raise OperationalError("DASHBOARD_PRESENTATION_IDENTITY_IMMUTABLE", "Use name/description fields for dashboard identity.", 422)
        row.definition_json = deepcopy(definition)
    if "name" in payload:
        if not isinstance(payload["name"], str) or not payload["name"] or len(payload["name"]) > 120: raise OperationalError("INVALID_NAME", "name must be 1-120 characters.", 422)
        row.name = payload["name"]
    if "description" in payload:
        if not isinstance(payload["description"], str) or len(payload["description"]) > 1000: raise OperationalError("INVALID_DESCRIPTION", "description exceeds 1000 characters.", 422)
        row.description = payload["description"]
    if "change_reason" in payload and (not isinstance(payload["change_reason"], str) or len(payload["change_reason"]) > 255): raise OperationalError("INVALID_CHANGE_REASON", "change_reason exceeds 255 characters.", 422)
    row.version += 1; row.updated_by = int(user["id"]); _revision(row, int(user["id"]), payload.get("change_reason")); db.session.commit(); return serialize(row)
def lifecycle(public_id, user, status):
    row = _get(public_id, user); row.status = status; row.updated_by = int(user["id"]); db.session.commit(); return serialize(row)
