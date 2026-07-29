"""UTC timestamps for ephemeral monitoring and alert payloads."""
from datetime import datetime, timezone


def current_utc_timestamp() -> str:
    """Return the current instant as an explicitly UTC RFC 3339 string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
