"""Seed Personal Analytics into the runner-owned disposable browser database."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import create_app
from backend.personal_analytics_uat import provision


def main() -> None:
    password = os.environ["FORWARDER_E2E_PASSWORD"]
    app = create_app(skip_startup=True)
    with app.app_context():
        summary = provision(app, password)
    print(json.dumps({"seed": "personal-analytics-e2e", **summary}, sort_keys=True))


if __name__ == "__main__":
    main()
