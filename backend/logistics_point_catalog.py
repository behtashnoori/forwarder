"""Separate governed catalog for LogisticsPointType values."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.extensions import db
from backend.logistics_network_models import LogisticsPointType
from backend.models import ReferenceDataSeedRun
from backend.operational_models import utcnow

CATALOG_PATH = (
    Path(__file__).with_name("reference_data") / "logistics-point-types-v1.0.0.json"
)
APPROVED_CHECKSUM = (
    "sha256:d2a23d0928c792118e80561cd6a270a4b137ae80ddb91b955761772743e50076"
)
ALLOWED_CODES = {
    "FACTORY",
    "WAREHOUSE",
    "DISTRIBUTION_CENTER",
    "CUSTOMS",
    "PORT",
    "BORDER_CROSSING",
    "AIRPORT",
    "RAIL_TERMINAL",
    "ROAD_TERMINAL",
    "CUSTOMER_SITE",
    "OTHER_GOVERNED",
}


class LogisticsCatalogError(RuntimeError):
    pass


def canonical_checksum(payload):
    unsigned = {k: v for k, v in payload.items() if k != "checksum"}
    data = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_catalog(path=CATALOG_PATH):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LogisticsCatalogError("catalog is not valid strict UTF-8 JSON") from exc
    if set(payload) != {
        "schema_version",
        "catalog_version",
        "source_version",
        "checksum",
        "logistics_point_types",
    }:
        raise LogisticsCatalogError("catalog schema is invalid")
    if (
        payload["schema_version"] != "1"
        or payload["checksum"] != canonical_checksum(payload)
        or payload["checksum"] != APPROVED_CHECKSUM
    ):
        raise LogisticsCatalogError("catalog checksum is invalid or unapproved")
    rows = payload["logistics_point_types"]
    if (
        not isinstance(rows, list)
        or {x.get("code") for x in rows} != ALLOWED_CODES
        or len(rows) != len(ALLOWED_CODES)
    ):
        raise LogisticsCatalogError(
            "catalog codes do not match accepted PDR-016 values"
        )
    orders = set()
    for row in rows:
        if set(row) != {
            "code",
            "fa_name",
            "en_name",
            "definition",
            "display_order",
            "is_active",
        }:
            raise LogisticsCatalogError("catalog row schema is invalid")
        if not all(
            isinstance(row[k], str) and row[k].strip() == row[k] and row[k]
            for k in ("code", "fa_name", "en_name", "definition")
        ):
            raise LogisticsCatalogError("catalog text is invalid")
        if (
            row["is_active"] is not True
            or not isinstance(row["display_order"], int)
            or row["display_order"] in orders
        ):
            raise LogisticsCatalogError("catalog ordering/state is invalid")
        orders.add(row["display_order"])
    return payload


def plan_catalog(payload, environment):
    existing = {x.immutable_code: x for x in LogisticsPointType.query.all()}
    created = unchanged = 0
    conflicts = []
    for entry in payload["logistics_point_types"]:
        row = existing.get(entry["code"])
        if row is None:
            created += 1
        elif all(
            getattr(row, k) == entry[k]
            for k in ("fa_name", "en_name", "definition", "display_order", "is_active")
        ):
            unchanged += 1
        else:
            conflicts.append(
                {"code": entry["code"], "reason": "existing governed values differ"}
            )
    return {
        "catalog_version": payload["catalog_version"],
        "checksum": payload["checksum"],
        "environment": environment,
        "planned_count": len(payload["logistics_point_types"]),
        "created_count": created,
        "unchanged_count": unchanged,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }


def apply_catalog(
    payload, *, environment, operator, approval_reference, expected_checksum, user_id
):
    if (
        expected_checksum != payload["checksum"]
        or not operator.strip()
        or not approval_reference.strip()
    ):
        raise LogisticsCatalogError(
            "explicit operator, approval, and expected checksum are required"
        )
    plan = plan_catalog(payload, environment)
    run = ReferenceDataSeedRun(
        catalog_version=payload["catalog_version"],
        checksum=payload["checksum"],
        environment=environment,
        mode="apply",
        planned_count=plan["planned_count"],
        created_count=0,
        unchanged_count=plan["unchanged_count"],
        conflict_count=plan["conflict_count"],
        status="started",
        executed_by=operator.strip(),
        approval_reference=approval_reference.strip(),
    )
    db.session.add(run)
    db.session.commit()
    if plan["conflicts"]:
        run.status = "refused"
        run.completed_at = utcnow()
        run.error_summary = "Catalog conflicts detected; no writes made."
        db.session.commit()
        return plan, run
    try:
        existing = {x.immutable_code for x in LogisticsPointType.query.all()}
        for entry in payload["logistics_point_types"]:
            if entry["code"] not in existing:
                db.session.add(
                    LogisticsPointType(
                        immutable_code=entry["code"],
                        fa_name=entry["fa_name"],
                        en_name=entry["en_name"],
                        definition=entry["definition"],
                        display_order=entry["display_order"],
                        is_active=True,
                        created_by=user_id,
                        updated_by=user_id,
                    )
                )
        run.status = "succeeded"
        run.created_count = plan["created_count"]
        run.completed_at = utcnow()
        db.session.commit()
        return plan, run
    except Exception as exc:
        db.session.rollback()
        persisted = ReferenceDataSeedRun.query.filter_by(public_id=run.public_id).one()
        persisted.status = "failed"
        persisted.completed_at = utcnow()
        persisted.error_summary = f"Catalog apply failed ({type(exc).__name__})."
        db.session.commit()
        raise LogisticsCatalogError("catalog apply failed") from exc
