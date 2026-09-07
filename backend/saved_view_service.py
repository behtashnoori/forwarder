"""Tenant- and owner-scoped personal Saved View persistence."""
from copy import deepcopy

from sqlalchemy import select

from backend.extensions import db
from backend.saved_view_models import SavedView, SavedViewRevision
from backend.saved_view_validation import SAVED_VIEW_SCHEMA_VERSION, align_v1_to_v2, runtime_definition, validate
from backend.services.operational_service import OperationalError, organization_for_user, require_permission


def _context(user):
    require_permission(user, "operational_shipment.read")
    return organization_for_user(int(user["id"])), int(user["id"])


def _get(public_id, user, include_archived=True):
    org, uid = _context(user)
    query = select(SavedView).where(SavedView.public_id == public_id, SavedView.organization_id == org, SavedView.owner_user_id == uid)
    if not include_archived:
        query = query.where(SavedView.status == "ACTIVE")
    row = db.session.scalar(query)
    if not row:
        raise OperationalError("SAVED_VIEW_NOT_FOUND", "Saved view not found.", 404)
    return row


def _revision(row, actor, reason=None):
    db.session.add(SavedViewRevision(saved_view_id=row.id, revision_number=row.version, definition_json=deepcopy(row.definition_json), semantic_version=row.semantic_version, saved_view_schema_version=row.saved_view_schema_version, name_snapshot=row.name, description_snapshot=row.description, changed_by=actor, change_reason=reason))


def serialize(row):
    data = {key: getattr(row, key) for key in ("public_id", "name", "description", "visibility", "status", "semantic_version", "saved_view_schema_version", "version", "created_at", "updated_at")} | {"definition": deepcopy(row.definition_json)}
    try:
        data["runtime_definition"] = runtime_definition(row.definition_json)
        data["compatibility_state"] = "COMPATIBLE"
    except ValueError as exc:
        data["compatibility_state"] = getattr(exc, "code", "INCOMPATIBLE_LEGACY_DEFINITION")
    return data


def list_(user, archived_only=False):
    org, uid = _context(user)
    query = select(SavedView).where(SavedView.organization_id == org, SavedView.owner_user_id == uid)
    query = query.where(SavedView.status == ("ARCHIVED" if archived_only else "ACTIVE"))
    return [serialize(row) for row in db.session.scalars(query.order_by(SavedView.updated_at.desc())).all()]


def get(public_id, user):
    return serialize(_get(public_id, user))


def create(payload, user):
    if set(payload) - {"name", "description", "definition"}:
        raise OperationalError("IMMUTABLE_SAVED_VIEW_FIELD", "Ownership and lifecycle fields are server-controlled.", 422)
    name, description = payload.get("name"), payload.get("description", "")
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        raise OperationalError("INVALID_NAME", "name must be 1-120 characters.", 422)
    if not isinstance(description, str) or len(description) > 1000:
        raise OperationalError("INVALID_DESCRIPTION", "description exceeds 1000 characters.", 422)
    definition = validate(payload.get("definition"))
    org, uid = _context(user)
    row = SavedView(organization_id=org, owner_user_id=uid, name=name.strip(), description=description, semantic_version=definition["semantic_version"], saved_view_schema_version=definition["schema_version"], definition_json=definition, created_by=uid, updated_by=uid)
    db.session.add(row); db.session.flush(); _revision(row, uid, "create"); db.session.commit()
    return serialize(row)


def update(public_id, payload, user):
    row = _get(public_id, user, include_archived=False)
    expected = payload.get("expected_version")
    if isinstance(expected, bool) or not isinstance(expected, int):
        raise OperationalError("EXPECTED_VERSION_REQUIRED", "expected_version is required.", 422)
    if expected != row.version:
        raise OperationalError("SAVED_VIEW_VERSION_CONFLICT", f"current_version={row.version}; updated_at={row.updated_at.isoformat()}", 409)
    if set(payload) - {"expected_version", "name", "description", "definition", "change_reason"}:
        raise OperationalError("IMMUTABLE_SAVED_VIEW_FIELD", "Ownership and lifecycle fields cannot be changed.", 422)
    next_name, next_description, next_definition = row.name, row.description, deepcopy(row.definition_json)
    if "name" in payload:
        if not isinstance(payload["name"], str) or not payload["name"].strip() or len(payload["name"]) > 120:
            raise OperationalError("INVALID_NAME", "name must be 1-120 characters.", 422)
        next_name = payload["name"].strip()
    if "description" in payload:
        if not isinstance(payload["description"], str) or len(payload["description"]) > 1000:
            raise OperationalError("INVALID_DESCRIPTION", "description exceeds 1000 characters.", 422)
        next_description = payload["description"]
    if "definition" in payload:
        next_definition = validate(payload["definition"])
    reason = payload.get("change_reason")
    if reason is not None and (not isinstance(reason, str) or len(reason) > 255):
        raise OperationalError("INVALID_CHANGE_REASON", "change_reason exceeds 255 characters.", 422)
    # Clicking update on an untouched v1 view must not create a conversion-only
    # revision: compare its deterministic runtime v2 representation.
    if row.definition_json.get("schema_version") == SAVED_VIEW_SCHEMA_VERSION and next_definition.get("schema_version") != SAVED_VIEW_SCHEMA_VERSION:
        try:
            if next_definition == align_v1_to_v2(row.definition_json) and (next_name, next_description) == (row.name, row.description): return serialize(row)
        except ValueError:
            pass
    if (next_name, next_description, next_definition) == (row.name, row.description, row.definition_json):
        return serialize(row)
    row.name, row.description, row.definition_json = next_name, next_description, next_definition
    row.semantic_version, row.saved_view_schema_version = next_definition["semantic_version"], next_definition["schema_version"]
    row.version += 1; row.updated_by = int(user["id"]); _revision(row, int(user["id"]), reason); db.session.commit()
    return serialize(row)


def lifecycle(public_id, payload, user, status):
    row = _get(public_id, user)
    expected = payload.get("expected_version")
    if expected != row.version:
        raise OperationalError("SAVED_VIEW_VERSION_CONFLICT", f"current_version={row.version}; updated_at={row.updated_at.isoformat()}", 409)
    if row.status == status:
        return serialize(row)
    row.status = status; row.updated_by = int(user["id"]); db.session.commit()
    return serialize(row)

def dashboard_snapshot(public_id, payload, user):
    row = _get(public_id, user, include_archived=False)
    runtime = runtime_definition(row.definition_json)
    query = runtime.get("query_definition", {})
    if query.get("query_kind") != "ROWSET" or query.get("population") != "SHIPMENTS":
        raise OperationalError("SAVED_VIEW_SNAPSHOT_INCOMPATIBLE", "Saved view is not a compatible Shipment ROWSET.", 422)
    from backend import dashboard_service
    return dashboard_service.add_saved_view_snapshot(row, runtime, payload, user)
