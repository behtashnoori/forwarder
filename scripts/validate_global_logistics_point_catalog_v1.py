"""Build and validate the read-only China→Iran GlobalLogisticsPoint V1 review package.

This tool never imports Flask, opens a database, or calls a mutation API.
"""
from __future__ import annotations

import hashlib
import ast
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LEGACY_SOURCE = ROOT / "backend/services/tracking_location_bootstrap_service.py"

def _literal_assignment(name: str):
    tree = ast.parse(LEGACY_SOURCE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == name for x in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError(f"missing literal {name} in legacy source")

ROWS = _literal_assignment("ROWS")
NOTES = _literal_assignment("NOTES")

PACKAGE = ROOT / "backend/reference_data/global-logistics-points-china-iran-v1.0.0.json"
APPROVED_BASELINE = ROOT / "backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json"
RECONCILIATION = ROOT / "docs/operational/data/global-logistics-points-china-iran-v1.0.0-legacy-reconciliation.json"
REPORT = ROOT / "docs/operational/data/global-logistics-points-china-iran-v1.0.0-owner-review.md"
OWNER_DECISION = ROOT / "docs/operational/data/global-logistics-points-china-iran-v1.0.0-baseline-owner-decision.md"

APPROVED_CODES = (
    "GLP-CN-ALASHANKOU",
    "GLP-CN-NINGBO-ZHOUSHAN",
    "GLP-IR-INCHEH-BORUN",
    "GLP-IR-SARAKHS",
    "GLP-KG-IRKESHTAM",
    "GLP-KZ-ALTYNKOL",
    "GLP-KZ-DOSTYK",
    "GLP-TM-FARAP",
    "GLP-TM-SERAKHS",
)

TYPE_CODES = {"FACTORY", "WAREHOUSE", "DISTRIBUTION_CENTER", "CUSTOMS", "PORT",
              "BORDER_CROSSING", "AIRPORT", "RAIL_TERMINAL", "ROAD_TERMINAL",
              "CUSTOMER_SITE", "OTHER_GOVERNED"}
MODES = {"ROAD", "RAIL", "SEA", "AIR", "MULTIMODAL"}
TAGS = {"CHINA_IRAN_MAIN", "CHINA_CENTRAL_ASIA_IRAN", "CHINA_KAZAKHSTAN_IRAN",
        "CHINA_KYRGYZSTAN_UZBEKISTAN_IRAN", "CHINA_SEA_IRAN", "CENTRAL_ASIA_IRAN"}
PACKAGE_STATES = {"READY_FOR_OWNER_APPROVAL", "NEEDS_OWNER_DECISION",
                  "NEEDS_EXTERNAL_VERIFICATION", "REJECTED_FOR_V1"}
CLASSES = {"CORE_V1", "OPTIONAL_V1", "FUTURE", "LEGACY_ONLY", "NEEDS_OWNER_REVIEW",
           "NEEDS_EXTERNAL_VERIFICATION", "NEEDS_SPLIT"}

REPO_SOURCE = {
    "source_type": "REPOSITORY-DERIVED",
    "source_organization": "Forwarder repository",
    "source_title": "Curated China-to-Iran tracking checkpoint bootstrap",
    "source_reference": "backend/services/tracking_location_bootstrap_service.py@6331ed95",
    "source_url": None,
    "source_version": "6331ed95",
    "checked_date": "2026-08-23",
}
UNECE = ("UNECE UN/LOCODE 2025-1", "https://unlocode.unece.org/publications/")
CAREC = ("CAREC border-crossing points", "https://cpmm.carecprogram.org/2023-report/appendix-7-central-asia-regional-economic-cooperation-border-crossing-points/")
CAREC_RAIL = ("CAREC railway assessment", "https://www.carecprogram.org/uploads/Situation-of-Railways-in-CAREC_8th_2022-9-19_WEB.pdf")
SIPG = ("Shanghai International Port Group", "https://en.portshanghai.com.cn/")
NBPORT = ("Ningbo-Zhoushan Port official site", "https://www.nbport.com.cn/")
CHINA_RAIL = ("China National Railway Administration unified China Railway Express brand", "https://www.nra.gov.cn/jglz/ysjg/jgys/201606/t20160608_326739.shtml")
XIAN = ("Xi'an government China-Europe freight train", "https://en.xa.gov.cn/MediaCenter/News/1848626630021976066.html")
TURKMEN = ("Government of Turkmenistan regional transport projects", "https://turkmenistan.gov.tm/en/post/11700/turkmenistan-implements-regional-and-transcontinental-transport-projects")
UNECE_IR_RAIL = ("UNECE Railways of the Islamic Republic of Iran", "https://unece.org/sites/default/files/2025-04/3%20ppt%20Farhad%20Sheidei%20%28Iran%29.pdf")

def ext_source(pair: tuple[str, str]) -> dict:
    title, url = pair
    return {"source_type": "EXTERNAL-VERIFIED", "source_organization": title.split()[0],
            "source_title": title, "source_reference": url, "source_url": url,
            "source_version": "retrieved-2026-08-23", "checked_date": "2026-08-23"}

LEGACY = {row[0]: row for row in ROWS}

# key, tier, type, modes, tags, classification, package state, authoritative source
CANDIDATES = [
 ("cn-shanghai","CORE_V1","PORT",["SEA"],["CHINA_SEA_IRAN"],"NEEDS_SPLIT","NEEDS_OWNER_DECISION",SIPG),
 ("cn-ningbo-zhoushan","CORE_V1","PORT",["SEA"],["CHINA_SEA_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",NBPORT),
 ("cn-shenzhen-yantian","CORE_V1","PORT",["SEA"],["CHINA_SEA_IRAN"],"NEEDS_SPLIT","NEEDS_OWNER_DECISION",UNECE),
 ("cn-guangzhou-nansha","CORE_V1","PORT",["SEA"],["CHINA_SEA_IRAN"],"NEEDS_SPLIT","NEEDS_OWNER_DECISION",UNECE),
 ("cn-xian","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_IRAN_MAIN","CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",XIAN),
 ("cn-zhengzhou","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_IRAN_MAIN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",CHINA_RAIL),
 ("cn-chengdu","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_IRAN_MAIN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",CHINA_RAIL),
 ("cn-chongqing","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_IRAN_MAIN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",CHINA_RAIL),
 ("cn-urumqi","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC_RAIL),
 ("cn-kashgar","CORE_V1","ROAD_TERMINAL",["ROAD"],["CHINA_KYRGYZSTAN_UZBEKISTAN_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC),
 ("cn-alashankou","CORE_V1","BORDER_CROSSING",["ROAD","RAIL"],["CHINA_KAZAKHSTAN_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",CAREC),
 ("cn-khorgos","CORE_V1","BORDER_CROSSING",["ROAD","RAIL"],["CHINA_KAZAKHSTAN_IRAN"],"NEEDS_SPLIT","NEEDS_OWNER_DECISION",CAREC),
 ("kz-dostyk","CORE_V1","BORDER_CROSSING",["ROAD","RAIL"],["CHINA_KAZAKHSTAN_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",CAREC),
 ("kz-altynkol","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_KAZAKHSTAN_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",CAREC_RAIL),
 ("KG-OSH","CORE_V1","ROAD_TERMINAL",["ROAD"],["CHINA_KYRGYZSTAN_UZBEKISTAN_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC),
 ("kg-irkeshtam","CORE_V1","BORDER_CROSSING",["ROAD"],["CHINA_KYRGYZSTAN_UZBEKISTAN_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",CAREC),
 ("uz-tashkent","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC_RAIL),
 ("uz-bukhara","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC_RAIL),
 ("tm-farap","CORE_V1","BORDER_CROSSING",["ROAD","RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",CAREC),
 ("tm-turkmenabat","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC_RAIL),
 ("tm-mary","CORE_V1","RAIL_TERMINAL",["RAIL"],["CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",TURKMEN),
 ("tm-tejen","CORE_V1","RAIL_TERMINAL",["RAIL"],["CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",TURKMEN),
 ("tm-serakhs","CORE_V1","BORDER_CROSSING",["ROAD","RAIL"],["CENTRAL_ASIA_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",UNECE_IR_RAIL),
 ("ir-sarakhs","CORE_V1","BORDER_CROSSING",["ROAD","RAIL"],["CENTRAL_ASIA_IRAN","CHINA_IRAN_MAIN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",UNECE_IR_RAIL),
 ("ir-incheh-borun","CORE_V1","BORDER_CROSSING",["ROAD","RAIL"],["CENTRAL_ASIA_IRAN"],"CORE_V1","READY_FOR_OWNER_APPROVAL",TURKMEN),
 ("ir-mashhad","CORE_V1","RAIL_TERMINAL",["RAIL"],["CHINA_IRAN_MAIN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",UNECE_IR_RAIL),
 ("ir-shahid-rajaee","CORE_V1","PORT",["SEA","RAIL","ROAD"],["CHINA_SEA_IRAN","CHINA_IRAN_MAIN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",UNECE),
 ("ir-chabahar","CORE_V1","PORT",["SEA","ROAD"],["CHINA_SEA_IRAN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",UNECE),
 ("ir-imam-khomeini","CORE_V1","PORT",["SEA","RAIL","ROAD"],["CHINA_SEA_IRAN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",UNECE),
 ("cn-qingdao","OPTIONAL_V1","PORT",["SEA"],["CHINA_SEA_IRAN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",UNECE),
 ("cn-tianjin-xingang","OPTIONAL_V1","PORT",["SEA"],["CHINA_SEA_IRAN"],"NEEDS_SPLIT","NEEDS_OWNER_DECISION",UNECE),
 ("cn-yiwu","OPTIONAL_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CHINA_RAIL),
 ("cn-wuhan","OPTIONAL_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CHINA_RAIL),
 ("cn-lanzhou","OPTIONAL_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CHINA_RAIL),
 ("kz-almaty","OPTIONAL_V1","ROAD_TERMINAL",["ROAD","RAIL"],["CHINA_KAZAKHSTAN_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC_RAIL),
 ("kz-shymkent","OPTIONAL_V1","ROAD_TERMINAL",["ROAD","RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_OWNER_REVIEW","NEEDS_OWNER_DECISION",CAREC_RAIL),
 ("uz-navoi","OPTIONAL_V1","RAIL_TERMINAL",["RAIL"],["CHINA_CENTRAL_ASIA_IRAN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",CAREC_RAIL),
 ("ir-amirabad","OPTIONAL_V1","PORT",["SEA","RAIL","ROAD"],["CENTRAL_ASIA_IRAN"],"NEEDS_EXTERNAL_VERIFICATION","NEEDS_EXTERNAL_VERIFICATION",UNECE),
 ("ir-anzali-caspian","OPTIONAL_V1","PORT",["SEA","ROAD"],["CENTRAL_ASIA_IRAN"],"NEEDS_SPLIT","NEEDS_OWNER_DECISION",UNECE),
]

NEW = {
 "kg-irkeshtam": ("kg-irkeshtam", "گذرگاه ایرکشتام (سمت قرقیزستان)", "Irkeshtam Border Crossing — Kyrgyzstan Side", "KG", "border_point", ["Irkeshtam"]),
}
PAIR = {"cn-alashankou":"CN-KZ-ALASHANKOU-DOSTYK", "kz-dostyk":"CN-KZ-ALASHANKOU-DOSTYK",
        "cn-khorgos":"CN-KZ-HORGOS-ALTYNKOL", "kz-altynkol":"CN-KZ-HORGOS-ALTYNKOL",
        "tm-farap":"UZ-TM-ALAT-FARAP", "tm-serakhs":"TM-IR-SERAKHS-SARAKHS",
        "ir-sarakhs":"TM-IR-SERAKHS-SARAKHS", "ir-incheh-borun":"TM-IR-AKYAYLA-INCHEH-BORUN",
        "kg-irkeshtam":"CN-KG-IRKESHTAM"}
EXTERNAL_CODES = {"cn-shanghai":[{"scheme":"UNLOCODE","value":"CNSHA","source_reference":UNECE[1]}],
                  "cn-alashankou":[{"scheme":"UNLOCODE","value":"CNAKL","source_reference":UNECE[1]}],
                  "ir-anzali-caspian":[{"scheme":"UNLOCODE","value":"IRBAZ","source_reference":"https://unlocode.unece.org/directory/locodes?country=IR&subdivision=01"}]}

def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().replace("\u200c", " ")
    return " ".join(value.split())

def slug(key: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", key.upper()).strip("-")

def runtime_row(spec: tuple) -> dict:
    key, tier, point_type, modes, tags, classification, state, authority = spec
    legacy = LEGACY.get(key) or NEW[key]
    _, fa_name, en_name, country, _, aliases = legacy
    code = f"GLP-{country}-{slug(key.split('-',1)[-1])}"
    facility = norm(code.replace("GLP-", ""))
    border = point_type == "BORDER_CROSSING"
    filtered_aliases = []
    seen_aliases = {norm(fa_name), norm(en_name)}
    for alias in aliases:
        normalized = norm(alias)
        if normalized and normalized not in seen_aliases:
            filtered_aliases.append({"value": alias, "language_code": None})
            seen_aliases.add(normalized)
    runtime = {
        "immutable_code": code, "point_type_code": point_type, "country_code": country,
        "fa_name": fa_name, "en_name": en_name, "normalized_name": norm(en_name),
        "facility_identity_key": facility, "geography_key": f"{country}:{facility}",
        "region_name": None, "city_name": None, "short_address": None,
        "latitude": None, "longitude": None, "timezone": None, "un_locode": None,
        "border_pair_key": PAIR.get(key),
        "border_side": "BIDIRECTIONAL" if border else "NOT_APPLICABLE",
        "supported_modes": modes, "corridor_tags": tags,
        "aliases": filtered_aliases,
        "external_codes": EXTERNAL_CODES.get(key, []),
        "proposed_lifecycle_status": "DRAFT", "proposed_verification_status": "UNVERIFIED",
    }
    sources = [dict(REPO_SOURCE), ext_source(authority)]
    review = {"tier": tier, "classification": classification, "package_review_status": state,
              "legacy_keys": [key] if key in LEGACY else [], "evidence_class": "EXTERNAL-VERIFIED",
              "sources": sources, "open_questions": []}
    if classification == "NEEDS_SPLIT": review["open_questions"].append("Owner must choose port-complex/crossing boundary or split into named facilities.")
    if classification in {"NEEDS_OWNER_REVIEW", "NEEDS_EXTERNAL_VERIFICATION"}:
        review["open_questions"].append("Confirm the exact bounded terminal/facility identity; the legacy label may denote a city or broad hub.")
    return {"runtime_candidate": runtime, "review": review}

def disposition(key: str) -> tuple[str, list[str], str, str]:
    matches = [runtime_row(x) for x in CANDIDATES if x[0] == key]
    if matches:
        item = matches[0]
        return item["review"]["classification"], [item["runtime_candidate"]["immutable_code"]], "MEDIUM" if item["review"]["package_review_status"] != "READY_FOR_OWNER_APPROVAL" else "HIGH", "Candidate only; no mapping row authorized."
    country = key.split("-", 1)[0].upper()
    if country in {"PK", "AF"}:
        return "LEGACY_ONLY", [], "HIGH", "Alternate Pakistan/Afghanistan corridor excluded from V1 scope pending owner business justification."
    return "FUTURE", [], "LOW", "Legacy tracking geography is not a bounded V1 global facility candidate."

def unsigned_package() -> dict:
    rows = sorted((runtime_row(x) for x in CANDIDATES), key=lambda x: x["runtime_candidate"]["immutable_code"])
    return {"schema_version":"1", "catalog_version":"china-iran-global-logistics-points-1.0.0",
            "scope":"China→Iran operational spine; owner review only", "source_version":"6331ed95+external-review-2026-08-23",
            "generated_metadata":{"generated_date":"2026-08-23", "generator":"scripts/validate_global_logistics_point_catalog_v1.py",
                                  "canonicalization":"UTF-8 JSON; sort_keys=true; separators=(',',':'); checksum field excluded",
                                  "production_seed_authorized":False},
            "global_logistics_points":rows}

def checksum(payload: dict) -> str:
    unsigned = {k:v for k,v in payload.items() if k != "checksum"}
    raw = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def unsigned_approved_baseline(parent: dict) -> dict:
    ready = {
        item["runtime_candidate"]["immutable_code"]: item
        for item in parent["global_logistics_points"]
        if item["review"]["package_review_status"] == "READY_FOR_OWNER_APPROVAL"
    }
    return {
        "schema_version": "1",
        "catalog_version": "china-iran-global-logistics-points-1.0.0-approved-baseline",
        "parent_catalog_version": parent["catalog_version"],
        "parent_catalog_path": str(PACKAGE.relative_to(ROOT)).replace("\\", "/"),
        "parent_catalog_checksum": parent["checksum"],
        "owner_decision_reference": str(OWNER_DECISION.relative_to(ROOT)).replace("\\", "/"),
        "approved_subset_count": len(APPROVED_CODES),
        "production_seed_authorized": False,
        "canonicalization": "UTF-8 JSON; sort_keys=true; separators=(',',':'); checksum field excluded",
        "approved_global_logistics_points": [ready[code] for code in APPROVED_CODES],
    }

def validate_approved_baseline(parent: dict, baseline: dict) -> list[str]:
    errors = []
    rows = baseline.get("approved_global_logistics_points", [])
    parent_ready = {
        item["runtime_candidate"]["immutable_code"]: item
        for item in parent.get("global_logistics_points", [])
        if item.get("review", {}).get("package_review_status") == "READY_FOR_OWNER_APPROVAL"
    }
    if baseline.get("checksum") != checksum(baseline): errors.append("approved baseline checksum mismatch")
    if baseline.get("approved_subset_count") != 9 or len(rows) != 9: errors.append("approved baseline is not exactly 9 rows")
    if baseline.get("production_seed_authorized") is not False: errors.append("approved baseline must not authorize Production seed")
    if baseline.get("parent_catalog_version") != parent.get("catalog_version"): errors.append("approved baseline parent version mismatch")
    if baseline.get("parent_catalog_checksum") != parent.get("checksum"): errors.append("approved baseline parent checksum mismatch")
    codes = [item.get("runtime_candidate", {}).get("immutable_code") for item in rows]
    if tuple(codes) != APPROVED_CODES: errors.append("approved baseline codes/order differ from owner decision")
    if set(codes) != set(parent_ready) or len(parent_ready) != 9: errors.append("approved baseline does not exactly equal current READY rows")
    identities = []
    for item in rows:
        runtime = item.get("runtime_candidate", {})
        review = item.get("review", {})
        code = runtime.get("immutable_code")
        identity = (runtime.get("country_code"), runtime.get("point_type_code"), runtime.get("facility_identity_key"))
        identities.append(identity)
        if parent_ready.get(code) != item: errors.append(f"approved row differs from parent {code}")
        if runtime.get("point_type_code") not in TYPE_CODES: errors.append(f"invalid approved type {code}")
        if not set(runtime.get("supported_modes", [])) <= MODES or not runtime.get("supported_modes"): errors.append(f"invalid approved modes {code}")
        if not re.fullmatch(r"[A-Z]{2}", runtime.get("country_code", "")): errors.append(f"invalid approved country {code}")
        if review.get("package_review_status") != "READY_FOR_OWNER_APPROVAL" or review.get("open_questions"): errors.append(f"unresolved row in approved baseline {code}")
        source_types = {source.get("source_type") for source in review.get("sources", [])}
        if not {"REPOSITORY-DERIVED", "EXTERNAL-VERIFIED"} <= source_types: errors.append(f"approved row lacks required provenance {code}")
        is_border = runtime.get("point_type_code") == "BORDER_CROSSING"
        if is_border and (not runtime.get("border_pair_key") or runtime.get("border_side") not in {"ENTRY", "EXIT", "BIDIRECTIONAL"}): errors.append(f"invalid approved border pair {code}")
    if len(codes) != len(set(codes)): errors.append("duplicate approved immutable_code")
    if len(identities) != len(set(identities)): errors.append("duplicate approved facility identity")
    return errors

def reconciliation_rows() -> list[dict]:
    result=[]
    for order,(key,fa,en,country,kind,aliases) in enumerate(ROWS):
        disp,codes,confidence,note=disposition(key)
        result.append({"legacy_internal_key":key,"legacy_name":{"fa":fa,"en":en},"country_code":country,
                       "legacy_type":kind,"aliases":aliases,"reference_status":"internal_reference",
                       "sort_order":order,"notes":NOTES.get(key),"proposed_v1_disposition":disp,
                       "proposed_global_codes":codes,"mapping_confidence":confidence,"review_notes":note})
    return result

def validate(payload: dict, reconciliation: list[dict]) -> list[str]:
    errors=[]; rows=payload.get("global_logistics_points",[])
    if payload.get("checksum") != checksum(payload): errors.append("checksum mismatch")
    codes=set(); identities=set()
    for item in rows:
        runtime=item.get("runtime_candidate",{}); review=item.get("review",{})
        code=runtime.get("immutable_code")
        identity=(runtime.get("country_code"),runtime.get("point_type_code"),runtime.get("facility_identity_key"))
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{2,63}",code or ""): errors.append(f"invalid code {code}")
        if code in codes: errors.append(f"duplicate code {code}")
        if identity in identities: errors.append(f"duplicate facility identity {identity}")
        codes.add(code); identities.add(identity)
        if runtime.get("point_type_code") not in TYPE_CODES: errors.append(f"invalid type {code}")
        if not re.fullmatch(r"[A-Z]{2}",runtime.get("country_code", "")): errors.append(f"invalid country {code}")
        if not runtime.get("fa_name") or not runtime.get("en_name"): errors.append(f"missing names {code}")
        if not set(runtime.get("supported_modes",[])) <= MODES or not runtime.get("supported_modes"): errors.append(f"invalid modes {code}")
        if not set(runtime.get("corridor_tags",[])) <= TAGS: errors.append(f"invalid corridors {code}")
        if review.get("classification") not in CLASSES or review.get("package_review_status") not in PACKAGE_STATES: errors.append(f"invalid review metadata {code}")
        alias_norms=[norm(x.get("value", "")) for x in runtime.get("aliases",[])]
        if len(alias_norms)!=len(set(alias_norms)) or "" in alias_norms: errors.append(f"duplicate/empty alias {code}")
        tags=runtime.get("corridor_tags",[])
        if len(tags)!=len(set(tags)): errors.append(f"duplicate corridor {code}")
        if review.get("package_review_status")=="READY_FOR_OWNER_APPROVAL" and not any(x.get("source_type")=="EXTERNAL-VERIFIED" for x in review.get("sources",[])): errors.append(f"ready row lacks provenance {code}")
        is_border=runtime.get("point_type_code")=="BORDER_CROSSING"
        if (is_border and not runtime.get("border_pair_key")) or (is_border and runtime.get("border_side") not in {"ENTRY","EXIT","BIDIRECTIONAL"}) or (not is_border and runtime.get("border_side") != "NOT_APPLICABLE"): errors.append(f"ambiguous border {code}")
        if (runtime.get("latitude") is None)!=(runtime.get("longitude") is None): errors.append(f"incomplete coordinates {code}")
        for ext in runtime.get("external_codes",[]):
            if set(ext)!={"scheme","value","source_reference"} or not all(ext.values()): errors.append(f"malformed external code {code}")
    if len(reconciliation)!=64 or {x["legacy_internal_key"] for x in reconciliation}!={x[0] for x in ROWS}: errors.append("legacy reconciliation is not exactly the repository 64")
    return errors

def report_text(payload: dict, reconciliation: list[dict]) -> str:
    rows=payload["global_logistics_points"]
    core=[x for x in rows if x["review"]["tier"]=="CORE_V1"]
    optional=[x for x in rows if x["review"]["tier"]=="OPTIONAL_V1"]
    unresolved=[x for x in rows if x["review"]["package_review_status"]!="READY_FOR_OWNER_APPROVAL"]
    lines=["# China→Iran Global Logistics Point Catalog V1 — owner review", "",
           "> DATA REVIEW ONLY. No seed, API mutation, Production access, adoption or materialization is authorized.", "",
           f"Package: `backend/reference_data/{PACKAGE.name}`", f"SHA-256: `{payload['checksum']}`",
           f"Candidates: {len(rows)} ({len(core)} CORE, {len(optional)} OPTIONAL, {len(unresolved)} unresolved)",
           "Canonicalization: UTF-8 JSON, recursively sorted object keys, compact separators, excluding the top-level `checksum` field.", "",
           "## Initial owner-approved baseline", "",
           "**INITIAL APPROVED BASELINE: 9**", "",
           "**DEFERRED CANDIDATES: 30** — 20 `NEEDS_OWNER_DECISION`; 10 `NEEDS_EXTERNAL_VERIFICATION`.", "",
           "The nine-point baseline is the official initial governed V1 baseline. It is deliberately minimal and does not approve the full 39-row package. The remaining candidates are `DEFERRED_FROM_INITIAL_BASELINE` at the decision layer only; they are not permanently rejected, and their package review states and proposed runtime states remain unchanged.", "",
           f"- Approved artifact: `backend/reference_data/{APPROVED_BASELINE.name}`",
           "- Approved checksum: `sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c`",
           f"- Owner decision: `docs/operational/data/{OWNER_DECISION.name}`", "",
           "Production seed authorized: **NO**", "",
           "| Immutable code | English name | Country | Type | Modes |", "|---|---|---|---|---|",
           "| GLP-CN-ALASHANKOU | Alashankou | CN | BORDER_CROSSING | ROAD, RAIL |",
           "| GLP-CN-NINGBO-ZHOUSHAN | Ningbo-Zhoushan | CN | PORT | SEA |",
           "| GLP-KZ-ALTYNKOL | Altynkol | KZ | RAIL_TERMINAL | RAIL |",
           "| GLP-KZ-DOSTYK | Dostyk | KZ | BORDER_CROSSING | ROAD, RAIL |",
           "| GLP-KG-IRKESHTAM | Irkeshtam Border Crossing — Kyrgyzstan Side | KG | BORDER_CROSSING | ROAD |",
           "| GLP-TM-FARAP | Farap | TM | BORDER_CROSSING | ROAD, RAIL |",
           "| GLP-TM-SERAKHS | Serakhs | TM | BORDER_CROSSING | ROAD, RAIL |",
           "| GLP-IR-SARAKHS | Sarakhs | IR | BORDER_CROSSING | ROAD, RAIL |",
           "| GLP-IR-INCHEH-BORUN | Incheh Borun | IR | BORDER_CROSSING | ROAD, RAIL |", "",
           "## Identity and review rules", "",
           "Codes use `GLP-{ISO2}-{STABLE-SLUG}`. They are governed identifiers, never numeric IDs or blindly copied UN/LOCODEs. Country/type codes are future importer lookup keys; the importer must resolve active runtime rows to opaque public IDs. Public IDs are generated by the service during apply.", "",
           "All proposed runtime states are DRAFT/UNVERIFIED. `READY_FOR_OWNER_APPROVAL` means data-package approval readiness, not runtime verification or activation. Coordinates and timezones are intentionally absent because row-specific authoritative evidence was not established.", "",
           "## CORE V1", "", "| Code | English / Persian | Country | Type | Modes | Corridors | Review | Open question |", "|---|---|---|---|---|---|---|---|"]
    for x in core:
        r=x["runtime_candidate"]; v=x["review"]
        lines.append(f"| {r['immutable_code']} | {r['en_name']} / {r['fa_name']} | {r['country_code']} | {r['point_type_code']} | {', '.join(r['supported_modes'])} | {', '.join(r['corridor_tags'])} | {v['package_review_status']} | {' '.join(v['open_questions']) or 'Approve bounded identity and labels.'} |")
    lines += ["", "## OPTIONAL V1", "", "| Code | English | Country | Type | Review |", "|---|---|---|---|---|"]
    for x in optional:
        r=x["runtime_candidate"]; v=x["review"]
        lines.append(f"| {r['immutable_code']} | {r['en_name']} | {r['country_code']} | {r['point_type_code']} | {v['package_review_status']} |")
    counts={k:sum(1 for x in reconciliation if x["proposed_v1_disposition"]==k) for k in CLASSES}
    lines += ["", "## Legacy 64 reconciliation", "", f"Exactly 64 repository rows inventoried. Dispositions: `{json.dumps(counts, sort_keys=True)}`.",
              f"Machine-readable table: `docs/operational/data/{RECONCILIATION.name}`. No legacy mapping rows are created.", "",
              "## External-source policy", "", "Repository-derived candidate material is distinguished from external-verified evidence in every row. Sources are authoritative or intergovernmental: UNECE UN/LOCODE, CAREC, national railway/government sources, and official port operators. External codes are included only for CNSHA, CNAKL and IRBAZ where the cited UNECE material supports them; all others remain empty.", "",
              "## Owner decisions", "", "1. Choose complex versus terminal granularity for Shanghai, Shenzhen/Yantian, Guangzhou/Nansha, Tianjin/Xingang and Anzali/Caspian.", "2. Confirm exact facilities behind city/hub legacy labels before approval (China rail origins, Osh, Tashkent, Bukhara, Turkmenabat, Mary, Tejen, Mashhad, Almaty and Shymkent).", "3. Confirm whether Aprin should replace broad Tehran in CORE V1 after authoritative facility evidence; no Aprin candidate is emitted yet.", "4. Decide whether Pakistan/Afghanistan alternate corridors remain excluded from V1.", "5. Commission row-specific official verification for Iranian port candidates and any missing terminal codes.", "",
              "## Future controlled apply", "", "Recommend a governed server-side package importer using Platform Admin authority, explicit checksum and approval reference, plan/apply separation, service-layer create calls, conflict refusal, and persisted run evidence. Initial apply must create only owner-approved rows as DRAFT/UNVERIFIED. Separate review/verify/activate actions remain mandatory. Rollback before adoption may deprecate or remove never-used drafts under an approved procedure; after adoption, use deprecation and retain history.", "",
              "Post-apply checks: exact created/unchanged/conflict counts; list by catalog codes; verify DRAFT/UNVERIFIED state; confirm zero adoptions/materializations; re-run duplicate, provenance and activation-gate diagnostics. Platform Admin identity, owner approval reference, expected checksum and rollback approver are required inputs.", ""]
    return "\n".join(lines)

def generate() -> None:
    payload=unsigned_package(); payload["checksum"]=checksum(payload)
    reconciliation=reconciliation_rows(); errors=validate(payload,reconciliation)
    if errors: raise SystemExit("\n".join(errors))
    PACKAGE.parent.mkdir(parents=True,exist_ok=True); RECONCILIATION.parent.mkdir(parents=True,exist_ok=True)
    PACKAGE.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    RECONCILIATION.write_text(json.dumps({"schema_version":"1","catalog_version":payload["catalog_version"],"rows":reconciliation},ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    REPORT.write_text(report_text(payload,reconciliation),encoding="utf-8")
    print(f"catalog-validator=PASS checksum={payload['checksum']} rows={len(payload['global_logistics_points'])} legacy={len(reconciliation)}")

def check() -> None:
    payload=json.loads(PACKAGE.read_text(encoding="utf-8")); rec=json.loads(RECONCILIATION.read_text(encoding="utf-8"))["rows"]
    errors=validate(payload,rec)
    expected=unsigned_package(); expected["checksum"]=checksum(expected)
    if payload != expected: errors.append("package differs from deterministic generator")
    if REPORT.read_text(encoding="utf-8") != report_text(payload,rec): errors.append("owner report differs from deterministic generator")
    if errors: raise SystemExit("\n".join(errors))
    print(f"catalog-validator=PASS checksum={payload['checksum']} rows={len(payload['global_logistics_points'])} legacy={len(rec)}")

def generate_approved_baseline() -> None:
    parent = json.loads(PACKAGE.read_text(encoding="utf-8"))
    baseline = unsigned_approved_baseline(parent)
    baseline["checksum"] = checksum(baseline)
    errors = validate_approved_baseline(parent, baseline)
    if errors: raise SystemExit("\n".join(errors))
    APPROVED_BASELINE.write_text(json.dumps(baseline, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"approved-baseline-validator=PASS checksum={baseline['checksum']} rows={len(baseline['approved_global_logistics_points'])}")

def check_approved_baseline() -> None:
    parent = json.loads(PACKAGE.read_text(encoding="utf-8"))
    baseline = json.loads(APPROVED_BASELINE.read_text(encoding="utf-8"))
    errors = validate_approved_baseline(parent, baseline)
    expected = unsigned_approved_baseline(parent)
    expected["checksum"] = checksum(expected)
    if baseline != expected: errors.append("approved baseline differs from deterministic generator")
    if errors: raise SystemExit("\n".join(errors))
    print(f"approved-baseline-validator=PASS checksum={baseline['checksum']} rows={len(baseline['approved_global_logistics_points'])}")

if __name__ == "__main__":
    if "--generate" in sys.argv:
        generate()
    elif "--generate-approved-baseline" in sys.argv:
        generate_approved_baseline()
    elif "--approved-baseline" in sys.argv:
        check_approved_baseline()
    else:
        check()
