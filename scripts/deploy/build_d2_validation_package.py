"""Build the governed D2 ValidateOnly package around the frozen S7 application RC."""
from __future__ import annotations

import hashlib, json, shutil, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_ID="D2-VALIDATION-S7-RC-f11f2ab-r3-final"
SOURCE_COMMIT="f11f2abfbff396f66f261f11c7f4bdb80b2d2007"
ARTIFACT_HASH="a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d"
SIDECAR_HASH="4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f"
ROOT=Path(__file__).resolve().parents[2]
RC=ROOT.parent/"release-candidates"/"S7-RC-f11f2ab"

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def main(output: Path, package_id: str = PACKAGE_ID) -> int:
    if output.exists(): raise RuntimeError("refusing to overwrite D2 package output")
    artifact=RC/"Forwarder-S7-RC-f11f2ab.zip"; sidecar=RC/(artifact.name+".manifest.json")
    if sha(artifact)!=ARTIFACT_HASH or sha(sidecar)!=SIDECAR_HASH: raise RuntimeError("frozen RC identity mismatch")
    output.mkdir(parents=True)
    for source,name in ((artifact,artifact.name),(sidecar,sidecar.name),(ROOT/"scripts/deploy/deploy_s7_rc_f11f2ab.ps1","deploy_s7_rc_f11f2ab.ps1"),(ROOT/"scripts/deploy/validate_forwarder_s7_rc_f11f2ab.ps1","validate_forwarder_s7_rc_f11f2ab.ps1")):
        shutil.copy2(source,output/name)
    wrapper=output/"validate_forwarder_s7_rc_f11f2ab.ps1"
    wrapper.write_text(wrapper.read_text(encoding="utf-8").replace(PACKAGE_ID+"'",package_id+"'"),encoding="utf-8")
    (output/"expected-production-baseline.json").write_text(json.dumps({"host":"SRV8756807400","current_release":"C:\\1-webapp\\forwarder-production\\release-adcc5da-adr043","runtime_root":"C:\\1-webapp\\forwarder-runtime","runtime_wrapper":"phase1b_production_cutover_runtime.py","task":"Forwarder Backend Production","listener":"127.0.0.1:5101","iis_site":"forwarder","iis_path":"C:\\1-webapp\\forwarder-production\\release-adcc5da-adr043\\dist","canonical_host":"samand.forwarderet.ir","canonical_origin":"https://samand.forwarderet.ir","legacy_origin":"https://server.logisticmarket.ir","database":"forwarder_prod_20260728_161711","alembic_head":"20260907_direct_shipment_responsibility","current_cors":"LEGACY_TRANSITION_EXPECTED"},indent=2)+"\n",encoding="utf-8")
    (output/"README-OPERATOR.txt").write_text("STEP 1: Copy this complete folder to the approved staging directory.\nSTEP 2: Open PowerShell as Administrator.\nSTEP 3: Run: PowerShell.exe -ExecutionPolicy Bypass -File .\\validate_forwarder_s7_rc_f11f2ab.ps1\nSTEP 4: Copy back the generated D2-validation-report JSON.\nSTEP 5: STOP. DO NOT DEPLOY. DO NOT EDIT ANY PRODUCTION FILE. If VALIDATION_RESULT=NO_GO, return the report to Development; do not repair Production.\n",encoding="utf-8")
    files=[]
    for path in sorted(output.iterdir()):
        if path.is_file(): files.append({"name":path.name,"bytes":path.stat().st_size,"sha256":sha(path)})
    (output/"SHA256SUMS.txt").write_text("\n".join(f"{x['sha256']}  {x['name']}" for x in files)+"\n",encoding="utf-8")
    checksum=output/"SHA256SUMS.txt"
    files.append({"name":checksum.name,"bytes":checksum.stat().st_size,"sha256":sha(checksum)})
    manifest={"schema":"forwarder-d2-validation-package-v1","package_id":package_id,"created_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"d1_tooling_commit":sys.argv[2] if len(sys.argv)>2 else "unknown","application_candidate":"S7-RC-f11f2ab","application_source_commit":SOURCE_COMMIT,"files":files}
    (output/"D2-package-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    outer=output.with_suffix(".zip")
    with zipfile.ZipFile(outer,"x",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(output.iterdir()): z.write(p,p.name)
    print(json.dumps({"package":str(output),"outer_artifact":str(outer),"outer_size":outer.stat().st_size,"outer_sha256":sha(outer)},sort_keys=True))
    return 0
if __name__=="__main__":
    try: raise SystemExit(main(Path(sys.argv[1]),sys.argv[3] if len(sys.argv)>3 else PACKAGE_ID))
    except (IndexError,RuntimeError) as e: print(str(e),file=sys.stderr); raise SystemExit(1)
