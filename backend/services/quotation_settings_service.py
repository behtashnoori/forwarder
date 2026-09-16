"""Organization-owned narrow audited IANA quotation policy command."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from backend.extensions import db
from backend.models import ExpertUser
from backend.operational_models import OperationalMembership, OperationalOrganization, OperationalAudit
from backend.services.quote_capability_crypto import CapabilityDenied
from backend.services.quote_response_authorization import database_instant


def set_quotation_timezone(actor_id, organization_id, value):
    if value is not None:
        if type(value) is not str or not value or len(value) > 64:
            raise ValueError('IANA_TIMEZONE_REQUIRED')
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError('IANA_TIMEZONE_INVALID') from None
    actor = db.session.scalar(select(ExpertUser).where(ExpertUser.id == actor_id)
        .execution_options(populate_existing=True).with_for_update())
    memberships = db.session.scalars(select(OperationalMembership).where(
        OperationalMembership.user_id == actor_id).order_by(OperationalMembership.id)
        .execution_options(populate_existing=True).with_for_update()).all()
    orgs = {identity: db.session.scalar(select(OperationalOrganization).where(OperationalOrganization.id == identity)
        .execution_options(populate_existing=True).with_for_update())
        for identity in sorted({organization_id, *(m.organization_id for m in memberships)})}
    active = [m for m in memberships if m.is_active and orgs[m.organization_id] and orgs[m.organization_id].is_active]
    org = orgs[organization_id]
    if (not actor or not actor.is_active or actor.authority != 'ORGANIZATION_ADMIN'
            or len(active) != 1 or active[0].organization_id != organization_id or not org or not org.is_active):
        raise CapabilityDenied('ORGANIZATION_ADMIN_REQUIRED')
    prior = org.quotation_validity_timezone
    if prior != value:
        org.quotation_validity_timezone = value
        db.session.add(OperationalAudit(organization_id=organization_id, actor_user_id=actor_id,
            action='organization.quotation-timezone.changed', entity_type='OperationalOrganization',
            entity_id=organization_id, metadata_json={'prior_timezone': prior, 'timezone': value,
                'applies_to': 'future-publications'}, recorded_at=database_instant()))
    db.session.flush()
    return {'timezone': org.quotation_validity_timezone, 'configured': value is not None}
