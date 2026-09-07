"""Build the immutable Personal Analytics staging operator archive."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

RC_ID="personal-analytics-rc-e5a54ac"; COMMIT="e5a54ac7808763e72da0242032b5019ac442746e"; HEAD="20260915_project_access_foundation"
ROOT=Path(__file__).resolve().parents[1]; OPERATOR=ROOT/"release-engineering"/RC_ID
EXCLUDE=(".git/","node_modules/","release-candidates/","tests/",".env", "dist/")
FIXTURE_COMPANION=("backend/personal_analytics_uat.py", "backend/operational_cli.py")

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()

def run(*args): return subprocess.check_output(args,cwd=ROOT,text=True).strip()

def build(output: Path, runtime: Path|None=None):
    if run("git","cat-file","-t",COMMIT) != "commit": raise RuntimeError("the exact RC commit is unavailable")
    if run("git","status","--porcelain","--untracked-files=no"): raise RuntimeError("tracked worktree must be clean")
    if run("python","-c","from alembic.config import Config; from alembic.script import ScriptDirectory; print(','.join(ScriptDirectory.from_config(Config('backend/migrations/alembic.ini')).get_heads()))") != HEAD: raise RuntimeError("unexpected Alembic head")
    if not (ROOT/"dist"/"index.html").is_file(): raise RuntimeError("build frontend first; dist/index.html is required")
    output.mkdir(parents=True,exist_ok=True); artifact=output/f"Forwarder-{RC_ID}-{COMMIT[:7]}.zip"
    if artifact.exists(): raise RuntimeError("refusing to overwrite an immutable artifact")
    names=[name for name in run("git","ls-tree","-r","--name-only",COMMIT).splitlines() if not any(name==item or name.startswith(item) for item in EXCLUDE)]
    with zipfile.ZipFile(artifact,"x",zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name in names: archive.write(ROOT/name,name)
        for name in FIXTURE_COMPANION: archive.write(ROOT/name,name)
        for path in sorted((ROOT/"dist").rglob("*")):
            if path.is_file(): archive.write(path,Path("dist")/path.relative_to(ROOT/"dist"))
    scripts={path.name:sha(path) for path in OPERATOR.glob("*") if path.is_file()}
    manifest={"schema":"forwarder-personal-analytics-staging-v1","rc_id":RC_ID,"source_commit":COMMIT,
      "commit_subject":run("git","log","-1","--format=%s",COMMIT),"alembic_head":HEAD,
      "built_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"frontend_artifact_sha256":sha(ROOT/"dist"/"index.html"),
      "backend_application_sha256":sha(artifact),"runtime_package_sha256":sha(runtime) if runtime else None,
      "fixture_companion_sha256":{name:sha(ROOT/name) for name in FIXTURE_COMPANION}, "operator_script_sha256":scripts,
      "compatibility":{"backend_port":5201,"iis_port":8443,"app_env":"staging|uat","database_prefixes":["forwarder_personal_analytics_uat","forwarder_staging_"]}}
    sidecar=artifact.with_suffix(".zip.manifest.json"); sidecar.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return artifact,sidecar

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--output",required=True); parser.add_argument("--runtime-package")
    args=parser.parse_args(); print(json.dumps([str(item) for item in build(Path(args.output),Path(args.runtime_package) if args.runtime_package else None)]))
