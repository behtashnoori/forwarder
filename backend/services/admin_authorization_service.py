"""Fail-closed authority and tenant context for administrative APIs."""
from dataclasses import dataclass
from functools import wraps
from flask import g, jsonify
from sqlalchemy import select
from backend.auth import get_current_user
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization
from backend.security import require_auth

PLATFORM_ADMIN = "PLATFORM_ADMIN"
ORGANIZATION_ADMIN = "ORGANIZATION_ADMIN"
EXPERT = "EXPERT"

class AdminAuthorizationError(Exception):
    def __init__(self, message, status_code=403):
        super().__init__(message); self.message, self.status_code = message, status_code

@dataclass(frozen=True)
class OrganizationContext:
    organization_id: int
    public_id: str
    membership_id: int

def effective_authority(user):
    authority = (getattr(user, "authority", None) or EXPERT).upper()
    return authority if authority in {PLATFORM_ADMIN, ORGANIZATION_ADMIN, EXPERT} else EXPERT

def organization_context_for_authenticated_user(user_id):
    user = db.session.get(ExpertUser, user_id)
    if not user or not user.is_active:
        raise AdminAuthorizationError("Active user required.")
    rows = db.session.execute(select(OperationalMembership, OperationalOrganization).join(
        OperationalOrganization, OperationalOrganization.id == OperationalMembership.organization_id
    ).where(OperationalMembership.user_id == user_id, OperationalMembership.is_active.is_(True))).all()
    if len(rows) != 1:
        raise AdminAuthorizationError("Exactly one active organization membership is required.")
    membership, organization = rows[0]
    if not organization.is_active:
        raise AdminAuthorizationError("Active organization required.")
    return OrganizationContext(int(organization.id), organization.public_id, int(membership.id))

def require_platform_admin():
    def decorator(fn):
        @wraps(fn)
        @require_auth
        def wrapped(*args, **kwargs):
            user = db.session.get(ExpertUser, g.current_user_id)
            if not user or not user.is_active or effective_authority(user) != PLATFORM_ADMIN:
                return jsonify({"error": "Platform administrator authority required."}), 403
            g.current_user, g.current_user_authority = get_current_user(), PLATFORM_ADMIN
            return fn(*args, **kwargs)
        return wrapped
    return decorator

def require_organization_admin_context(*, allow_platform=True):
    def decorator(fn):
        @wraps(fn)
        @require_auth
        def wrapped(*args, **kwargs):
            user = db.session.get(ExpertUser, g.current_user_id)
            authority = effective_authority(user) if user and user.is_active else EXPERT
            if allow_platform and authority == PLATFORM_ADMIN:
                g.organization_context = None
            elif authority == ORGANIZATION_ADMIN:
                try: g.organization_context = organization_context_for_authenticated_user(user.id)
                except AdminAuthorizationError as exc: return jsonify({"error": exc.message}), exc.status_code
            else:
                return jsonify({"error": "دسترسی غیرمجاز", "required_roles": ["admin"], "user_role": getattr(user, "role", None)}), 403
            g.current_user, g.current_user_authority = get_current_user(), authority
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def require_reporting_export_oversight():
    """Fail closed until the accepted reporting/export companion decision exists."""
    def decorator(fn):
        @wraps(fn)
        @require_auth
        def wrapped(*args, **kwargs):
            # Authenticate first, but intentionally expose no tenant/report metadata.
            return jsonify({
                "error": "Reporting and export oversight is not enabled by an accepted companion decision."
            }), 403
        return wrapped
    return decorator
