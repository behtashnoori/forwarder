"""Service helpers for user-management user CRUD endpoints."""
from __future__ import annotations

from typing import Any

import bcrypt
from sqlalchemy import and_

from backend.extensions import db
from backend.models import ExpertSpecialization, ExpertUser
from backend.operational_models import OperationalMembership


class UserValidationError(Exception):
    """Validation failure that maps to the current user-management 400 response."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UserNotFoundError(Exception):
    """Raised when the requested user does not exist."""


def build_user_specialization_payload(specialization: ExpertSpecialization) -> dict[str, Any]:
    """Build the current specialization payload nested under a user."""
    payload = {
        "id": specialization.id,
        "transport_method": {
            "id": specialization.transport_method.id,
            "name": specialization.transport_method.name_fa,
        },
        "proficiency_level": specialization.proficiency_level,
        "is_primary": specialization.is_primary,
    }
    return payload


def build_user_payload(user: ExpertUser, *, workload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the current user-management user response item shape."""
    manager_info = None
    if user.manager:
        manager_info = {
            "id": user.manager.id,
            "name": user.manager.full_name,
        }

    subordinates_count = len(user.subordinates) if user.subordinates else 0

    payload = {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "department": user.department,
        "is_active": user.is_active,
        "can_handle_domestic": user.can_handle_domestic,
        "can_handle_international": user.can_handle_international,
        "sla_response_work_minutes": user.sla_response_work_minutes,
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "manager": manager_info,
        "subordinates_count": subordinates_count,
        "specializations": [
            build_user_specialization_payload(specialization)
            for specialization in user.specializations
        ],
        "workload": workload["active_count"] if workload is not None else user.get_workload(),
    }
    if workload is not None:
        payload["workload_detail"] = workload
    return payload


def list_users_payload(context=None) -> list[dict[str, Any]]:
    """List all users in the current full_name order."""
    query = db.session.query(ExpertUser)
    if context is not None:
        query = query.join(OperationalMembership, OperationalMembership.user_id == ExpertUser.id).filter(OperationalMembership.organization_id == context.organization_id, OperationalMembership.is_active.is_(True))
    users = query.order_by(ExpertUser.full_name).all()
    if context is None:
        return [build_user_payload(user) for user in users]
    from backend.services.expert_workload_service import organization_workloads, workload_payload
    counts = organization_workloads(context.organization_id, [user.id for user in users])
    return [
        build_user_payload(
            user,
            workload=workload_payload(context.organization_id, user, counts.get(user.id, 0)),
        )
        for user in users
    ]


def normalize_optional_create_string(value: Any, *, lowercase: bool = False) -> str | None:
    """Preserve create-time optional string normalization semantics."""
    if not value or not str(value).strip():
        return None

    normalized = str(value).strip()
    if lowercase:
        normalized = normalized.lower()
    return normalized


