#!/usr/bin/env python3
"""Dry-run or apply the idempotent Request transport catalog reconciliation."""

import argparse
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.extensions import db
from backend.models import TransportMethod
from backend import create_app
from backend.request_transport_catalog import DEFAULT_TRANSPORT_METHODS, catalog_name_key


def reconcile_transport_methods(*, apply: bool = False) -> dict:
    """Plan or apply missing canonical rows without deleting historical rows."""
    app = create_app(skip_startup=True)
    with app.app_context():
        existing = {
            catalog_name_key(row.name): row
            for row in db.session.query(TransportMethod).order_by(TransportMethod.id).all()
        }
        missing = [item for item in DEFAULT_TRANSPORT_METHODS if catalog_name_key(item["name"]) not in existing]
        if apply:
            for item in missing:
                db.session.add(TransportMethod(**item, is_active=True))
            db.session.commit()
        else:
            db.session.rollback()
        return {
            "status": "APPLIED" if apply else "DRY_RUN",
            "inserted": len(missing) if apply else 0,
            "missing": [item["name"] for item in missing],
            "historical_rows_deleted": 0,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(reconcile_transport_methods(apply=args.apply), ensure_ascii=False, sort_keys=True))
