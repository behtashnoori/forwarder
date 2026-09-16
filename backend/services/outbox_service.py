"""Public, caller-transaction-owned durable event emission (no dispatch)."""
from backend.census_context import ensure_census_context
from backend.extensions import db
from backend.operational_models import OperationalOutbox


def record_event(organization_id, event_type, aggregate_type, aggregate_id, payload=None):
    context = ensure_census_context(db.session)
    body = dict(payload or {})
    body['_ownership_census'] = {
        'census_id': context.census_id, 'cache_version': context.cache_version,
        'cache_token': context.cache_token,
    }
    event = OperationalOutbox(organization_id=organization_id, event_type=event_type,
                              aggregate_type=aggregate_type, aggregate_id=aggregate_id,
                              payload=body)
    db.session.add(event)
    return event
