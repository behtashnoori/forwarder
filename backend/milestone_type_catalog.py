"""Separate, explicit, fail-closed MilestoneType catalog."""

import hashlib
import json
from pathlib import Path
from backend.extensions import db
from backend.models import ReferenceDataSeedRun
from backend.operational_models import utcnow
from backend.project_configuration_models import MilestoneType
from backend.services.project_configuration_service import MILESTONE_CODES

CATALOG_PATH = (
    Path(__file__).with_name("reference_data") / "milestone-types-v1.0.0.json"
)
APPROVED_CHECKSUM = (
    "sha256:d9045e0034b9a37ec4b25402cd3adde43d7f39b969b59e084d5a7d202b5951c2"
)


class MilestoneCatalogError(RuntimeError):
    pass


def checksum(p):
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(
                {k: v for k, v in p.items() if k != "checksum"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    )


def load_catalog(path=CATALOG_PATH):
    try:
        p = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise MilestoneCatalogError("catalog is not valid strict UTF-8 JSON") from exc
    if (
        set(p)
        != {
            "schema_version",
            "catalog_version",
            "source_version",
            "checksum",
            "milestone_types",
        }
        or p["schema_version"] != "1"
        or checksum(p) != APPROVED_CHECKSUM
        or p["checksum"] != APPROVED_CHECKSUM
    ):
        raise MilestoneCatalogError("catalog schema/checksum is invalid or unapproved")
    rows = p["milestone_types"]
    if (
        not isinstance(rows, list)
        or len(rows) != 13
        or {x.get("code") for x in rows} != MILESTONE_CODES
    ):
        raise MilestoneCatalogError("catalog codes differ from governance")
    return p


def plan_catalog(p, environment):
    existing = {x.immutable_code: x for x in MilestoneType.query.all()}
    created = unchanged = 0
    conflicts = []
    for e in p["milestone_types"]:
        x = existing.get(e["code"])
        if x is None:
            created += 1
        elif all(
            getattr(x, k) == e[k]
            for k in ("fa_name", "en_name", "definition", "display_order", "is_active")
        ):
            unchanged += 1
        else:
            conflicts.append(
                {"code": e["code"], "reason": "existing governed values differ"}
            )
    return {
        "catalog_version": p["catalog_version"],
        "checksum": p["checksum"],
        "environment": environment,
        "planned_count": 13,
        "created_count": created,
        "unchanged_count": unchanged,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }


def apply_catalog(
    p, *, environment, operator, approval_reference, expected_checksum, user_id
):
    if (
        expected_checksum != p["checksum"]
        or not operator.strip()
        or not approval_reference.strip()
    ):
        raise MilestoneCatalogError(
            "explicit operator, approval, and checksum are required"
        )
    plan = plan_catalog(p, environment)
    run = ReferenceDataSeedRun(
        catalog_version=p["catalog_version"],
        checksum=p["checksum"],
        environment=environment,
        mode="apply",
        planned_count=13,
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
        existing = {x.immutable_code for x in MilestoneType.query.all()}
        for e in p["milestone_types"]:
            if e["code"] not in existing:
                db.session.add(
                    MilestoneType(
                        immutable_code=e["code"],
                        fa_name=e["fa_name"],
                        en_name=e["en_name"],
                        definition=e["definition"],
                        display_order=e["display_order"],
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
        raise MilestoneCatalogError("catalog apply failed") from exc
