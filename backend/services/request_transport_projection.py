"""Read-only projection of transport facts already stored on a request."""
from __future__ import annotations

from typing import Any


def project_existing_request_transport(source: Any) -> dict[str, str | None]:
    """Expose existing scalar transport fields without normalization or inference."""
    return {
        "transport_method": getattr(source, "transport_method", None),
        "international_transport_method": getattr(
            source, "international_transport_method", None
        ),
        "domestic_transport_method": getattr(source, "domestic_transport_method", None),
        "transport_method_preference": getattr(
            source, "transport_method_preference", None
        ),
    }


__all__ = ["project_existing_request_transport"]
