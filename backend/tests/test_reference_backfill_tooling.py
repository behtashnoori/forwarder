import csv
import hashlib
import json

import pytest
from sqlalchemy import text

from backend import create_app
from backend.extensions import db
from backend.models import City, Country, County, IranPort, Province
from backend.services.reference_backfill_service import (
    BASE_HEADERS, apply_package, diff_package, export_inventory_package,
    fingerprint, mutable_target_allowed, normalize, validate_package,
)


@pytest.fixture()
def app():
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:"})
    with app.app_context():
        db.session.execute(text("create table alembic_version(version_num varchar(255) not null)"))
        db.session.execute(text("insert into alembic_version values ('20260720_expand_reference_data_identity')"))
        # Country.code is constrained to three characters, so TST is the
        # unmistakably synthetic parent code used by TEST-* identities.
        country=Country(code="TST",name_en="TEST Synthetic",name_fa="TEST Synthetic")
        db.session.add(country); db.session.flush()
        province=Province(name_fa="TEST Province"); db.session.add(province); db.session.flush()
        county=County(name_fa="TEST County",province_id=province.id); db.session.add(county); db.session.flush()
        city=City(name_fa="TEST City",province_id=province.id,county_id=county.id); db.session.add(city); db.session.flush()
        db.session.add(IranPort(name_fa="TEST Port",name_en="TEST Port",province_id=province.id)); db.session.commit()
        yield app
        db.session.remove(); db.drop_all()


