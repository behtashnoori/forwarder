import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("descriptor",ROOT/"scripts/deploy/release_descriptor.py")
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def valid(): return {"release_id":"S8-RC-a9ed9ae-rg1-frozen","application_source_sha":"a"*40+"9"*24,"rc_zip_sha256":"b"*64,"alembic_head":"20260908_governed_international_geography","runtime_id":"runtime","runtime_sha256":"c"*64,"deployment_package_id":"D2-S8","previous_release_id":"S7-RC-a257669-rg1-frozen","previous_application_source_sha":"d"*64,"qualification":{}}
def test_descriptor_rejects_live_production_facts(tmp_path):
    data=valid();data["database_name"]="forbidden";path=tmp_path/"d.json";path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="forbidden"):module.load(path)
def test_generic_scripts_have_no_historical_candidate_or_broad_kill():
    source="\n".join(p.read_text(encoding="utf-8") for p in (ROOT/"scripts/deploy").glob("*_generic.*"))
    assert "a257669" not in source and "Stop-Process -Name" not in source and "taskkill /IM" not in source
