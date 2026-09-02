"""Test the actual transferred D2 package, not only its source templates."""
import hashlib, json, shutil, subprocess, sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[2]
BUILDER=ROOT/"scripts/deploy/build_d2_validation_package.py"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def pwsh(): return shutil.which("powershell") or shutil.which("pwsh")

def simulation(root):
    previous=root/"production/release-adcc5da-adr043"; (previous/"dist").mkdir(parents=True); (previous/"dist/index.html").write_text("old")
    runtime=root/"runtime"; runtime.mkdir(); (runtime/"production.env").write_text("DATABASE_URL=postgresql://redacted\nJWT_SECRET_KEY=redacted\nCORS_ALLOW_ALL_ORIGINS=false\nCORS_ORIGINS=https://server.logisticmarket.ir\nCORS_ORIGIN=https://server.logisticmarket.ir\n"); (runtime/"phase1b_production_cutover_runtime.py").write_text("# fixture")
    (root/"task.txt").write_text(str(previous)); (root/"iis.txt").write_text(str(previous/"dist")); (root/"host.txt").write_text("SRV8756807400"); (root/"admin.txt").write_text("yes"); (root/"database.txt").write_text("forwarder_prod_20260728_161711|20260907_direct_shipment_responsibility")
    staging=root/"staging"; staging.mkdir(); rc=ROOT.parent/"release-candidates/S7-RC-f11f2ab"; shutil.copy2(rc/"Forwarder-S7-RC-f11f2ab.zip",staging); shutil.copy2(rc/"Forwarder-S7-RC-f11f2ab.zip.manifest.json",staging)

@pytest.mark.skipif(not pwsh(),reason="PowerShell unavailable")
def test_packaged_validate_only_workflow_and_integrity(tmp_path):
    package=tmp_path/"D2-VALIDATION-S7-RC-f11f2ab"
    subprocess.run([sys.executable,str(BUILDER),str(package),"test-commit"],check=True,capture_output=True,text=True)
    manifest=json.loads((package/"D2-package-manifest.json").read_text())
    assert manifest["package_id"]=="D2-VALIDATION-S7-RC-f11f2ab"
    for record in manifest["files"]:
        path=package/record["name"]; assert path.stat().st_size==record["bytes"]; assert sha(path)==record["sha256"]
    assert sha(package/"Forwarder-S7-RC-f11f2ab.zip")=="a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d"
    assert sha(package/"Forwarder-S7-RC-f11f2ab.zip.manifest.json")=="4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f"
    sim=tmp_path/"simulation"; simulation(sim)
    result=subprocess.run([pwsh(),"-NoProfile","-ExecutionPolicy","Bypass","-File",str(package/"validate_forwarder_s7_rc_f11f2ab.ps1"),"-SimulationRoot",str(sim)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert "VALIDATION_RESULT=GO" in result.stdout and "DEPLOYMENT_PERFORMED=NO" in result.stdout
    assert not (sim/"production/release-f11f2ab-s7").exists()
    assert "redacted" not in result.stdout+result.stderr

@pytest.mark.skipif(not pwsh(),reason="PowerShell unavailable")
def test_packaged_wrapper_fails_closed_on_tampered_artifact(tmp_path):
    package=tmp_path/"D2-VALIDATION-S7-RC-f11f2ab"; subprocess.run([sys.executable,str(BUILDER),str(package),"test-commit"],check=True,capture_output=True,text=True)
    with (package/"Forwarder-S7-RC-f11f2ab.zip").open("ab") as handle: handle.write(b"tamper")
    result=subprocess.run([pwsh(),"-NoProfile","-File",str(package/"validate_forwarder_s7_rc_f11f2ab.ps1")],capture_output=True,text=True)
    assert result.returncode!=0 and "VALIDATION_RESULT=NO_GO" in result.stdout
