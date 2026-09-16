"""Provider-neutral result contract and explicitly enabled deterministic adapter."""
from dataclasses import dataclass
from flask import current_app


@dataclass(frozen=True)
class ProviderResult:
    outcome: str
    reference: str
    reason: str
    retryable: bool = False


class FakeEmailProvider:
    name = 'fake-email.v1'
    simulated = True

    def send(self, *, reference, recipient, template):
        if recipient.split('@')[-1] not in {'example.test', 'example.invalid'}:
            return ProviderResult('FAILED', reference, 'SYNTHETIC_RECIPIENT_REQUIRED')
        mode = current_app.config.get('NOTIFICATION_FAKE_OUTCOME', 'SENT')
        if mode not in {'ACCEPTED', 'SENT', 'DELIVERED', 'FAILED', 'UNKNOWN'}:
            raise ValueError('INVALID_FAKE_OUTCOME')
        return ProviderResult(mode, reference, 'SIMULATED_' + mode, mode == 'FAILED')

    def reconcile(self, *, reference):
        # Explicit qualification scenario, never an inferred successful receipt.
        outcome = current_app.config.get('NOTIFICATION_FAKE_RECONCILIATION', 'UNKNOWN')
        if outcome not in {'ACCEPTED', 'SENT', 'DELIVERED', 'FAILED', 'UNKNOWN'}:
            raise ValueError('INVALID_FAKE_RECONCILIATION')
        return ProviderResult(outcome, reference, 'SIMULATED_RECONCILIATION_' + outcome, outcome == 'FAILED')

    def send_quote(self, *, reference, recipient, template, grant_id, read_delivery=False):
        """Bounded synthetic adapter; capability never enters durable provider result."""
        from backend.extensions import db
        from backend.services.quote_response_authorization import capability_for_adapter
        from backend.services.quote_capability_crypto import CapabilityDenied
        capture = current_app.config.get('QUOTE_CAPABILITY_PRIVATE_CAPTURE')
        origin = current_app.config.get('QUOTE_CAPABILITY_CUSTOMER_ORIGIN')
        allowed = current_app.config.get('QUOTE_CAPABILITY_ALLOWED_ORIGINS')
        from backend.services.quote_capability_crypto import customer_origins
        try:
            allowed = customer_origins(current_app.config, testing=current_app.testing)
        except CapabilityDenied:
            return ProviderResult('FAILED', reference, 'PRIVATE_CAPTURE_REQUIRED')
        if (type(capture) is not PrivateQuoteCapture or type(origin) is not str
                or type(allowed) not in {tuple, list} or origin not in allowed):
            return ProviderResult('FAILED', reference, 'PRIVATE_CAPTURE_REQUIRED')
        result = self.send(reference=reference, recipient=recipient, template=template)
        if result.outcome == 'FAILED':
            return result
        try:
            token, exact_recipient = capability_for_adapter(grant_id, write=not read_delivery)
            if recipient != exact_recipient:
                raise CapabilityDenied('RECIPIENT_CHANGED')
            # No business lock survives private simulated transport communication.
            db.session.rollback()
        except CapabilityDenied:
            db.session.rollback()
            return ProviderResult('FAILED', reference, 'CAPABILITY_UNAVAILABLE')
        if result.outcome in {'ACCEPTED', 'SENT', 'DELIVERED'}:
            capture._capture(reference, recipient, origin + '/quote-response.html#' + token)
        return result


class PrivateQuoteCapture:
    """Synthetic test fixture memory only. No route or public serializer exposes it."""
    def __init__(self):
        self._messages = {}

    def __repr__(self):
        return '<PrivateQuoteCapture: private synthetic messages redacted>'

    def _capture(self, reference, recipient, link):
        self._messages.setdefault(reference, (recipient, link))

    def consume_for_fixture(self, reference):
        return self._messages.pop(reference)

    def clear(self):
        self._messages.clear()


def configured_provider():
    if (current_app.config.get('NOTIFICATION_PROVIDER') != 'fake'
            or current_app.config.get('NOTIFICATION_ENVIRONMENT') != 'qualification'
            or not current_app.testing):
        raise ValueError('EXPLICIT_FAKE_QUALIFICATION_REQUIRED')
    return FakeEmailProvider()
