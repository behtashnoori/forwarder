"""Canonical exact-hostname normalization, resolution, and administration."""
from __future__ import annotations

import re
from typing import Any

from sqlalchemy.exc import MultipleResultsFound

from backend.extensions import db
from backend.operational_models import OrganizationHostname, OperationalOrganization


HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class HostnameValidationError(ValueError):
    pass


class HostnameResolutionError(RuntimeError):
    """Routing state is ambiguous and must fail closed."""


def normalize_hostname(value: str | None) -> str:
    """Return a lowercase ASCII DNS hostname with scheme/path/port removed safely."""
    if not isinstance(value, str):
        raise HostnameValidationError("hostname is required")
    raw = value.strip()
    if not raw or any(character.isspace() for character in raw):
        raise HostnameValidationError("hostname is malformed")
    if "://" in raw or any(character in raw for character in "/?#@"):
        raise HostnameValidationError("hostname must not contain a scheme, path, query, or userinfo")
    if raw.startswith("["):
        raise HostnameValidationError("IP literals are not tenant hostnames")
    if raw.count(":") > 1:
        raise HostnameValidationError("hostname is malformed")
    host, separator, port = raw.rpartition(":")
    if separator:
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            raise HostnameValidationError("hostname port is malformed")
        raw = host
    raw = raw.rstrip(".")
    try:
        normalized = raw.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise HostnameValidationError("hostname is malformed") from exc
    if len(normalized) > 253 or "." not in normalized:
        raise HostnameValidationError("a fully-qualified hostname is required")
    labels = normalized.split(".")
    if any(not HOST_LABEL.fullmatch(label) for label in labels):
        raise HostnameValidationError("hostname is malformed")
    return normalized


def resolve_organization_for_host(value: str | None) -> OperationalOrganization | None:
    """Resolve one active exact mapping to one active Organization; never infer identity."""
    try:
        hostname = normalize_hostname(value)
    except HostnameValidationError:
        return None
    try:
        mapping = (
            db.session.query(OrganizationHostname)
            .join(OperationalOrganization)
            .filter(
                OrganizationHostname.hostname == hostname,
                OrganizationHostname.is_active.is_(True),
                OperationalOrganization.is_active.is_(True),
            )
            .one_or_none()
        )
    except MultipleResultsFound as exc:
        raise HostnameResolutionError("duplicate active hostname routing state") from exc
    return mapping.organization if mapping else None


def serialize_hostname(row: OrganizationHostname) -> dict[str, Any]:
    return {
        "id": row.id,
        "public_id": row.public_id,
        "organization_id": row.organization_id,
        "organization_public_id": row.organization.public_id,
        "organization_name": row.organization.name,
        "hostname": row.hostname,
        "is_primary": row.is_primary,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def list_hostnames(organization_id: int | None = None) -> list[dict[str, Any]]:
    query = db.session.query(OrganizationHostname)
    if organization_id is not None:
        query = query.filter(OrganizationHostname.organization_id == organization_id)
    return [serialize_hostname(row) for row in query.order_by(OrganizationHostname.hostname).all()]


def create_hostname(payload: dict[str, Any]) -> OrganizationHostname:
    organization = db.session.get(OperationalOrganization, payload.get("organization_id"))
    if not organization:
        raise HostnameValidationError("organization not found")
    hostname = normalize_hostname(payload.get("hostname"))
    row = OrganizationHostname(
        organization_id=organization.id,
        hostname=hostname,
        is_primary=bool(payload.get("is_primary", False)),
        is_active=bool(payload.get("is_active", True)),
    )
    db.session.add(row)
    db.session.commit()
    return row


def update_hostname(public_id: str, payload: dict[str, Any]) -> OrganizationHostname:
    row = OrganizationHostname.query.filter_by(public_id=public_id).one_or_none()
    if not row:
        raise HostnameValidationError("hostname mapping not found")
    if "hostname" in payload:
        row.hostname = normalize_hostname(payload["hostname"])
    if "is_active" in payload:
        row.is_active = bool(payload["is_active"])
    if "is_primary" in payload:
        make_primary = bool(payload["is_primary"])
        if make_primary:
            OrganizationHostname.query.filter(
                OrganizationHostname.organization_id == row.organization_id,
                OrganizationHostname.id != row.id,
            ).update({OrganizationHostname.is_primary: False})
        row.is_primary = make_primary
    db.session.commit()
    return row
