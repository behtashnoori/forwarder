"""Authoritative supported-currency contract for Golden quotes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Final


QUOTE_CURRENCY_CONTRACT_PATH: Final = (
    Path(__file__).resolve().parents[2] / "contracts" / "quote-currencies.v1.json"
)


def _load_contract() -> tuple[str, tuple[dict[str, str], ...]]:
    document = json.loads(QUOTE_CURRENCY_CONTRACT_PATH.read_text(encoding="utf-8"))
    if document.get("contract") != "quote-currencies.v1":
        raise RuntimeError("Unsupported quote currency contract")

    default = document.get("default")
    raw_currencies = document.get("currencies")
    if not isinstance(default, str) or not isinstance(raw_currencies, list):
        raise RuntimeError("Invalid quote currency contract")

    currencies: list[dict[str, str]] = []
    for item in raw_currencies:
        if not isinstance(item, dict):
            raise RuntimeError("Invalid quote currency entry")
        code = item.get("code")
        label_fa = item.get("label_fa")
        if (
            not isinstance(code, str)
            or len(code) != 3
            or code != code.upper()
            or not isinstance(label_fa, str)
            or not label_fa.strip()
        ):
            raise RuntimeError("Invalid quote currency entry")
        currencies.append({"code": code, "label_fa": label_fa})

    codes = [item["code"] for item in currencies]
    if len(codes) != len(set(codes)) or default not in codes:
        raise RuntimeError("Invalid quote currency set")
    return default, tuple(currencies)


DEFAULT_QUOTE_CURRENCY, QUOTE_CURRENCIES = _load_contract()
SUPPORTED_QUOTE_CURRENCIES: Final = frozenset(
    item["code"] for item in QUOTE_CURRENCIES
)


__all__ = [
    "DEFAULT_QUOTE_CURRENCY",
    "QUOTE_CURRENCIES",
    "QUOTE_CURRENCY_CONTRACT_PATH",
    "SUPPORTED_QUOTE_CURRENCIES",
]
