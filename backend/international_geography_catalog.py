"""Explicit, additive geography import into the existing reference authorities.

No startup hook. Call plan first and apply with a pinned checksum and named
operator/approval. Existing identities, labels and lifecycle are never changed.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from backend.extensions import db
from backend.models import Country, InternationalCity, ReferenceDataSeedRun
from backend.services.international_geography_readiness import validate_snapshot

CATALOG_PATH = Path(__file__).with_name("reference_data") / "international-geography-v2-fwd02.json"
CATALOG_SHA256 = "b3e71f12f7c9cc8a9c5061a9df0ed67f085636bc84bd7120400694adab2d48ca"


def load_catalog():
    raw = CATALOG_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CATALOG_SHA256:
        raise ValueError("Geography catalog checksum mismatch")
    data = json.loads(raw)
    errors = validate_snapshot(data)
    if errors:
        raise ValueError("Invalid geography catalog: " + "; ".join(errors))
    for record in data["records"]:
        record["locations"] = [{**data.get("location_defaults", {}), **item} for item in record["locations"]]
    return data


def plan_catalog():
    data = load_catalog()
    countries = {row.code: row for row in Country.query.all()}
    code_countries = {}
    for row in InternationalCity.query.filter(InternationalCity.un_locode.isnot(None)).all():
        code_countries.setdefault(row.un_locode, set()).add(row.country_id)
    creates = []
    conflicts = []
    unchanged = 0
    for record in data["records"]:
        source = record["country"]
        country = countries.get(source["code"])
        if country is None:
            creates.append({"kind": "country", "code": source["code"], "source": source})
        else:
            unchanged += 1
        existing = InternationalCity.query.filter_by(country_id=country.id).all() if country else []
        by_code = {row.un_locode: row for row in existing if row.un_locode}
        unbound_names = {row.name_en.casefold() for row in existing if not row.un_locode}
        for item in record["locations"]:
            assigned_countries = code_countries.get(item["un_locode"], set())
            if assigned_countries and assigned_countries != {country.id if country else None}:
                conflicts.append(item["un_locode"])
                continue
            if item["un_locode"] in by_code:
                unchanged += 1
                continue
            # A label alone cannot prove shared identity; require an explicit
            # reviewed mapping for unbound legacy rows. Different authoritative
            # codes may legitimately share a name and must remain distinct.
            if item["name_en"].casefold() in unbound_names:
                conflicts.append(item["un_locode"])
                continue
            creates.append({"kind": "location", "code": source["code"], "source": item})
    return {"dataset_id": data["dataset_id"], "checksum": CATALOG_SHA256,
            "creates": creates, "conflicts": conflicts, "unchanged_count": unchanged}


def apply_catalog(*, expected_checksum, executed_by, approval_reference, environment):
    if expected_checksum != CATALOG_SHA256:
        raise ValueError("Expected checksum does not match approved geography input")
    for value, maximum in ((executed_by, 160), (approval_reference, 200), (environment, 32)):
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError("Named operator, approval and environment are required")
    if db.session.new or db.session.dirty or db.session.deleted:
        raise ValueError("Geography apply requires a clean unit of work")
    plan = plan_catalog()
    run = ReferenceDataSeedRun(
        catalog_version="international-geography-v2-fwd02", catalog_family="GEOGRAPHY",
        checksum="sha256:" + CATALOG_SHA256, environment=environment,
        executed_by=executed_by, approval_reference=approval_reference,
        planned_count=len(plan["creates"]) + plan["unchanged_count"] + len(plan["conflicts"]),
        unchanged_count=plan["unchanged_count"], conflict_count=len(plan["conflicts"]),
        status="refused" if plan["conflicts"] else "started",
    )
    db.session.add(run)
    db.session.commit()
    if plan["conflicts"]:
        run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        return plan, run
    try:
        countries = {row.code: row for row in Country.query.all()}
        for change in plan["creates"]:
            item = change["source"]
            provenance = {key: item[key] for key in ("source_organization", "source_reference", "source_version")}
            if change["kind"] == "country":
                row = Country(code=item["code"], name_en=item["name_en"], name_fa=item["name_fa"],
                              dataset_id=plan["dataset_id"], **provenance)
                db.session.add(row)
                db.session.flush()
                countries[row.code] = row
            else:
                db.session.add(InternationalCity(
                    country_id=countries[change["code"]].id,
                    **{key: item[key] for key in ("un_locode", "name_en", "name_fa", "city_type", "is_major_port", "is_major_airport")},
                    dataset_id=plan["dataset_id"], **provenance,
                ))
        run.status = "succeeded"
        run.created_count = len(plan["creates"])
        # Existing audit column is proven UTC-naive; no storage contract change.
        run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        return plan, run
    except Exception:
        db.session.rollback()
        run.status = "failed"
        run.error_summary = "Geography apply rolled back; inspect operator diagnostics."
        run.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.session.commit()
        raise
