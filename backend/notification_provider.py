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


def configured_provider():
    if (current_app.config.get('NOTIFICATION_PROVIDER') != 'fake'
            or current_app.config.get('NOTIFICATION_ENVIRONMENT') != 'qualification'
            or not current_app.testing):
        raise ValueError('EXPLICIT_FAKE_QUALIFICATION_REQUIRED')
    return FakeEmailProvider()
