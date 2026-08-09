"""Release fitness gate for normative OperationalShipment identity boundaries."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPES = (
    ROOT / "backend" / "routes",
    ROOT / "src",
    ROOT / "scripts" / "uat",
    ROOT / "docs" / "openapi" / "openapi.yaml",
)
RULES = (
    (re.compile(r"operational-shipments/<int:shipment"), "numeric Flask path converter"),
    (re.compile(r"operational-shipments/by-public-id"), "non-canonical public-id alias"),
    (re.compile(r"const\s+shipmentId\s*=\s*data\??\.id"), "frontend persistence-ID addressing"),
    (re.compile(r"const\s+shipmentId\s*=\s*shipment\.id"), "UAT persistence-ID addressing"),
    (re.compile(r"shipments\.map\(\(item\)\s*=>\s*item\.id\)"), "UAT persistence-ID deduplication"),
    (re.compile(r'"shipment_numeric_id"\s*:'), "exported numeric shipment identity"),
    (re.compile(r"/operational-shipments/\d+(?:/|[\"'`])"), "literal numeric shipment URL"),
)
FRONTEND_RULES = (
    (re.compile(r"shipment\.data\.id\b"), "frontend Shipment detail persistence-ID addressing"),
    (re.compile(r"\bshipment\.id\b"), "frontend Shipment persistence-ID addressing"),
)


def files():
    for scope in SCOPES:
        if scope.is_file():
            yield scope
        elif scope.exists():
            yield from (p for p in scope.rglob("*") if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".yaml", ".yml"})


def main() -> int:
    leaks: list[str] = []
    for path in files():
        text = path.read_text(encoding="utf-8")
        for pattern, label in RULES:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                leaks.append(f"{path.relative_to(ROOT)}:{line}: {label}")
        if path.is_relative_to(ROOT / "src"):
            for pattern, label in FRONTEND_RULES:
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    leaks.append(f"{path.relative_to(ROOT)}:{line}: {label}")
    if leaks:
        print("Shipment identity fitness gate: FAIL")
        print("\n".join(leaks))
        return 1
    print("Shipment identity fitness gate: PASS (zero normative numeric leaks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
