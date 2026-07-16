"""Controlled, fail-closed identity Backfill package tooling."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path, PurePosixPath
from typing import Any

from sqlalchemy import func, text

from backend.extensions import db
from backend.models import (
    City, Country, County, CustomsOffice, CustomsProvinceMapping, IranPort,
    PortCustomsOffice, PortLocation, PortProvinceMapping, Province,
)
from backend.services.reference_schema_service import validate_effective_range

SCHEMA_VERSION = "1.0"
TARGET_REVISION = "20260720_expand_reference_data_identity"
PACKAGE_TYPE = "reference_identity_backfill"
NORMALIZATION_PROFILE = "forwarder-reference-nfc-fa-v1"
DOMAINS = ("countries", "provinces", "counties", "cities", "ports", "port_locations", "port_coverage", "customs_offices", "port_customs_relationships", "customs_coverage")
IDENTITY_DOMAINS = {"provinces", "counties", "cities", "ports"}
APPLY_SEMANTICS = {"assign_missing_identity", "assign_missing_parent", "create_port_location", "update_provenance", "validate_only"}
SUPPLY_STATUSES = {"supplied", "not_supplied", "intentionally_empty", "not_applicable"}
PROVENANCE = ("source_organization", "source_reference", "source_version", "dataset_id")
LIFECYCLE = ("is_active", "effective_from", "effective_to")
APPROVAL_STATUSES = {
    "draft", "under_review", "approved_for_validation",
    "approved_for_candidate_backfill", "approved_for_production_backfill",
    "rejected", "superseded",
}
CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
CSV_ESCAPE_PREFIX = "'FORWARDER-CSV-SAFE:'"
BASE_HEADERS = (
    "record_id", "record_fingerprint_sha256", "current_name_fa", "current_name_en", "current_code",
    "current_parent_path", "current_parent_ids", "current_is_active", "current_effective_from", "current_effective_to",
    "current_source_organization", "current_source_reference", "current_source_version", "current_dataset_id",
    "proposed_code", "proposed_country_code", "proposed_parent_code", "proposed_is_active", "proposed_effective_from",
    "proposed_effective_to", "proposed_source_organization", "proposed_source_reference", "proposed_source_version",
    "proposed_dataset_id", "owner_decision", "owner_notes",
)
PORT_LOCATION_HEADERS = (
    "port_record_id", "port_fingerprint_sha256", "country_code", "province_code", "county_code", "city_code",
    "location_status", "effective_from", "effective_to", "source_organization", "source_reference", "source_version",
    "dataset_id", "owner_decision", "owner_notes",
)


def normalize(value: Any) -> str:
    value = "" if value is None else str(value)
    value = unicodedata.normalize("NFC", value).translate(str.maketrans({"ي": "ی", "ك": "ک"}))
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise ValueError("control character is forbidden")
    return " ".join(value.strip().split())


def _canonical(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _fingerprint_payload(domain: str, record: Any) -> dict[str, Any]:
    parent_ids: dict[str, Any] = {}
    for name in ("country_id", "province_id", "county_id", "city_id", "port_id", "customs_office_id"):
        if hasattr(record, name): parent_ids[name] = getattr(record, name)
    return {
        "domain": domain,
        "record_id": record.id,
        "name_fa": normalize(getattr(record, "name_fa", "")),
        "name_en": normalize(getattr(record, "name_en", "")),
        "code": getattr(record, "code", None),
        "parent_ids": parent_ids,
        "is_active": bool(getattr(record, "is_active", True)),
        "effective_from": _date(getattr(record, "effective_from", None)),
        "effective_to": _date(getattr(record, "effective_to", None)),
        "provenance": {field: getattr(record, field, None) for field in PROVENANCE},
    }


def fingerprint(domain: str, record: Any) -> str:
    return hashlib.sha256(_canonical(_fingerprint_payload(domain, record))).hexdigest()


def expected_post_fingerprint(domain: str, record: Any, row: dict[str, str]) -> str:
    try: parent_ids=json.loads(row.get("current_parent_ids") or "{}")
    except json.JSONDecodeError: parent_ids={}
    payload={"domain":domain,"record_id":int(row["record_id"]),"name_fa":normalize(row.get("current_name_fa","")),
             "name_en":normalize(row.get("current_name_en","")),"code":row.get("current_code") or None,
             "parent_ids":parent_ids,"is_active":row.get("current_is_active","true").lower()=="true",
             "effective_from":row.get("current_effective_from", ""),
             "effective_to":row.get("current_effective_to", ""),
             "provenance":{field:row.get("current_"+field) or None for field in PROVENANCE}}
    if row.get("proposed_code"): payload["code"]=row["proposed_code"]
    if row.get("proposed_country_code") and domain in {"provinces", "ports"}:
        country = Country.query.filter_by(code=row["proposed_country_code"]).one_or_none()
        if country is not None:
            payload["parent_ids"]["country_id"] = country.id
    for field in PROVENANCE:
        if row.get("proposed_" + field): payload["provenance"][field] = row["proposed_" + field]
    for field in LIFECYCLE:
        value = row.get("proposed_" + field)
        if value:
            payload[field] = value.lower() == "true" if field == "is_active" else value
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _safe_csv(value: Any) -> str:
    value = "" if value is None else str(value)
    return CSV_ESCAPE_PREFIX + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value


def _unsafecsv(value: str) -> str:
    encoded = value[len(CSV_ESCAPE_PREFIX):] if value.startswith(CSV_ESCAPE_PREFIX) else None
    return encoded if encoded is not None and encoded.startswith(("=", "+", "-", "@", "\t", "\r")) else value


def _parse_date(value: str, *, required: bool = False) -> date | None:
    if not value:
        if required: raise ValueError("date is required")
        return None
    return date.fromisoformat(value)


def _parse_bool(value: str) -> bool | None:
    if not value: return None
    if value.lower() not in {"true", "false"}: raise ValueError("boolean must be true or false")
    return value.lower() == "true"


def _date(value: Any) -> str:
    return value.isoformat() if value else ""


def _records(domain: str):
    model = {"countries": Country, "provinces": Province, "counties": County, "cities": City, "ports": IranPort,
             "port_coverage": PortProvinceMapping, "customs_offices": CustomsOffice,
             "port_customs_relationships": PortCustomsOffice, "customs_coverage": CustomsProvinceMapping,
             "port_locations": PortLocation}[domain]
    return model.query.order_by(model.id).all()


def _inventory_row(domain: str, record: Any) -> dict[str, str]:
    parents = {name: getattr(record, name) for name in ("country_id", "province_id", "county_id", "city_id", "port_id", "customs_office_id") if hasattr(record, name)}
    path = "/".join(f"{key}={parents[key]}" for key in sorted(parents) if parents[key] is not None)
    row = {key: "" for key in BASE_HEADERS}
    row.update({"record_id": str(record.id), "record_fingerprint_sha256": fingerprint(domain, record),
                "current_name_fa": getattr(record, "name_fa", "") or "", "current_name_en": getattr(record, "name_en", "") or "",
                "current_code": getattr(record, "code", "") or "", "current_parent_path": path,
                "current_parent_ids": json.dumps(parents, sort_keys=True, separators=(",", ":")),
                "current_is_active": str(bool(getattr(record, "is_active", True))).lower(),
                "current_effective_from": _date(getattr(record, "effective_from", None)),
                "current_effective_to": _date(getattr(record, "effective_to", None)),
                **{"current_"+field: getattr(record, field, None) or "" for field in PROVENANCE}})
    return {key: _safe_csv(value) for key, value in row.items()}


def export_inventory_package(output: Path, *, database_name: str, domains: set[str] | None = None) -> dict[str, Any]:
    output = output.resolve()
    repository=Path(__file__).resolve().parents[2]
    if output==repository or repository in output.parents: raise ValueError("owner inventory must be outside the repository")
    output.mkdir(parents=True, exist_ok=True); mappings = output / "mappings"; mappings.mkdir(exist_ok=True)
    chosen = set(DOMAINS if domains is None else domains)
    files = []
    counts = {}
    for domain in DOMAINS:
        path = mappings / f"{domain}.csv"
        # PortLocation is an explicit creation-intent file. Existing locations are
        # protected through their Port fingerprint and are never emitted as proposals.
        rows = [] if domain == "port_locations" else (_records(domain) if domain in chosen else [])
        headers = PORT_LOCATION_HEADERS if domain == "port_locations" else BASE_HEADERS
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers); writer.writeheader()
            if domain != "port_locations": writer.writerows(_inventory_row(domain, row) for row in rows)
        raw = path.read_bytes(); counts[domain] = len(rows)
        files.append({"path": f"mappings/{domain}.csv", "domain": domain,
                      "supplied_status": ("intentionally_empty" if domain == "port_locations" else ("supplied" if domain in chosen else "not_supplied")), "row_count": len(rows),
                      "sha256": hashlib.sha256(raw).hexdigest(), "encoding": "UTF-8", "delimiter": ",", "header_version": "1.0",
                      "apply_semantics": "create_port_location" if domain == "port_locations" else ("assign_missing_identity" if domain in IDENTITY_DOMAINS else "update_provenance")})
    manifest = {"package_schema_version": SCHEMA_VERSION, "package_type": PACKAGE_TYPE, "dataset_id": f"candidate-inventory-{date.today().isoformat()}",
                "dataset_version": "draft-1", "target_schema_revision": TARGET_REVISION, "exported_from_database": database_name,
                "exported_at": datetime.now(timezone.utc).isoformat(), "effective_date": date.today().isoformat(),
                "source_organization": "OWNER_REVIEW_REQUIRED", "source_reference": "DRAFT_INVENTORY",
                "normalization_profile": NORMALIZATION_PROFILE, "checksum_algorithm": "SHA-256", "files": files,
                "package_notes": "Draft owner-review inventory; proposed fields are intentionally blank."}
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    (output / "manifest.json").write_bytes(manifest_bytes)
    approval = {"dataset_id": manifest["dataset_id"], "dataset_version": manifest["dataset_version"],
                "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(), "approval_status": "draft", "approved_by": "OWNER_REVIEW_REQUIRED",
                "approved_at": datetime.now(timezone.utc).isoformat(), "approval_reference": "DRAFT_ONLY", "approved_domains": [],
                "approved_operations": [], "limitations": ["No apply authorization"], "candidate_apply_authorized": False,
                "production_apply_authorized": False}
    (output / "approval.DRAFT.json").write_text(json.dumps(approval, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {"status": "AWAITING_OWNER_INPUT", "counts": counts, "proposed_values_populated": 0, "production_readiness": "NO-GO"}
    (output / "inventory-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "inventory-summary.md").write_text("# Inventory summary\n\nStatus: AWAITING_OWNER_INPUT\n\n" + "\n".join(f"- {k}: {v}" for k,v in counts.items()) + "\n", encoding="utf-8")
    (output / "README_FA.md").write_text("# بسته بررسی مالک داده\n\nاین فایل صرفاً برای بررسی و تکمیل توسط مالک داده است.\nستون‌های proposed_code و proposed_* عمداً خالی هستند.\nشناسه‌های عددی فقط locator موقت هستند و کلید کسب‌وکار نیستند.\nهیچ کدی نباید از نام یا ID تولید شود.\nتکمیل فایل به‌معنای مجوز Apply نیست. Apply به Candidate و Production نیازمند تأیید مستقل است.\n", encoding="utf-8")
    return summary


@dataclass
class Issue:
    code: str; message: str; domain: str = "package"; row: int | None = None; severity: str = "error"


@dataclass
class Validation:
    status: str; issues: list[Issue] = field(default_factory=list); manifest: dict[str, Any] | None = None; rows: dict[str, list[dict[str,str]]] = field(default_factory=dict)

    def as_dict(self): return {"status": self.status, "issues": [issue.__dict__ for issue in self.issues]}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_package(path: Path, *, against_database: bool = False) -> Validation:
    path = path.resolve(); issues: list[Issue] = []; rows: dict[str,list[dict[str,str]]] = {}
    try: manifest = _load_json(path / "manifest.json")
    except Exception: return Validation("REJECTED", [Issue("MANIFEST_INVALID", "manifest.json is missing or invalid")])
    required = {"package_schema_version","package_type","dataset_id","dataset_version","target_schema_revision","exported_from_database","exported_at","effective_date","source_organization","source_reference","normalization_profile","checksum_algorithm","files","package_notes"}
    if required - manifest.keys() or manifest.get("package_schema_version") != SCHEMA_VERSION or manifest.get("package_type") != PACKAGE_TYPE or manifest.get("target_schema_revision") != TARGET_REVISION or manifest.get("checksum_algorithm") != "SHA-256":
        issues.append(Issue("MANIFEST_INVALID", "manifest contract/version/type/revision is invalid"))
    try:
        datetime.fromisoformat(str(manifest.get("exported_at", "")).replace("Z", "+00:00")); _parse_date(str(manifest.get("effective_date", "")), required=True)
    except ValueError:
        issues.append(Issue("MANIFEST_INVALID", "manifest dates are invalid"))
    seen_paths=set(); seen_domains=set()
    for entry in manifest.get("files",[]):
        rel=entry.get("path",""); pure=PurePosixPath(rel); domain=entry.get("domain","")
        if pure.is_absolute() or ".." in pure.parts or "\\" in rel or rel in seen_paths: issues.append(Issue("MANIFEST_INVALID","unsafe or duplicate path",domain))
        if domain not in DOMAINS or domain in seen_domains: issues.append(Issue("MANIFEST_INVALID","unsupported or duplicate domain",domain))
        seen_paths.add(rel); seen_domains.add(domain)
        required_entry={"path","domain","supplied_status","row_count","sha256","encoding","delimiter","header_version","apply_semantics"}
        if set(entry) != required_entry or entry.get("supplied_status") not in SUPPLY_STATUSES or entry.get("apply_semantics") not in APPLY_SEMANTICS or entry.get("encoding") != "UTF-8" or entry.get("delimiter") != "," or entry.get("header_version") != "1.0" or not isinstance(entry.get("row_count"),int) or isinstance(entry.get("row_count"), bool) or entry.get("row_count",-1)<0:
            issues.append(Issue("MANIFEST_INVALID","invalid file metadata",domain))
        expected_path=f"mappings/{domain}.csv"
        if rel != expected_path: issues.append(Issue("MANIFEST_INVALID","domain path is not canonical",domain))
        if entry.get("supplied_status") != "supplied" and entry.get("row_count") != 0:
            issues.append(Issue("MANIFEST_INVALID","non-supplied domain must declare zero rows",domain))
        file_path=(path/pure).resolve()
        if path not in file_path.parents: issues.append(Issue("MANIFEST_INVALID","path escapes package",domain)); continue
        if entry.get("supplied_status") != "supplied": continue
        try: raw=file_path.read_bytes(); decoded=raw.decode("utf-8")
        except Exception: issues.append(Issue("INVALID_UTF8","file missing or not UTF-8",domain)); continue
        if hashlib.sha256(raw).hexdigest()!=entry.get("sha256"): issues.append(Issue("CHECKSUM_MISMATCH","file checksum differs",domain))
        reader=csv.DictReader(StringIO(decoded, newline="")); parsed=list(reader); expected=PORT_LOCATION_HEADERS if domain=="port_locations" else BASE_HEADERS
        if tuple(reader.fieldnames or ()) != expected: issues.append(Issue("HEADER_MISMATCH","CSV header differs",domain))
        if len(parsed)!=entry.get("row_count"): issues.append(Issue("ROW_COUNT_MISMATCH","CSV row count differs",domain))
        for index,row in enumerate(parsed,2):
            if None in row: issues.append(Issue("HEADER_MISMATCH","CSV row contains extra columns",domain,index))
            for key,value in row.items():
                if key is not None and (value or "").startswith(("=","+","-","@","\t","\r")):
                    issues.append(Issue("CSV_INJECTION_RISK","unsafe owner-supplied value",domain,index))
        rows[domain]=[{k:((v or "") if k and (k.startswith("proposed_") or k in {"country_code","province_code","county_code","city_code","owner_decision","owner_notes"}) else _unsafecsv(v or "")) for k,v in row.items() if k is not None} for row in parsed]
    if seen_domains != set(DOMAINS): issues.append(Issue("PARTIAL_PACKAGE","manifest must declare every domain"))
    approvals=list(path.glob("approval*.json"))
    if len(approvals)!=1: issues.append(Issue("APPROVAL_INVALID","exactly one approval JSON is required")); approval={}
    else:
        try: approval=_load_json(approvals[0])
        except Exception: approval={}; issues.append(Issue("APPROVAL_INVALID","approval JSON invalid"))
    manifest_hash=hashlib.sha256((path/"manifest.json").read_bytes()).hexdigest()
    approval_required={"dataset_id","dataset_version","manifest_sha256","approval_status","approved_by","approved_at","approval_reference","approved_domains","approved_operations","limitations","candidate_apply_authorized","production_apply_authorized"}
    if set(approval) != approval_required or approval.get("approval_status") not in APPROVAL_STATUSES:
        issues.append(Issue("APPROVAL_INVALID","approval fields/status are invalid"))
    if not isinstance(approval.get("approved_domains"), list) or not set(approval.get("approved_domains", [])).issubset(DOMAINS):
        issues.append(Issue("APPROVAL_INVALID","approved domains are invalid"))
    if not isinstance(approval.get("approved_operations"), list) or not set(approval.get("approved_operations", [])).issubset(APPLY_SEMANTICS):
        issues.append(Issue("APPROVAL_INVALID","approved operations are invalid"))
    if approval.get("approval_status") in {"rejected", "superseded"}:
        issues.append(Issue("APPROVAL_INVALID","approval status is not actionable"))
    try:
        datetime.fromisoformat(str(approval.get("approved_at", "")).replace("Z", "+00:00"))
    except ValueError:
        issues.append(Issue("APPROVAL_INVALID","approved_at is invalid"))
    if approval.get("production_apply_authorized") and approval.get("approval_status")!="approved_for_production_backfill": issues.append(Issue("APPROVAL_INVALID","production authorization/status mismatch"))
    if approval.get("candidate_apply_authorized") and approval.get("approval_status")!="approved_for_candidate_backfill": issues.append(Issue("APPROVAL_INVALID","candidate authorization/status mismatch"))
    if approval.get("dataset_id")!=manifest.get("dataset_id") or approval.get("dataset_version")!=manifest.get("dataset_version") or approval.get("manifest_sha256")!=manifest_hash:
        issues.append(Issue("APPROVAL_INVALID","approval identity/checksum mismatch"))
    approved_domains=set(approval.get("approved_domains",[])); approved_operations=set(approval.get("approved_operations",[]))
    for entry in manifest.get("files",[]):
        if entry.get("supplied_status")=="supplied" and entry.get("row_count",0)>0 and approval.get("approval_status") not in {"draft","under_review","approved_for_validation"}:
            if entry.get("domain") not in approved_domains: issues.append(Issue("UNAUTHORIZED_DOMAIN","domain is not approved",entry.get("domain","package")))
            if entry.get("apply_semantics") not in approved_operations: issues.append(Issue("UNAUTHORIZED_OPERATION","operation is not approved",entry.get("domain","package")))
    awaiting=False
    for domain in IDENTITY_DOMAINS:
        proposed_seen: set[tuple[str, str]] = set()
        for index,row in enumerate(rows.get(domain,[]),2):
            if not row.get("proposed_code"): awaiting=True; issues.append(Issue("MISSING_PROPOSED_CODE","owner code is blank",domain,index,"information"))
            else:
                if not CODE_RE.fullmatch(row["proposed_code"]): issues.append(Issue("MANIFEST_INVALID","proposed code format is invalid",domain,index))
                scope = row.get("proposed_country_code") if domain in {"provinces", "ports"} else row.get("current_parent_ids", "")
                key = (scope or "", row["proposed_code"])
                if key in proposed_seen: issues.append(Issue("DUPLICATE_PROPOSED_CODE","duplicate proposed code in scope",domain,index))
                proposed_seen.add(key)
            if not re.fullmatch(r"[0-9a-f]{64}",row.get("record_fingerprint_sha256","")): issues.append(Issue("MANIFEST_INVALID","fingerprint format invalid",domain,index))
            try:
                start=_parse_date(row.get("proposed_effective_from", "")); end=_parse_date(row.get("proposed_effective_to", "")); validate_effective_range(start,end)
                _parse_bool(row.get("proposed_is_active", ""))
            except (ValueError, TypeError): issues.append(Issue("EFFECTIVE_RANGE_INVALID","lifecycle values are invalid",domain,index))
            if row.get("proposed_code") and not row.get("proposed_source_organization"):
                issues.append(Issue("PROVENANCE_MISSING","source organization is required for an approved identity",domain,index))
            if row.get("proposed_code") and not row.get("proposed_source_reference"):
                issues.append(Issue("PROVENANCE_MISSING","source reference is required for an approved identity",domain,index))
    if against_database:
        revision=db.session.execute(text("select version_num from alembic_version")).scalar_one()
        if revision!=TARGET_REVISION: issues.append(Issue("MANIFEST_INVALID","target revision mismatch"))
        for domain, domain_rows in rows.items():
            if domain not in DOMAINS: continue
            if domain=="port_locations":
                for index,row in enumerate(domain_rows,2):
                    port=db.session.get(IranPort,int(row["port_record_id"])) if row.get("port_record_id","").isdigit() else None
                    if port is None: issues.append(Issue("RECORD_NOT_FOUND","port locator not found",domain,index)); continue
                    port_row=next((item for item in rows.get("ports",[]) if item.get("record_id")==row.get("port_record_id")),None)
                    current_port=fingerprint("ports",port)
                    post_match=bool(port_row and current_port==expected_post_fingerprint("ports",port,port_row)
                                    and row.get("port_fingerprint_sha256")==port_row.get("record_fingerprint_sha256"))
                    if current_port!=row.get("port_fingerprint_sha256") and not post_match:
                        issues.append(Issue("RECORD_DRIFT","port fingerprint differs",domain,index))
                continue
            model={"countries":Country,"provinces":Province,"counties":County,"cities":City,"ports":IranPort,"port_coverage":PortProvinceMapping,"customs_offices":CustomsOffice,"port_customs_relationships":PortCustomsOffice,"customs_coverage":CustomsProvinceMapping}[domain]
            for index,row in enumerate(domain_rows,2):
                record=db.session.get(model,int(row["record_id"])) if row.get("record_id","").isdigit() else None
                if record is None: issues.append(Issue("RECORD_NOT_FOUND","locator not found",domain,index)); continue
                current=fingerprint(domain,record)
                post_match=current==expected_post_fingerprint(domain,record,row)
                if current!=row.get("record_fingerprint_sha256") and not post_match: issues.append(Issue("RECORD_DRIFT","current record fingerprint differs",domain,index))
                if getattr(record,"code",None) and row.get("proposed_code") and getattr(record,"code")!=row["proposed_code"]: issues.append(Issue("CURRENT_CODE_CONFLICT","existing code differs from proposed code",domain,index))
    errors=[i for i in issues if i.severity=="error"]
    status="REJECTED" if errors else ("AWAITING_OWNER_INPUT" if awaiting or approval.get("approval_status")=="draft" else ("PASS_WITH_WARNINGS" if issues else "PASS"))
    return Validation(status,issues,manifest,rows)


def diff_package(path: Path) -> dict[str,Any]:
    validation=validate_package(path,against_database=True); items=[]
    if validation.status in {"REJECTED","BLOCKED"}: return {"status":validation.status,"planned_writes":0,"items":[],"issues":validation.as_dict()["issues"]}
    models={"countries":Country,"provinces":Province,"counties":County,"cities":City,"ports":IranPort,
            "port_coverage":PortProvinceMapping,"customs_offices":CustomsOffice,
            "port_customs_relationships":PortCustomsOffice,"customs_coverage":CustomsProvinceMapping}
    for domain in ("countries","provinces","counties","cities","ports","port_coverage","customs_offices","port_customs_relationships","customs_coverage"):
        for row in validation.rows.get(domain,[]):
            record=db.session.get(models[domain],int(row["record_id"])); changes=[]
            if row.get("proposed_code") and row["proposed_code"] != (getattr(record,"code",None) or ""): changes.append("assign_code")
            if domain in {"provinces","ports"} and row.get("proposed_country_code"):
                country=Country.query.filter_by(code=row["proposed_country_code"]).one_or_none()
                if country and getattr(record,"country_id",None)!=country.id: changes.append("assign_country")
            if any(row.get("proposed_"+name) and row.get("proposed_"+name)!=getattr(record,name) for name in ("source_organization","source_reference","source_version","dataset_id")): changes.append("update_provenance")
            if any(row.get("proposed_"+name) and row.get("proposed_"+name)!=_date(getattr(record,name,None)) for name in ("effective_from","effective_to")): changes.append("update_lifecycle")
            if row.get("proposed_is_active") and _parse_bool(row["proposed_is_active"])!=getattr(record,"is_active",None): changes.append("update_lifecycle")
            category=changes[0] if changes else ("awaiting_owner_input" if domain in IDENTITY_DOMAINS and not row.get("proposed_code") else "unchanged")
            items.append({"domain":domain,"record_id":record.id,"category":category,"changes":changes})
    for row in validation.rows.get("port_locations",[]):
        port_id=int(row["port_record_id"]); existing=PortLocation.query.filter_by(port_id=port_id,is_active=True).one_or_none()
        changes=[] if existing else ["create_port_location"]
        items.append({"domain":"port_locations","record_id":port_id,"category":changes[0] if changes else "unchanged","changes":changes})
    items.sort(key=lambda x:(DOMAINS.index(x["domain"]),x["record_id"],x["category"]))
    writes=sum(bool(i["changes"]) for i in items)
    return {"status":validation.status,"planned_writes":writes,"items":items,"issues":validation.as_dict()["issues"]}


FORBIDDEN_TARGETS={"forwarder_db","forwarder_candidate_uat_20260717","postgres","template0","template1"}


def mutable_target_allowed(database_name: str) -> bool:
    return bool(
        re.fullmatch(r"[A-Za-z0-9_]+", database_name or "")
        and database_name not in FORBIDDEN_TARGETS
        and "prod" not in database_name.lower()
        and database_name.startswith(("forwarder_backfill_test_","forwarder_backfill_candidate_test_"))
    )


def apply_package(path: Path, *, database_name: str, apply: bool) -> dict[str,Any]:
    if not mutable_target_allowed(database_name):
        return {"status":"REJECTED","code":"FORBIDDEN_TARGET","writes":0}
    if db.engine.dialect.name=="postgresql" and db.session.execute(text("select current_database()" )).scalar_one()!=database_name:
        return {"status":"REJECTED","code":"FORBIDDEN_TARGET","writes":0}
    validation=validate_package(path,against_database=True); diff=diff_package(path)
    if not apply: return {"status":validation.status,"mode":"dry_run","writes":0,"planned_writes":diff["planned_writes"]}
    approval_paths=list(path.resolve().glob("approval*.json")); approval=_load_json(approval_paths[0]) if len(approval_paths)==1 else {}
    if validation.status not in {"PASS","PASS_WITH_WARNINGS"} or approval.get("approval_status") != "approved_for_candidate_backfill" or not approval.get("candidate_apply_authorized") or approval.get("production_apply_authorized"):
        return {"status":"REJECTED","code":"APPLY_NOT_AUTHORIZED","writes":0}
    writes=0
    try:
        if db.engine.dialect.name=="postgresql": db.session.execute(text("select pg_advisory_xact_lock(742021)"))
        locked_pre={}
        model_map={"countries":Country,"provinces":Province,"counties":County,"cities":City,"ports":IranPort,"port_coverage":PortProvinceMapping,"customs_offices":CustomsOffice,"port_customs_relationships":PortCustomsOffice,"customs_coverage":CustomsProvinceMapping}
        for domain in model_map:
            ids=sorted(int(row["record_id"]) for row in validation.rows.get(domain,[]) if row.get("record_id","").isdigit())
            if ids:
                records=db.session.query(model_map[domain]).filter(model_map[domain].id.in_(ids)).order_by(model_map[domain].id).with_for_update().all()
                locked_pre.update({(domain,r.id):fingerprint(domain,r) for r in records})
        for domain,domain_rows in validation.rows.items():
            if domain in model_map:
                for row in domain_rows:
                    if row.get("record_id") and locked_pre.get((domain,int(row["record_id"]))) not in {row.get("record_fingerprint_sha256"),expected_post_fingerprint(domain,db.session.get(model_map[domain],int(row["record_id"])),row)}: raise ValueError("record drift after lock")
        for domain in ("countries","provinces","counties","cities","ports"):
            model={"countries":Country,"provinces":Province,"counties":County,"cities":City,"ports":IranPort}[domain]
            for row in validation.rows.get(domain,[]):
                record=db.session.get(model,int(row["record_id"])); code=row.get("proposed_code")
                if code and not getattr(record,"code",None): record.code=code; writes+=1
                if domain in {"provinces","ports"} and row.get("proposed_country_code") and getattr(record,"country_id",None) is None:
                    country=Country.query.filter_by(code=row["proposed_country_code"]).one_or_none()
                    if country is None: raise ValueError("proposed country code does not exist")
                    record.country_id=country.id; writes+=1
                for field in PROVENANCE:
                    proposed=row.get("proposed_"+field)
                    if proposed and getattr(record,field)!=proposed: setattr(record,field,proposed); writes+=1
                proposed_active=_parse_bool(row.get("proposed_is_active", ""))
                if proposed_active is not None and getattr(record,"is_active",None) != proposed_active:
                    record.is_active=proposed_active; writes+=1
                for field in ("effective_from", "effective_to"):
                    proposed=row.get("proposed_"+field)
                    if proposed:
                        parsed=_parse_date(proposed)
                        if getattr(record,field,None) != parsed: setattr(record,field,parsed); writes+=1
        for row in validation.rows.get("port_locations",[]):
            if not row.get("port_record_id"): continue
            port=db.session.get(IranPort,int(row["port_record_id"])); country=Country.query.filter_by(code=row.get("country_code")).one_or_none()
            province=Province.query.filter_by(code=row.get("province_code"),country_id=country.id if country else None).one_or_none()
            port_package_row=next((item for item in validation.rows.get("ports",[]) if item.get("record_id")==row.get("port_record_id")),None)
            accepted_port_fingerprints={fingerprint("ports",port)}
            if port_package_row:
                accepted_port_fingerprints.add(port_package_row.get("record_fingerprint_sha256", ""))
                accepted_port_fingerprints.add(expected_post_fingerprint("ports",port,port_package_row))
            if port is None or country is None or province is None or row.get("port_fingerprint_sha256") not in accepted_port_fingerprints: raise ValueError("invalid port location locator/hierarchy")
            county=County.query.filter_by(code=row.get("county_code"),province_id=province.id).one_or_none() if row.get("county_code") else None
            city=City.query.filter_by(code=row.get("city_code"),county_id=county.id).one_or_none() if row.get("city_code") and county else None
            if row.get("county_code") and county is None or row.get("city_code") and city is None: raise ValueError("invalid port location hierarchy")
            existing=PortLocation.query.filter_by(port_id=port.id,is_active=True).one_or_none()
            if existing is None:
                db.session.add(PortLocation(port_id=port.id,country_id=country.id,province_id=province.id,county_id=county.id if county else None,city_id=city.id if city else None,
                    location_status=row.get("location_status") or "unknown", source_organization=row.get("source_organization") or None,
                    source_reference=row.get("source_reference") or None,source_version=row.get("source_version") or None,dataset_id=row.get("dataset_id") or None,
                    effective_from=_parse_date(row.get("effective_from", "")), effective_to=_parse_date(row.get("effective_to", "")))); writes+=1
        for domain,model in (("port_coverage",PortProvinceMapping),("customs_offices",CustomsOffice),("port_customs_relationships",PortCustomsOffice),("customs_coverage",CustomsProvinceMapping)):
            for row in validation.rows.get(domain,[]):
                record=db.session.get(model,int(row["record_id"]))
                for field in PROVENANCE:
                    proposed=row.get("proposed_"+field)
                    if proposed and getattr(record,field)!=proposed: setattr(record,field,proposed); writes+=1
        db.session.flush()
        # Final invariant validation is intentionally inside the write transaction.
        for model in (Country,Province,County,City,IranPort,PortProvinceMapping,CustomsOffice,PortCustomsOffice,PortLocation,CustomsProvinceMapping):
            for record in model.query.all():
                validate_effective_range(getattr(record,"effective_from",None),getattr(record,"effective_to",None))
        for model,parent in ((Province,"country_id"),(County,"province_id"),(City,"county_id"),(IranPort,"country_id")):
            parent_column=getattr(model,parent)
            duplicate=db.session.query(parent_column,getattr(model,"code")).filter(getattr(model,"code").isnot(None)).group_by(parent_column,getattr(model,"code")).having(func.count(model.id)>1).first()
            if duplicate: raise ValueError("duplicate scoped code after apply")
        inconsistent_city=db.session.query(City.id).join(County,City.county_id==County.id).filter(City.province_id!=County.province_id).first()
        if inconsistent_city: raise ValueError("city hierarchy is inconsistent")
        # This is the transaction-safe subset of schema readiness. The shared
        # report performs engine-level inspection, which must not open another
        # connection while this transaction owns uncommitted changes.
        if db.session.query(PortProvinceMapping.port_id,PortProvinceMapping.province_id).group_by(
                PortProvinceMapping.port_id,PortProvinceMapping.province_id).having(func.count(PortProvinceMapping.id)>1).first():
            raise ValueError("reference schema coverage conflict")
        db.session.commit(); return {"status":"PASS","mode":"apply","writes":writes}
    except Exception:
        db.session.rollback(); return {"status":"REJECTED","code":"TRANSACTION_ROLLED_BACK","writes":0}