def _approve(package):
    proposals={"provinces":("TEST-P","TST"),"counties":("TEST-C",None),"cities":("TEST-CITY",None),"ports":("TEST-PORT","TST")}
    for domain,(code,country) in proposals.items():
        path=package/"mappings"/f"{domain}.csv"
        with path.open(encoding="utf-8",newline="") as handle: rows=list(csv.DictReader(handle))
        rows[0]["proposed_code"]=code
        if country: rows[0]["proposed_country_code"]=country
        rows[0]["proposed_source_organization"]="TEST-OWNER"; rows[0]["proposed_source_reference"]="TEST-REF"
        rows[0]["proposed_source_version"]="TEST-1"; rows[0]["proposed_dataset_id"]="TEST-DATASET"
        with path.open("w",encoding="utf-8",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=BASE_HEADERS); writer.writeheader(); writer.writerows(rows)
    manifest=json.loads((package/"manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        file=package/entry["path"]; entry["sha256"]=hashlib.sha256(file.read_bytes()).hexdigest()
    raw=json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True).encode()+b"\n"; (package/"manifest.json").write_bytes(raw)
    approval=json.loads((package/"approval.DRAFT.json").read_text(encoding="utf-8")); approval.update({
        "manifest_sha256":hashlib.sha256(raw).hexdigest(),"approval_status":"approved_for_candidate_backfill",
        "approved_by":"TEST-OWNER","approved_domains":[e["domain"] for e in manifest["files"] if e["row_count"]],
        "approved_operations":list({e["apply_semantics"] for e in manifest["files"] if e["row_count"]}),"candidate_apply_authorized":True})
    (package/"approval.DRAFT.json").write_text(json.dumps(approval,indent=2,sort_keys=True)+"\n",encoding="utf-8")


def test_fingerprint_and_normalization_are_deterministic(app):
    province=Province.query.one(); assert fingerprint("provinces",province)==fingerprint("provinces",province)
    assert normalize("  ك ي  ")=="ک ی"


def test_export_is_deterministic_in_row_order_and_blank_proposals(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    rows=list(csv.DictReader((tmp_path/"mappings/provinces.csv").open(encoding="utf-8")))
    assert [int(row["record_id"]) for row in rows]==sorted(int(row["record_id"]) for row in rows)
    assert all(not row["proposed_code"] for row in rows)
    assert validate_package(tmp_path).status=="AWAITING_OWNER_INPUT"


def test_checksum_and_path_traversal_rejected(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    manifest=json.loads((tmp_path/"manifest.json").read_text()); manifest["files"][0]["path"]="../escape.csv"
    (tmp_path/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    assert validate_package(tmp_path).status=="REJECTED"


def test_drift_detection(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    Province.query.one().name_fa="changed"; db.session.commit()
    result=validate_package(tmp_path,against_database=True)
    assert any(issue.code=="RECORD_DRIFT" for issue in result.issues)


def test_forbidden_targets_and_dry_run_zero_writes(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    assert apply_package(tmp_path,database_name="forwarder_candidate_uat_20260717",apply=True)["code"]=="FORBIDDEN_TARGET"
    before=Province.query.one().code
    assert apply_package(tmp_path,database_name="forwarder_backfill_test_unit",apply=False)["writes"]==0
    assert Province.query.one().code==before


def test_approved_apply_and_repeat_are_idempotent(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit"); _approve(tmp_path)
    assert validate_package(tmp_path,against_database=True).status=="PASS"
    first=apply_package(tmp_path,database_name="forwarder_backfill_test_unit",apply=True)
    assert first["status"]=="PASS" and first["writes"]>0
    assert (Province.query.one().code,County.query.one().code,City.query.one().code,IranPort.query.one().code)==("TEST-P","TEST-C","TEST-CITY","TEST-PORT")
    assert diff_package(tmp_path)["planned_writes"]==0
    second=apply_package(tmp_path,database_name="forwarder_backfill_test_unit",apply=True)
    assert second=={"status":"PASS","mode":"apply","writes":0}


def test_transaction_rolls_back_duplicate_code(app,tmp_path):
    second=Province(name_fa="TEST Province 2"); db.session.add(second); db.session.commit()
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit"); _approve(tmp_path)
    path=tmp_path/"mappings/provinces.csv"; rows=list(csv.DictReader(path.open(encoding="utf-8")))
    rows[1]["proposed_code"]="TEST-P"; rows[1]["proposed_country_code"]="TST"
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=BASE_HEADERS); writer.writeheader(); writer.writerows(rows)
    manifest=json.loads((tmp_path/"manifest.json").read_text()); next(e for e in manifest["files"] if e["domain"]=="provinces")["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    raw=json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True).encode()+b"\n"; (tmp_path/"manifest.json").write_bytes(raw)
    approval=json.loads((tmp_path/"approval.DRAFT.json").read_text()); approval["manifest_sha256"]=hashlib.sha256(raw).hexdigest(); (tmp_path/"approval.DRAFT.json").write_text(json.dumps(approval))
    result=apply_package(tmp_path,database_name="forwarder_backfill_test_unit",apply=True)
    assert result["status"]=="REJECTED" and Province.query.filter(Province.code.isnot(None)).count()==0


@pytest.mark.parametrize("name", [
    "forwarder_db", "forwarder_candidate_uat_20260717", "postgres", "template0", "template1",
    "forwarder_production", "forwarder_backfill_test_prod", "unknown", "forwarder_backfill_test_x;drop",
    "postgresql:" + "//TEST-CREDENTIAL@TEST-HOST/TEST-DB",
])
def test_mutable_target_guard_is_fail_closed(name):
    assert mutable_target_allowed(name) is False


def test_mutable_target_guard_accepts_only_disposable_prefixes():
    assert mutable_target_allowed("forwarder_backfill_test_20260721")
    assert mutable_target_allowed("forwarder_backfill_candidate_test_case1")


def test_row_count_and_missing_domain_are_rejected(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    manifest=json.loads((tmp_path/"manifest.json").read_text(encoding="utf-8"))
    manifest["files"][0]["row_count"] += 1
    manifest["files"].pop()
    (tmp_path/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    result=validate_package(tmp_path)
    assert result.status=="REJECTED"
    assert {issue.code for issue in result.issues} >= {"ROW_COUNT_MISMATCH","PARTIAL_PACKAGE"}


def test_invalid_utf8_is_rejected(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    path=tmp_path/"mappings/provinces.csv"; path.write_bytes(b"\xff\xfe")
    result=validate_package(tmp_path)
    assert result.status=="REJECTED"
    assert any(issue.code=="INVALID_UTF8" for issue in result.issues)


def test_production_approval_is_never_apply_authorized(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit"); _approve(tmp_path)
    approval_path=tmp_path/"approval.DRAFT.json"; approval=json.loads(approval_path.read_text())
    approval["approval_status"]="approved_for_production_backfill"
    approval["candidate_apply_authorized"]=False; approval["production_apply_authorized"]=True
    approval_path.write_text(json.dumps(approval),encoding="utf-8")
    result=apply_package(tmp_path,database_name="forwarder_backfill_test_unit",apply=True)
    assert result=={"status":"REJECTED","code":"APPLY_NOT_AUTHORIZED","writes":0}


def test_invalid_effective_range_and_missing_provenance_are_rejected(app,tmp_path):
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    path=tmp_path/"mappings/provinces.csv"; rows=list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["proposed_code"]="TEST-P"; rows[0]["proposed_effective_from"]="2026-02-02"; rows[0]["proposed_effective_to"]="2026-01-01"
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=BASE_HEADERS); writer.writeheader(); writer.writerows(rows)
    manifest=json.loads((tmp_path/"manifest.json").read_text()); next(e for e in manifest["files"] if e["domain"]=="provinces")["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    raw=json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True).encode()+b"\n"; (tmp_path/"manifest.json").write_bytes(raw)
    approval=json.loads((tmp_path/"approval.DRAFT.json").read_text()); approval["manifest_sha256"]=hashlib.sha256(raw).hexdigest(); (tmp_path/"approval.DRAFT.json").write_text(json.dumps(approval))
    codes={issue.code for issue in validate_package(tmp_path).issues}
    assert {"EFFECTIVE_RANGE_INVALID","PROVENANCE_MISSING"}.issubset(codes)


def test_csv_formula_values_are_export_safe_and_original_apostrophe_is_preserved(app,tmp_path):
    province=Province.query.one(); province.name_fa="=SUM(1,1)"; County.query.one().name_fa="'=literal"; db.session.commit()
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    exported=next(csv.DictReader((tmp_path/"mappings/provinces.csv").open(encoding="utf-8")))
    assert exported["current_name_fa"].startswith("'FORWARDER-CSV-SAFE:'=")
    result=validate_package(tmp_path)
    assert result.rows["provinces"][0]["current_name_fa"]=="=SUM(1,1)"
    assert result.rows["counties"][0]["current_name_fa"]=="'=literal"


def test_no_code_is_generated_from_name_or_locator(app,tmp_path):
    province=Province.query.one(); original_id=province.id; original_name=province.name_fa
    export_inventory_package(tmp_path,database_name="forwarder_backfill_test_unit")
    row=next(csv.DictReader((tmp_path/"mappings/provinces.csv").open(encoding="utf-8")))
    assert row["proposed_code"]=="" and row["record_id"]==str(original_id) and original_name not in row["proposed_code"]
