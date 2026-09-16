"""Notification owner staging contract for the existing expert inbox."""
from backend.extensions import db
from backend.models import ExpertConsoleNotification
from sqlalchemy import select


def _stage_fact_attention(root, fact):
    from backend.services.assigned_work_authorization import authorize_work_action
    if not root.assigned_to or not authorize_work_action({'id':root.assigned_to},root,'request.read').allowed:
        return False
    if root.assigned_to and not db.session.scalar(select(ExpertConsoleNotification.id).where(
            ExpertConsoleNotification.quote_response_fact_id == fact.id,
            ExpertConsoleNotification.expert_user_id == root.assigned_to)):
        db.session.add(ExpertConsoleNotification(operational_organization_id=fact.organization_id,
            quote_response_fact_id=fact.id, expert_user_id=root.assigned_to, shipment_request_id=root.id,
            notification_type='customer_quote_response', title='پاسخ مشتری به پیشنهاد',
            message=f'{fact.response}; quote={fact.snapshot["quote_public_id"]}; sequence={fact.sequence}',
            is_read=False, created_at=fact.recorded_at.replace(tzinfo=None)))
    return True


def reroute_response_attention(scope):
    from backend.quote_response_models import QuoteResponseFact
    from backend.services.quote_response_authorization import lock_grants
    lock_grants(scope)
    facts = db.session.scalars(select(QuoteResponseFact).where(
        QuoteResponseFact.request_id == scope['root'].id,
        QuoteResponseFact.organization_id == scope['root'].operational_organization_id)
        .order_by(QuoteResponseFact.id).with_for_update()).all()
    for fact in facts:
        _stage_fact_attention(scope['root'], fact)


def stage_response_inbox(root, fact, event, quote):
    attention = _stage_fact_attention(root, fact)
    event.payload = {**event.payload, 'inbox_delivery':{
        'state':'PREPARED' if attention else 'BLOCKED',
        'reason':'CURRENT_AUTHORIZED_ASSIGNEE' if attention else 'ASSIGNEE_NOT_CURRENTLY_AUTHORIZED'}}
    # No existing certification contract proves an external expert destination.
    # Keep the primary inbox and persist the external dependency, never guess
    # an email/phone from a staff profile or send a real message.
    from backend.notification_models import NotificationAction
    from backend.services.quote_notification_contract import digest
    db.session.flush()
    intent = {'fact_id': fact.id, 'quote_public_id': quote.public_id,
        'assignee_id': root.assigned_to, 'channel': 'EMAIL',
        'policy': 'quote-response-expert.v1', 'certification': 'NOT_PROVEN'}
    db.session.add(NotificationAction(organization_id=fact.organization_id,
        request_id=root.id, event_id=event.id, actor_id=quote.created_by_expert_id,
        policy='quote-response-expert.v1', channel='EMAIL',
        intent_digest=digest(intent), state='BLOCKED',
        reason='EXPERT_DESTINATION_NOT_CERTIFIED', approval='POLICY_DELEGATED'))
    event.published_at = fact.recorded_at
