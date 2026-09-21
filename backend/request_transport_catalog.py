"""Governed catalog contract for ShipmentRequest transport intent."""
from __future__ import annotations

from typing import Final


COMBINED_TRANSPORT_CODE: Final = "Combined Transport"
COMBINED_TRANSPORT_LABEL_FA: Final = "حمل ترکیبی"
COMBINED_TRANSPORT_DESCRIPTION_FA: Final = (
    "ترکیب چند روش حمل؛ توالی واقعی در برنامه مسیر عملیاتی تعیین می‌شود"
)

# These are Request-intent catalog values. They are deliberately separate from
# the concrete RouteLeg transport-mode vocabulary.
DEFAULT_TRANSPORT_METHODS: Final = (
    {
        "name": "Sea Freight",
        "name_fa": "حمل دریایی",
        "description": "حمل کالا از طریق دریا - مناسب برای بارهای حجیم و سنگین",
    },
    {
        "name": "Air Freight",
        "name_fa": "حمل هوایی",
        "description": "حمل کالا از طریق هوا - سریع و مناسب برای بارهای فوری",
    },
    {
        "name": "Land Transport",
        "name_fa": "حمل زمینی",
        "description": "حمل کالا از طریق جاده - مناسب برای مسیرهای کوتاه و متوسط",
    },
    {
        "name": "Rail Transport",
        "name_fa": "حمل ریلی",
        "description": "حمل کالا از طریق راه‌آهن - مناسب برای بارهای حجیم و مسیرهای طولانی",
    },
    {
        "name": "Road Transport",
        "name_fa": "حمل جاده‌ای",
        "description": "حمل کالا از طریق جاده - سریع و قابل اعتماد برای حمل داخلی",
    },
    {
        "name": "Air Transport",
        "name_fa": "حمل هوایی",
        "description": "حمل کالا از طریق هوا - سریع‌ترین روش برای حمل داخلی",
    },
    {
        "name": COMBINED_TRANSPORT_CODE,
        "name_fa": COMBINED_TRANSPORT_LABEL_FA,
        "description": COMBINED_TRANSPORT_DESCRIPTION_FA,
    },
)

# Historical API clients have persisted these supported values even when a
# catalog fixture was not present. They remain accepted for compatibility but
# are not aliases for the new Combined Transport intent.
LEGACY_REQUEST_TRANSPORT_VALUES: Final = frozenset(
    {
        "road",
        "rail",
        "sea",
        "air",
        "Road Transport",
        "Rail Transport",
        "Land Transport",
        "Air Transport",
        "Sea Freight",
        "Air Freight",
    }
)


def catalog_name_key(value: str) -> str:
    """Return the comparison key used only for deterministic catalog de-duplication."""
    return " ".join(value.strip().casefold().split())
