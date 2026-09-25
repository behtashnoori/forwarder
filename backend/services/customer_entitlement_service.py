"""Org Admin commands and current DN10 authorization queries. Never auto-link."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.customer_entitlement_models import CustomerEntitlement
from backend.models import Customer, CustomerGamification, ExpertUser
from backend.operational_models import OperationalOrganization, utcnow
from backend.services.admin_authorization_service import (
    AdminAuthorizationError, effective_authority, organization_context_for_authenticated_user,
)
from backend.services.operational_service import OperationalError
from backend.services.legacy_datetime import serialize_legacy_utc_datetime


def _admin(organization_id, actor_id):
    actor = db.session.get(ExpertUser, actor_id)
    if not actor or not actor.is_active or effective_authority(actor) != "ORGANIZATION_ADMIN":
        raise OperationalError("ENTITLEMENT_FORBIDDEN", "فقط مدیر سازمان مجاز است", 403)
    try:
        context = organization_context_for_authenticated_user(actor_id)
    except AdminAuthorizationError as exc:
        raise OperationalError("ENTITLEMENT_FORBIDDEN", "سازمان فعال لازم است", 403) from exc
    if context.organization_id != organization_id:
        raise OperationalError("ENTITLEMENT_FORBIDDEN", "دسترسی غیرمجاز", 403)


def authorized_customer_ids(account):
    """SQL subquery: live grant + current active tenant/account/CRM, no cache."""
    return select(CustomerEntitlement.customer_id).join(
        Customer, Customer.id == CustomerEntitlement.customer_id,
    ).join(
        CustomerGamification, CustomerGamification.id == CustomerEntitlement.portal_account_id,
    ).join(
        OperationalOrganization, OperationalOrganization.id == CustomerEntitlement.organization_id,
    ).where(
        CustomerEntitlement.portal_account_id == account.id,
        CustomerEntitlement.organization_id == account.operational_organization_id,
        CustomerEntitlement.revoked_at.is_(None),
        Customer.operational_organization_id == CustomerEntitlement.organization_id,
        Customer.ownership_scope == "TENANT", Customer.status == "active",
        CustomerGamification.operational_organization_id == CustomerEntitlement.organization_id,
        CustomerGamification.account_status == "ACTIVE", OperationalOrganization.is_active.is_(True),
    )


def _project(row):
    account = db.session.get(CustomerGamification, row.portal_account_id)
    customer = db.session.get(Customer, row.customer_id)
    return {
        "public_id": row.public_id, "portal_account_public_id": account.public_id,
        "account_label": account.email, "customer_id": customer.id,
        "customer_label": customer.company_name or " ".join(filter(None, [customer.first_name, customer.last_name])) or "مشتری",
        "status": "REVOKED" if row.revoked_at else "ACTIVE",
        # Both new fields are proven UTC Instants; SQLite drops their tzinfo.
        "granted_at": serialize_legacy_utc_datetime(row.granted_at), "granted_by": row.granted_by,
        "revoked_at": serialize_legacy_utc_datetime(row.revoked_at),
        "revoked_by": row.revoked_by,
    }


def configuration(organization_id, actor_id):
    _admin(organization_id, actor_id)
    accounts = db.session.scalars(select(CustomerGamification).where(
        CustomerGamification.operational_organization_id == organization_id,
        CustomerGamification.account_status == "ACTIVE",
    ).order_by(CustomerGamification.email)).all()
    customers = db.session.scalars(select(Customer).where(
        Customer.operational_organization_id == organization_id,
        Customer.ownership_scope == "TENANT", Customer.status == "active",
    ).order_by(Customer.id)).all()
    rows = db.session.scalars(select(CustomerEntitlement).where(
        CustomerEntitlement.organization_id == organization_id,
    ).order_by(CustomerEntitlement.id.desc())).all()
    return {
        "accounts": [{"public_id": a.public_id, "label": a.email} for a in accounts],
        "customers": [{"id": c.id, "label": c.company_name or " ".join(filter(None, [c.first_name, c.last_name])) or "مشتری"} for c in customers],
        "grants": [_project(row) for row in rows],
    }


def grant(organization_id, actor_id, payload, command_key):
    _admin(organization_id, actor_id)
    if not isinstance(payload, dict) or set(payload) - {"portal_account_public_id", "customer_id"}:
        raise OperationalError("ENTITLEMENT_INVALID", "اطلاعات دسترسی معتبر نیست")
    account_public_id, customer_id = payload.get("portal_account_public_id"), payload.get("customer_id")
    if (not isinstance(account_public_id, str) or type(customer_id) is not int or customer_id <= 0
            or not isinstance(command_key, str) or not 1 <= len(command_key) <= 100):
        raise OperationalError("ENTITLEMENT_INVALID", "حساب، مشتری و شناسه درخواست معتبر لازم است")
    # One account lock serializes grant/revoke; distinct relationships remain independent facts.
    account = db.session.scalar(select(CustomerGamification).where(
        CustomerGamification.public_id == account_public_id,
        CustomerGamification.operational_organization_id == organization_id,
        CustomerGamification.account_status == "ACTIVE",
    ).with_for_update().execution_options(populate_existing=True))
    customer = db.session.scalar(select(Customer).where(
        Customer.id == customer_id, Customer.operational_organization_id == organization_id,
        Customer.ownership_scope == "TENANT", Customer.status == "active",
    ).with_for_update().execution_options(populate_existing=True))
    if not account or not customer:
        raise OperationalError("ENTITLEMENT_TARGET_NOT_FOUND", "حساب یا مشتری فعال یافت نشد", 404)
    previous = db.session.scalar(select(CustomerEntitlement).where(
        CustomerEntitlement.organization_id == organization_id, CustomerEntitlement.command_key == command_key,
    ))
    if previous:
        if previous.portal_account_id != account.id or previous.customer_id != customer.id or previous.granted_by != actor_id:
            raise OperationalError("ENTITLEMENT_REPLAY_CONFLICT", "شناسه درخواست قبلاً برای اطلاعات دیگری استفاده شده است", 409)
        return _project(previous), False  # replay never resurrects a revoked grant
    active = db.session.scalar(select(CustomerEntitlement.id).where(
        CustomerEntitlement.organization_id == organization_id,
        CustomerEntitlement.portal_account_id == account.id,
        CustomerEntitlement.customer_id == customer.id, CustomerEntitlement.revoked_at.is_(None),
    ))
    if active is not None:
        raise OperationalError("ENTITLEMENT_ALREADY_ACTIVE", "این دسترسی از قبل فعال است", 409)
    row = CustomerEntitlement(organization_id=organization_id, portal_account_id=account.id,
                              customer_id=customer.id, command_key=command_key, granted_by=actor_id)
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise OperationalError("ENTITLEMENT_CONFLICT", "دسترسی تغییر کرده است؛ دوباره بخوانید", 409) from exc
    return _project(row), True


def revoke(organization_id, actor_id, public_id):
    _admin(organization_id, actor_id)
    row = db.session.scalar(select(CustomerEntitlement).where(
        CustomerEntitlement.organization_id == organization_id, CustomerEntitlement.public_id == public_id,
    ))
    if not row:
        raise OperationalError("ENTITLEMENT_NOT_FOUND", "دسترسی یافت نشد", 404)
    db.session.scalar(select(CustomerGamification).where(
        CustomerGamification.id == row.portal_account_id,
    ).with_for_update())
    db.session.refresh(row, with_for_update=True)
    if row.revoked_at is None:
        row.revoked_by, row.revoked_at = actor_id, utcnow()
        db.session.commit()
    return _project(row)
