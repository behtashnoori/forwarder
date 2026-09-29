"""Governed provisioning for one dedicated platform maintenance administrator."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import (
    OperationalAudit,
    OperationalIdempotency,
    OperationalMembership,
    OperationalOrganization,
)
from backend.services.admin_authorization_service import (
    ORGANIZATION_ADMIN_PERMISSION,
    PLATFORM_ADMIN,
)
from backend.services.user_service import hash_password


PROVISION_OPERATION = "platform_maintenance_admin.provision"
PROVISION_ACTIONS = (
    "platform_maintenance_admin.actor_created",
    "platform_maintenance_admin.authority_assigned",
    "platform_maintenance_admin.membership_assigned",
)
LEGACY_ADMIN_ROLE = "admin"
_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,49}\Z")
_OPERATOR_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@:/ -]{1,159}\Z")
_APPROVAL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,199}\Z")


class PlatformAdminProvisioningError(Exception):
    """Fail-closed provisioning refusal with a stable machine-readable code."""

    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _normalize_inputs(
    *,
    username: str,
    full_name: str,
    password: str,
    organization_public_id: str,
    operator: str,
    approval_reference: str,
) -> dict[str, str]:
    values = {
        "username": str(username or "").strip(),
        "full_name": str(full_name or "").strip(),
        "password": str(password or ""),
        "organization_public_id": str(organization_public_id or "").strip(),
        "operator": str(operator or "").strip(),
        "approval_reference": str(approval_reference or "").strip(),
    }
    if not _USERNAME_PATTERN.fullmatch(values["username"]):
        raise PlatformAdminProvisioningError(
            "USERNAME_INVALID",
            "Username must be 3-50 characters using letters, numbers, dot, dash, or underscore.",
            422,
        )
    if not values["full_name"] or len(values["full_name"]) > 100:
        raise PlatformAdminProvisioningError(
            "FULL_NAME_INVALID", "A full name of at most 100 characters is required.", 422
        )
    if any(ord(character) < 32 for character in values["full_name"]):
        raise PlatformAdminProvisioningError(
            "FULL_NAME_INVALID", "Full name contains a control character.", 422
        )
    if not values["password"] or len(values["password"]) > 100:
        raise PlatformAdminProvisioningError(
            "PASSWORD_INVALID", "A password of at most 100 characters is required.", 422
        )
    if not values["organization_public_id"] or len(values["organization_public_id"]) > 36:
        raise PlatformAdminProvisioningError(
            "ORGANIZATION_ID_INVALID", "An organization public ID is required.", 422
        )
    if not _OPERATOR_PATTERN.fullmatch(values["operator"]):
        raise PlatformAdminProvisioningError(
            "OPERATOR_INVALID", "A bounded named operator is required.", 422
        )
    if not _APPROVAL_PATTERN.fullmatch(values["approval_reference"]):
        raise PlatformAdminProvisioningError(
            "APPROVAL_REFERENCE_INVALID",
            "A bounded approval reference is required.",
            422,
        )
    return values


def _request_hash(values: dict[str, str]) -> str:
    payload = {
        "approval_reference": values["approval_reference"],
        "full_name": values["full_name"],
        "organization_public_id": values["organization_public_id"],
        "operator": values["operator"],
        "permissions": [ORGANIZATION_ADMIN_PERMISSION],
        "role": LEGACY_ADMIN_ROLE,
        "target_authority": PLATFORM_ADMIN,
        "target_state": "active",
        "username": values["username"],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _idempotency_key(organization_public_id: str, username: str) -> str:
    return hashlib.sha256(
        f"{organization_public_id}\0{username}".encode("utf-8")
    ).hexdigest()


def _password_matches(user: ExpertUser, password: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _common_audit_metadata(
    *, values: dict[str, str], user_id: int, membership_id: int
) -> dict:
    return {
        "approval_reference": values["approval_reference"],
        "membership_id": membership_id,
        "operator": values["operator"],
        "organization_public_id": values["organization_public_id"],
        "resulting_state": "active",
        "target_actor_id": user_id,
        "target_actor_username": values["username"],
        "target_authority": PLATFORM_ADMIN,
    }


def _validate_replay(
    *,
    ledger: OperationalIdempotency,
    organization: OperationalOrganization,
    values: dict[str, str],
    request_hash: str,
) -> tuple[ExpertUser, OperationalMembership]:
    if ledger.request_hash != request_hash:
        raise PlatformAdminProvisioningError(
            "IDEMPOTENCY_CONFLICT",
            "The requested identity was already provisioned with different governed inputs.",
        )
    user = db.session.get(ExpertUser, ledger.result_resource_id)
    if user is None or user.username != values["username"]:
        raise PlatformAdminProvisioningError(
            "PROVISIONING_STATE_DRIFT", "Provisioning identity evidence is incomplete."
        )
    memberships = list(
        db.session.scalars(
            select(OperationalMembership).where(OperationalMembership.user_id == user.id)
        )
    )
    identity_matches = (
        user.full_name == values["full_name"]
        and user.role == LEGACY_ADMIN_ROLE
        and user.authority == PLATFORM_ADMIN
        and user.is_active is True
        and _password_matches(user, values["password"])
    )
    membership_matches = (
        len(memberships) == 1
        and memberships[0].organization_id == organization.id
        and memberships[0].is_active is True
        and set(memberships[0].permissions or []) == {ORGANIZATION_ADMIN_PERMISSION}
    )
    if not identity_matches:
        raise PlatformAdminProvisioningError(
            "IDENTITY_CONFLICT", "The existing provisioned actor no longer matches the request."
        )
    if not membership_matches:
        raise PlatformAdminProvisioningError(
            "MEMBERSHIP_CONFLICT",
            "The existing provisioned actor does not have exactly the governed tenant membership.",
        )
    audits = list(
        db.session.scalars(
            select(OperationalAudit).where(
                OperationalAudit.organization_id == organization.id,
                OperationalAudit.actor_user_id == user.id,
                OperationalAudit.action.in_(PROVISION_ACTIONS),
            )
        )
    )
    if {audit.action for audit in audits} != set(PROVISION_ACTIONS) or len(audits) != 3:
        raise PlatformAdminProvisioningError(
            "PROVISIONING_STATE_DRIFT", "Provisioning audit evidence is incomplete."
        )
    expected = _common_audit_metadata(
        values=values, user_id=int(user.id), membership_id=int(memberships[0].id)
    )
    if any(
        audit.recorded_at is None
        or any(audit.metadata_json.get(key) != value for key, value in expected.items())
        for audit in audits
    ):
        raise PlatformAdminProvisioningError(
            "PROVISIONING_STATE_DRIFT", "Provisioning audit evidence does not match."
        )
    return user, memberships[0]


def provision_platform_maintenance_admin(
    *,
    username: str,
    full_name: str,
    password: str,
    organization_public_id: str,
    operator: str,
    approval_reference: str,
    bootstrap_authorized: bool,
) -> dict:
    """Create one dedicated System Admin and exact tenant membership atomically.

    ``bootstrap_authorized`` is supplied only by the explicitly confirmed offline
    command. It is deliberately not inferred from a pre-existing Product actor,
    which avoids making creation of the first System Admin circular.
    """
    if bootstrap_authorized is not True:
        raise PlatformAdminProvisioningError(
            "BOOTSTRAP_TRUST_REQUIRED",
            "An explicitly confirmed offline bootstrap command is required.",
            403,
        )
    values = _normalize_inputs(
        username=username,
        full_name=full_name,
        password=password,
        organization_public_id=organization_public_id,
        operator=operator,
        approval_reference=approval_reference,
    )
    request_hash = _request_hash(values)
    idempotency_key = _idempotency_key(
        values["organization_public_id"], values["username"]
    )

    try:
        organization = db.session.execute(
            select(OperationalOrganization)
            .where(
                OperationalOrganization.public_id == values["organization_public_id"]
            )
            .with_for_update()
        ).scalar_one_or_none()
        if organization is None:
            raise PlatformAdminProvisioningError(
                "ORGANIZATION_NOT_FOUND", "The target organization was not found.", 404
            )
        if not organization.is_active:
            raise PlatformAdminProvisioningError(
                "ORGANIZATION_INACTIVE", "The target organization is inactive."
            )

        ledger = db.session.scalar(
            select(OperationalIdempotency).where(
                OperationalIdempotency.organization_id == organization.id,
                OperationalIdempotency.operation == PROVISION_OPERATION,
                OperationalIdempotency.resource_type == "organization",
                OperationalIdempotency.command_resource_id == organization.id,
                OperationalIdempotency.idempotency_key == idempotency_key,
            )
        )
        if ledger is not None:
            user, membership = _validate_replay(
                ledger=ledger,
                organization=organization,
                values=values,
                request_hash=request_hash,
            )
            db.session.commit()
            return {
                "status": "UNCHANGED",
                "user_id": int(user.id),
                "username": user.username,
                "authority": user.authority,
                "state": "active",
                "organization_public_id": organization.public_id,
                "membership_id": int(membership.id),
                "active_membership_count": 1,
                "audit_recorded": False,
            }

        existing = db.session.scalar(
            select(ExpertUser).where(ExpertUser.username == values["username"])
        )
        if existing is not None:
            existing_memberships = list(
                db.session.scalars(
                    select(OperationalMembership).where(
                        OperationalMembership.user_id == existing.id
                    )
                )
            )
            if existing.authority != PLATFORM_ADMIN:
                code = "AUTHORITY_CONFLICT"
            elif existing_memberships:
                code = "MEMBERSHIP_CONFLICT"
            else:
                code = "IDENTITY_CONFLICT"
            raise PlatformAdminProvisioningError(
                code,
                "The username already exists and cannot be elevated or repurposed.",
            )

        user = ExpertUser(
            username=values["username"],
            full_name=values["full_name"],
            password_hash=hash_password(values["password"]),
            role=LEGACY_ADMIN_ROLE,
            authority=PLATFORM_ADMIN,
            is_active=True,
            email=None,
            phone=None,
        )
        db.session.add(user)
        db.session.flush()
        membership = OperationalMembership(
            organization_id=organization.id,
            user_id=user.id,
            is_active=True,
            permissions=[ORGANIZATION_ADMIN_PERMISSION],
        )
        db.session.add(membership)
        db.session.flush()

        action_time = datetime.now(timezone.utc)
        common_metadata = _common_audit_metadata(
            values=values, user_id=int(user.id), membership_id=int(membership.id)
        )
        audit_specs = (
            (PROVISION_ACTIONS[0], "ExpertUser", user.id, "actor_creation"),
            (PROVISION_ACTIONS[1], "ExpertUser", user.id, "authority_assignment"),
            (
                PROVISION_ACTIONS[2],
                "OperationalMembership",
                membership.id,
                "organization_membership_assignment",
            ),
        )
        for action, entity_type, entity_id, fact in audit_specs:
            db.session.add(
                OperationalAudit(
                    organization_id=organization.id,
                    actor_user_id=user.id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    metadata_json={**common_metadata, "governance_fact": fact},
                    recorded_at=action_time,
                )
            )

        response = {
            "status": "CHANGED",
            "user_id": int(user.id),
            "username": user.username,
            "authority": user.authority,
            "state": "active",
            "organization_public_id": organization.public_id,
            "membership_id": int(membership.id),
            "active_membership_count": 1,
            "audit_recorded": True,
        }
        db.session.add(
            OperationalIdempotency(
                organization_id=organization.id,
                operation=PROVISION_OPERATION,
                resource_type="organization",
                command_resource_id=organization.id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                result_resource_id=user.id,
                response_json=response,
            )
        )
        db.session.commit()
        return response
    except PlatformAdminProvisioningError:
        db.session.rollback()
        raise
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise PlatformAdminProvisioningError(
            "PERSISTENCE_FAILED", "Provisioning did not commit.", 500
        ) from exc
    except Exception:
        db.session.rollback()
        raise
