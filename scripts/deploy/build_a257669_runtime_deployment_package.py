"""Build immutable D2 r4: frozen application plus governed runtime contract."""
from __future__ import annotations
import hashlib, json, shutil, sys, tempfile, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ID = "D2-VALIDATION-S7-RC-a257669-rg1-frozen-r5"
RUNTIME_ID = "Forwarder-Windows-Runtime-S7-RC-a257669-r4"
APP = ROOT / "release-candidates" / "S7-RC-a257669-rg1-frozen" / "Forwarder-S7-RC-a257669-rg1-frozen-a257669.zip"
RUNTIME = ROOT / "release-candidates" / (RUNTIME_ID + ".zip")
IDENTITY = {"expected_application_release_id":"S7-RC-a257669-rg1-frozen","expected_application_source_sha":"a2576690364fcaf58ca7ddc6c57143c3084bbb00","expected_application_zip_sha256":"aca7a147cad97edf0e3f03d763c63471c283f62021a23a4e6a47b5e59aa88534","expected_application_zip_size":1323912,"target_alembic_head":"20260908_governed_international_geography","runtime_id":RUNTIME_ID,"lpaf_version":"2.2","rollback_strategy":"KEEP_UPGRADED_DB_AND_ROLLBACK_APP"}
FILES = ["README-OPERATOR-r4.md", "preflight_a257669.ps1", "deploy_a257669_r4.ps1", "validate_a257669_r4.ps1"]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(output: Path):
    output.mkdir(parents=True, exist_ok=False)
    artifact = output / (PACKAGE_ID + ".zip"); side = output / (artifact.name + ".manifest.json")
    if sha(APP) != IDENTITY["expected_application_zip_sha256"]: raise RuntimeError("frozen application identity mismatch")
    runtime_side = RUNTIME.with_suffix(RUNTIME.suffix + ".manifest.json")
    runtime_manifest = json.loads(runtime_side.read_text(encoding="utf-8"))
    if runtime_manifest["runtime_id"] != RUNTIME_ID or sha(RUNTIME) != runtime_manifest["artifact_sha256"]: raise RuntimeError("governed runtime identity mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp); records=[]
        for source, name in [(APP, APP.name), (APP.with_suffix(APP.suffix+".manifest.json"), APP.name+".manifest.json"), (RUNTIME,RUNTIME.name), (runtime_side,runtime_side.name)]:
            dst=stage/name; shutil.copy2(source,dst); records.append({"path":name,"sha256":sha(dst),"bytes":dst.stat().st_size})
        for name in FILES:
            dst=stage/name; shutil.copy2(ROOT/"scripts"/"deploy"/name,dst); records.append({"path":name,"sha256":sha(dst),"bytes":dst.stat().st_size})
        manifest={"schema":"forwarder-d2-runtime-deployment-package-v1","deployment_package_id":PACKAGE_ID,**IDENTITY,"runtime_artifact": {"filename":RUNTIME.name,"sha256":sha(RUNTIME),"size_bytes":RUNTIME.stat().st_size,"manifest_sha256":sha(runtime_side)},"files":records}
        (stage/"deployment-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        with zipfile.ZipFile(artifact,"x",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for path in sorted(stage.iterdir()): z.write(path,path.name)
    side.write_text(json.dumps({"artifact_filename":artifact.name,"artifact_size":artifact.stat().st_size,"artifact_sha256":sha(artifact),"deployment_package_id":PACKAGE_ID},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"artifact":str(artifact),"sha256":sha(artifact),"manifest":str(side),"manifest_sha256":sha(side)}))
if __name__ == "__main__":
    build(Path(sys.argv[1]))
