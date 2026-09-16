"""Owner transaction receipt for bounded compatibility tracking commands."""

import hashlib
import json

from sqlalchemy import select

from backend.extensions import db
from backend.models import ShipmentTracking
from backend.operational_models import OperationalIdempotency


class ReceiptConflict(ValueError):
    pass


def begin(tracking: ShipmentTracking, operation: str, resource_id: int, key: str | None, payload: dict):
    # Every command on a tracking root locks the same row before checking the
    # scoped unique receipt. PostgreSQL serializes concurrent same-key writes.
    db.session.execute(select(ShipmentTracking.id).where(ShipmentTracking.id == tracking.id).with_for_update()).scalar_one()
    if key is None:
        return None, None
    if not isinstance(key, str) or not 1 <= len(key) <= 100:
        raise ReceiptConflict("invalid Idempotency-Key")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    receipt = db.session.scalar(select(OperationalIdempotency).where(
        OperationalIdempotency.organization_id == tracking.operational_organization_id,
        OperationalIdempotency.operation == operation,
        OperationalIdempotency.resource_type == "tracking",
        OperationalIdempotency.command_resource_id == resource_id,
        OperationalIdempotency.idempotency_key == key,
    ))
    if receipt:
        if receipt.request_hash != digest:
            raise ReceiptConflict("Idempotency-Key was used with another payload")
        return receipt, receipt.response_json
    receipt = OperationalIdempotency(
        organization_id=tracking.operational_organization_id,
        operation=operation,
        resource_type="tracking",
        command_resource_id=resource_id,
        idempotency_key=key,
        request_hash=digest,
    )
    db.session.add(receipt)
    return receipt, None


def complete(receipt, result_id: int, response: dict):
    if receipt is not None:
        receipt.result_resource_id = result_id
        receipt.response_json = response
