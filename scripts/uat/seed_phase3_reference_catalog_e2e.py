"""Tailor the shared synthetic graph for the P3-01 Expert journey."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.uat.seed_shared_transport_e2e import main as seed_shared_transport


def main() -> None:
    previous = os.environ.get("FORWARDER_E2E_PRIMARY_EXPERT")
    os.environ["FORWARDER_E2E_PRIMARY_EXPERT"] = "restricted"
    try:
        seed_shared_transport()
    finally:
        if previous is None:
            os.environ.pop("FORWARDER_E2E_PRIMARY_EXPERT", None)
        else:
            os.environ["FORWARDER_E2E_PRIMARY_EXPERT"] = previous


if __name__ == "__main__":
    main()