def hash_password(password: str) -> str:
    """Hash a password using the existing bcrypt settings."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def add_user_specializations(user_id: int, specializations: list[dict[str, Any]]) -> None:
    """Add specializations using the current defaults."""
    for spec_data in specializations:
        specialization = ExpertSpecialization(
            expert_user_id=user_id,
            transport_method_id=spec_data.get("transport_method_id"),
            proficiency_level=spec_data.get("proficiency_level", "intermediate"),
            is_primary=spec_data.get("is_primary", False),
        )
        db.session.add(specialization)


def create_user(payload: dict[str, Any], context=None) -> ExpertUser:
    """Create and commit a user using the current route behavior."""
    data = payload
    if context is not None and str(data.get("authority", "EXPERT")).upper() != "EXPERT":
        raise UserValidationError("Organization administrators cannot grant administrative authority.")
    if str(data.get("role", "")).lower() == "admin":
        raise UserValidationError("Administrative roles require controlled onboarding.")

    if not data.get("username"):
        raise UserValidationError("نام کاربری الزامی است")
    if not data.get("password"):
        raise UserValidationError("رمز عبور الزامی است")
    if not data.get("full_name"):
        raise UserValidationError("نام کامل الزامی است")
    if not data.get("role"):
        raise UserValidationError("نقش کاربر الزامی است")

    existing_user = ExpertUser.query.filter_by(username=data.get("username")).first()
    if existing_user:
        raise UserValidationError("نام کاربری قبلاً استفاده شده است")

    validate_expert_scope(
        data.get("role"),
        data.get("is_active", True),
        {
            "can_handle_domestic": data.get("can_handle_domestic", True),
            "can_handle_international": data.get("can_handle_international", True),
        },
    )
    sla_minutes = validate_sla_minutes(data.get("sla_response_work_minutes", 120))

    user = ExpertUser(
        username=data.get("username"),
        password_hash=hash_password(data.get("password")),
        full_name=data.get("full_name"),
        email=normalize_optional_create_string(data.get("email"), lowercase=True),
        phone=normalize_optional_create_string(data.get("phone")),
        role=data.get("role"),
        department=normalize_optional_create_string(data.get("department")),
        manager_id=data.get("manager_id"),
        is_active=data.get("is_active", True),
        can_handle_domestic=data.get("can_handle_domestic", True),
        can_handle_international=data.get("can_handle_international", True),
        sla_response_work_minutes=sla_minutes,
    )

    db.session.add(user)
    db.session.flush()
    if context is not None:
        if data.get("manager_id") and not user_in_organization(data["manager_id"], context.organization_id):
            raise UserValidationError("Manager must belong to the same organization.")
        db.session.add(OperationalMembership(organization_id=context.organization_id, user_id=user.id, is_active=True, permissions=[]))
    add_user_specializations(user.id, data.get("specializations", []))
    db.session.commit()
    return user


def get_user_or_raise(user_id: int, context=None) -> ExpertUser:
    """Return a user or raise the current not-found route outcome."""
    query = db.session.query(ExpertUser)
    if context is not None:
        query = query.join(OperationalMembership, OperationalMembership.user_id == ExpertUser.id).filter(OperationalMembership.organization_id == context.organization_id, OperationalMembership.is_active.is_(True))
    user = query.filter(ExpertUser.id == user_id).one_or_none()
    if not user:
        raise UserNotFoundError()
    return user


def replace_user_specializations(user_id: int, specializations: list[dict[str, Any]]) -> None:
    """Replace specializations using the current delete-then-add behavior."""
    db.session.query(ExpertSpecialization).filter(
        ExpertSpecialization.expert_user_id == user_id
    ).delete()
    add_user_specializations(user_id, specializations)


def update_user(user_id: int, payload: dict[str, Any], context=None) -> ExpertUser:
    """Update and commit a user using the current route behavior."""
    user = get_user_or_raise(user_id, context)
    data = payload
    if context is not None:
        if getattr(user, "authority", "EXPERT") == "PLATFORM_ADMIN":
            raise UserNotFoundError()
        if "authority" in data or data.get("role") == "admin":
            raise UserValidationError("Administrative authority cannot be changed here.")
        if data.get("manager_id") and not user_in_organization(data["manager_id"], context.organization_id):
            raise UserValidationError("Manager must belong to the same organization.")
    password_changed = False
    deactivated = False
    role_changed = False
    validate_expert_scope(
        data.get("role", user.role),
        data.get("is_active", user.is_active),
        {
            "can_handle_domestic": data.get("can_handle_domestic", user.can_handle_domestic),
            "can_handle_international": data.get("can_handle_international", user.can_handle_international),
        },
    )

    if "username" in data:
        new_username = data["username"]
        if new_username != user.username:
            existing_user = ExpertUser.query.filter(
                and_(
                    ExpertUser.username == new_username,
                    ExpertUser.id != user_id,
                )
            ).first()
            if existing_user:
                raise UserValidationError("نام کاربری قبلاً استفاده شده است")
            user.username = new_username

    if "password" in data:
        password = data["password"]
        if password and password.strip():
            user.password_hash = hash_password(password)
            password_changed = True

    for field in ["full_name", "email", "phone", "department", "is_active"]:
        if field in data:
            if field == "is_active" and user.is_active and data[field] is False:
                deactivated = True
            setattr(user, field, data[field])

    if "role" in data:
        role_changed = data["role"] != user.role
        user.role = data["role"]

    if "manager_id" in data:
        user.manager_id = data["manager_id"]

    for field in ["can_handle_domestic", "can_handle_international"]:
        if field in data:
            setattr(user, field, bool(data[field]))

    if "sla_response_work_minutes" in data:
        user.sla_response_work_minutes = validate_sla_minutes(
            data["sla_response_work_minutes"]
        )

    if "specializations" in data:
        replace_user_specializations(user_id, data["specializations"])

    if password_changed or deactivated or role_changed:
        from backend.services.auth_session_service import revoke_all_user_sessions
        reason = "password_changed" if password_changed else "account_deactivated" if deactivated else "admin_revoked"
        revoke_all_user_sessions(user_id, reason, commit=False)
    db.session.commit()
    return user

def user_in_organization(user_id: int, organization_id: int) -> bool:
    return db.session.query(OperationalMembership.id).filter(OperationalMembership.user_id == user_id, OperationalMembership.organization_id == organization_id, OperationalMembership.is_active.is_(True)).first() is not None


def validate_sla_minutes(value: Any) -> int:
    """Validate the admin-managed per-expert SLA duration."""
    if isinstance(value, bool):
        raise UserValidationError("مدت SLA باید عدد صحیح باشد")
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise UserValidationError("مدت SLA باید عدد صحیح باشد") from exc
    if str(value).strip() != str(normalized) or not 1 <= normalized <= 10080:
        raise UserValidationError("مدت SLA باید بین ۱ تا ۱۰۰۸۰ دقیقه باشد")
    return normalized


def validate_expert_scope(role: str, is_active: bool, data: dict[str, Any]) -> None:
    """Require at least one assignment capability for active expert roles."""
    from backend.services.expert_scope_service import is_expert_role

    if (
        is_active
        and is_expert_role(role)
        and not data.get("can_handle_domestic", False)
        and not data.get("can_handle_international", False)
    ):
        raise UserValidationError("حداقل یک حوزه فعالیت برای کارشناس فعال الزامی است")
