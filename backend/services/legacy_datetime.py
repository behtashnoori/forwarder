"""Serialization helpers for narrowly verified legacy timestamp contracts."""
from datetime import datetime, timezone


def serialize_legacy_utc_datetime(value: datetime | None) -> str | None:
    """Serialize a verified UTC-naive legacy value as RFC 3339 UTC.

    A naive input must already be UTC by its field's established storage
    contract. This helper must not be used for local-naive or mixed timestamps.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")
