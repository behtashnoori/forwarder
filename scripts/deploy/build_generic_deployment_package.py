"""Package an immutable RC with descriptor-driven, preflight-only deployment logic."""
from __future__ import annotations
import json, shutil, sys, tempfile, zipfile
from pathlib import Path
from release_descriptor import load, sha

ROOT=Path(__file__).resolve().parents[2]
def build(descriptor_path: Path, rc: Path, runtime: Path, output: Path):
    descriptor=load(descriptor_path)
    if sha(rc)!=descriptor["rc_zip_sha256"] or sha(runtime)!=descriptor["runtime_sha256"]: raise RuntimeError("immutable input hash mismatch")
    output.mkdir(parents=True,exist_ok=False); artifact=output/(descriptor["deployment_package_id"]+".zip")
    with tempfile.TemporaryDirectory() as raw:
        stage=Path(raw); files=[(descriptor_path,"release-descriptor.json"),(rc,rc.name),(runtime,runtime.name),(runtime.with_suffix(runtime.suffix+".manifest.json"),runtime.name+".manifest.json")]
        for name in ("preflight_generic.ps1","deploy_generic.ps1","validate_generic.ps1","README-GENERIC-OPERATOR.md"):
            files.append((ROOT/"scripts"/"deploy"/name,name))
        records=[]
        for source,name in files:
            if not source.is_file(): raise RuntimeError(f"required package file missing: {source}")
            target=stage/name; shutil.copy2(source,target); records.append({"path":name,"sha256":sha(target),"bytes":target.stat().st_size})
        (stage/"deployment-manifest.json").write_text(json.dumps({"schema":"forwarder-generic-deployment-v1","descriptor":descriptor,"files":records},indent=2,sort_keys=True)+"\n",encoding="utf-8")
        with zipfile.ZipFile(artifact,"x",zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for path in sorted(stage.iterdir()): archive.write(path,path.name)
    side=artifact.with_suffix(artifact.suffix+".manifest.json"); side.write_text(json.dumps({"artifact":artifact.name,"sha256":sha(artifact),"bytes":artifact.stat().st_size},indent=2)+"\n",encoding="utf-8")
    return artifact,side
if __name__=="__main__":
    result=build(*map(Path,sys.argv[1:5])); print(json.dumps([str(x) for x in result]))
