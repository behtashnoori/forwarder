"""
Dynamic CORS configuration with explicit dev/test/production behavior.
"""

from __future__ import annotations

import os
import re
from typing import List, Set

from backend.config import (
    get_configured_cors_origins,
    get_runtime_environment,
    is_development_environment,
    is_production_environment,
)


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "1" if default else "0").lower()
    return raw in ("1", "true", "yes")


def _dev_origins_from_common_ports() -> Set[str]:
    """Generate common localhost/127.0.0.1 origins for local development."""
    common_ports = [3000, 5173, 8080, 8081, 8082, 8083, 8084, 8085]
    vite_ports = list(range(8080, 8201))
    origins: Set[str] = set()
    for port in set(common_ports + vite_ports):
        origins.add(f"http://localhost:{port}")
        origins.add(f"http://127.0.0.1:{port}")
    return origins


def generate_cors_origins(*, testing: bool = False) -> List[str]:
    """Generate the allowed CORS origin list for the active runtime."""
    environment = get_runtime_environment(testing=testing)
    explicit_origins = set(get_configured_cors_origins())

    if is_production_environment(environment):
        return sorted(explicit_origins)

    origins = _dev_origins_from_common_ports()
    origins.update(origin for origin in explicit_origins if origin.startswith("http"))
    return sorted(origins)


def validate_origin(origin: str, *, testing: bool = False) -> bool:
    """Validate whether an origin matches the non-production localhost policy."""
    if not origin:
        return False

    if is_production_environment(get_runtime_environment(testing=testing)):
        return origin in get_configured_cors_origins()

    localhost_pattern = r"^http://(localhost|127\.0\.0\.1):\d+$"
    return bool(re.match(localhost_pattern, origin)) or origin in generate_cors_origins(testing=testing)


def is_cors_origin_allowed(origin: str | None, *, testing: bool = False, cors_config: dict | None = None) -> bool:
    """Return True when the request origin is allowed for CORS."""
    if not origin:
        return False

    environment = get_runtime_environment(testing=testing)
    allow_any = _bool_env("CORS_ALLOW_ALL_ORIGINS", False)
    if not is_production_environment(environment) and allow_any:
        return True

    origins = (cors_config or {}).get("origins") or generate_cors_origins(testing=testing)
    if origin in origins:
        return True
    if is_development_environment(environment) or testing:
        return validate_origin(origin, testing=testing)
    return False


def get_cors_config(*, testing: bool = False) -> dict:
    """
    Get CORS configuration.

    Production uses only explicit CORS_ORIGINS/CORS_ORIGIN values and never
    expands to wildcard or localhost defaults. Development and tests keep the
    local browser origins needed by Vite and localhost workflows.
    """
    origins = generate_cors_origins(testing=testing)

    return {
        "resources": {
            r"/*": {
                "origins": origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-CSRF-Token",
                    "X-Requested-With",
                    "Accept",
                    "Origin",
                ],
                "supports_credentials": True,
                "max_age": 3600,
            }
        },
        "supports_credentials": True,
        "origins": origins,
    }


def log_cors_info(*, testing: bool = False) -> None:
    """Log non-sensitive CORS configuration information for debugging."""
    config = get_cors_config(testing=testing)
    origins = config["origins"]
    environment = get_runtime_environment(testing=testing)

    print("CORS Configuration:")
    print(f"   Environment: {environment}")
    print(f"   Total Origins: {len(origins)}")
    print(f"   Supports Credentials: {config['supports_credentials']}")
    print(f"   Max Age: {config['resources'][r'/*']['max_age']} seconds")

    if origins:
        print("   Sample Origins:")
        for origin in origins[:5]:
            print(f"      - {origin}")
        if len(origins) > 5:
            print(f"      ... and {len(origins) - 5} more")

    print()


if __name__ == "__main__":
    log_cors_info()
