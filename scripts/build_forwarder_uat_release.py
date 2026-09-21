"""Build and verify the immutable Forwarder UAT package from a clean commit."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path


VERSION = "1.10.0"
PREVIOUS_VERSION = "1.9.5.1"
BASE_SHA = "a742628293359379cb476b782a2fe27e61a8db1f"
DATABASE_HEAD = "20260926_fixed_shipment_responsible_expert"
RELEASE_ID = f"Forwarder-UAT-v{VERSION}"
RELEASE_TAG = f"forwarder-uat-v{VERSION}"
RUNTIME_NAME = "Forwarder-Windows-Runtime-S7-RC-a257669-r4.zip"
RUNTIME_SHA256 = "f4a8f108aa89a78d7986f01fb8f6aa8af5e2d35e00617a8453eb1f15df945070"
HISTORICAL_SECURITY_REMEDIATION = {
    "policy": "exact-credential-migration-remediated-in-ancestry-v1",
    "legacy_revision": "20240926_add_password_to_expert_user",
    "legacy_file_sha256": "6ed41e455ed80e69922f201dbe2e8fd4e9db3e1c60f49bf64fb39a4451013554",
    "remediation_revision": "security_credential_remediation",
    "remediation_sha256": "72e19843e625054dac4f338ee7f54772bc2ebef332dabdab7417e50fab6635ee",
}


def run(args: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> str:
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True, capture_output=True).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def revision_graph(versions: Path) -> tuple[dict[str, tuple[str, ...]], list[str]]:
    graph: dict[str, tuple[str, ...]] = {}
    for path in versions.glob("*.py"):
        values: dict[str, object] = {}
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in {"revision", "down_revision"}:
                    values[target.id] = ast.literal_eval(node.value)
        revision = values.get("revision")
        parent = values.get("down_revision")
        if not isinstance(revision, str):
            continue
        parents = () if parent is None else ((parent,) if isinstance(parent, str) else tuple(parent))
        graph[revision] = tuple(str(item) for item in parents)
    referenced = {parent for parents in graph.values() for parent in parents}
    return graph, sorted(set(graph) - referenced)


def verify_runtime_tree(runtime: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("artifact") != RUNTIME_NAME
        or manifest.get("artifact_sha256") != RUNTIME_SHA256
        or manifest.get("runtime_id") != "Forwarder-Windows-Runtime-S7-RC-a257669-r4"
    ):
        raise RuntimeError("approved runtime manifest identity mismatch")
    expected = {
        item["path"]: (item["bytes"], item["sha256"])
        for item in manifest.get("files", [])
    }
    actual = {
        path.relative_to(runtime).as_posix(): (path.stat().st_size, sha256(path))
        for path in runtime.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        changed = sorted(
            name for name in set(actual) & set(expected) if actual[name] != expected[name]
        )
        raise RuntimeError(
            f"approved runtime tree mismatch; missing={missing}; "
            f"unexpected={unexpected}; changed={changed}"
        )


GATEWAY = r'''"""Same-origin static frontend and /api gateway for the owned UAT runtime."""
from __future__ import annotations
import argparse
import http.client
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

p=argparse.ArgumentParser();p.add_argument('--dist',type=Path,required=True);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,required=True);p.add_argument('--backend-port',type=int,required=True);a=p.parse_args()
root=a.dist.resolve(strict=True)

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def proxy(self):
        length=int(self.headers.get('Content-Length','0'));body=self.rfile.read(length) if length else None
        headers={k:v for k,v in self.headers.items() if k.lower() not in {'host','connection','content-length','accept-encoding'}}
        conn=http.client.HTTPConnection('127.0.0.1',a.backend_port,timeout=60)
        try:
            conn.request(self.command,self.path,body=body,headers=headers);response=conn.getresponse();payload=response.read()
            self.send_response(response.status)
            for key,value in response.getheaders():
                if key.lower() not in {'connection','transfer-encoding','content-length','content-encoding'}:self.send_header(key,value)
            self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
        finally:conn.close()
    def static(self):
        requested=urlsplit(self.path).path.lstrip('/');candidate=(root/requested).resolve()
        if root not in candidate.parents and candidate!=root:self.send_error(403);return
        if not candidate.is_file():candidate=root/'index.html'
        payload=candidate.read_bytes();kind=mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
        self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-cache' if candidate.name=='index.html' else 'public, max-age=31536000, immutable');self.end_headers();self.wfile.write(payload)
    def dispatch(self):self.proxy() if self.path.startswith('/api/') else self.static()
    do_GET=dispatch;do_HEAD=dispatch;do_POST=dispatch;do_PUT=dispatch;do_PATCH=dispatch;do_DELETE=dispatch;do_OPTIONS=dispatch
    def log_message(self,fmt,*args):print('gateway',self.address_string(),fmt%args,flush=True)

ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
'''

START = r'''#requires -Version 5.1
[CmdletBinding()]param([Parameter(Mandatory=$true)][string]$DatabaseUrl,[Parameter(Mandatory=$true)][string]$DocumentStorageRoot,[int]$BackendPort=5110,[int]$FrontendPort=8110)
Set-StrictMode -Version Latest;$ErrorActionPreference='Stop';$root=$PSScriptRoot
$uri=[Uri]$DatabaseUrl;if($uri.Host -notin @('127.0.0.1','localhost','::1','[::1]') -or $uri.AbsolutePath.Trim('/') -notmatch '^forwarder_uat_'){throw 'UAT database must be an owned loopback database named forwarder_uat_*'}
$state=Join-Path $root '.uat-state';if(Test-Path -LiteralPath $state){throw 'UAT state already exists; run STOP-UAT.ps1 first'};New-Item -ItemType Directory -Path $state|Out-Null
$python=Join-Path $root 'runtime\python.exe';$secret=[guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N');$old=@{}
foreach($name in @('APP_ENV','DATABASE_URL','DOCUMENT_STORAGE_ROOT','SECRET_KEY','JWT_SECRET_KEY','AUTO_MIGRATE_ON_STARTUP','PORT','RELEASE_IDENTITY_PATH')){$old[$name]=[Environment]::GetEnvironmentVariable($name,'Process')}
try{
 $env:APP_ENV='uat';$env:DATABASE_URL=$DatabaseUrl;$env:DOCUMENT_STORAGE_ROOT=$DocumentStorageRoot;$env:SECRET_KEY=$secret;$env:JWT_SECRET_KEY=$secret;$env:AUTO_MIGRATE_ON_STARTUP='false';$env:PORT="$BackendPort";$env:RELEASE_IDENTITY_PATH=(Join-Path $root 'release-manifest.json')
 & $python -m backend.migration_cli check;if($LASTEXITCODE -ne 0){throw 'UAT database is not at the packaged head'}
 $backend=Start-Process -FilePath $python -ArgumentList @('-m','waitress',"--listen=127.0.0.1:$BackendPort",'backend.wsgi:app') -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $state 'backend.out.log') -RedirectStandardError (Join-Path $state 'backend.err.log')
 $frontend=Start-Process -FilePath $python -ArgumentList @('uat_gateway.py','--dist',(Join-Path $root 'dist'),'--port',"$FrontendPort",'--backend-port',"$BackendPort") -WorkingDirectory $root -PassThru -WindowStyle Hidden -RedirectStandardOutput (Join-Path $state 'frontend.out.log') -RedirectStandardError (Join-Path $state 'frontend.err.log')
 Set-Content -LiteralPath (Join-Path $state 'backend.pid') -Value $backend.Id;Set-Content -LiteralPath (Join-Path $state 'frontend.pid') -Value $frontend.Id
 $ready=$false;1..120|ForEach-Object{try{$r=Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort/api/health" -TimeoutSec 2;if($r.StatusCode -lt 500){$ready=$true}}catch{};if(-not $ready){Start-Sleep -Milliseconds 500}}
 if(-not $ready){& (Join-Path $root 'STOP-UAT.ps1');throw 'UAT runtime readiness timed out'}
 Write-Output "FORWARDER_UAT_URL=http://127.0.0.1:$FrontendPort";Write-Output 'FORWARDER_UAT_RUNTIME=READY'
}finally{foreach($name in $old.Keys){if($null -eq $old[$name]){Remove-Item "Env:$name" -ErrorAction SilentlyContinue}else{[Environment]::SetEnvironmentVariable($name,$old[$name],'Process')}}}
'''

STOP = r'''#requires -Version 5.1
[CmdletBinding()]param()
Set-StrictMode -Version Latest;$ErrorActionPreference='Stop';$root=$PSScriptRoot;$state=Join-Path $root '.uat-state'
if(-not(Test-Path -LiteralPath $state)){Write-Output 'FORWARDER_UAT_RUNTIME=ALREADY_STOPPED';exit 0}
foreach($name in @('frontend','backend')){$pidPath=Join-Path $state ($name+'.pid');if(Test-Path -LiteralPath $pidPath){$ownedPid=[int](Get-Content -LiteralPath $pidPath -Raw);$process=Get-CimInstance Win32_Process -Filter "ProcessId=$ownedPid" -ErrorAction SilentlyContinue;if($null -ne $process){if($process.ExecutablePath -ne (Join-Path $root 'runtime\python.exe')){throw "Refusing to stop non-package process $ownedPid"};& taskkill.exe /PID $ownedPid /T /F *> $null}}}
Remove-Item -LiteralPath $state -Recurse -Force;Write-Output 'FORWARDER_UAT_RUNTIME=STOPPED'
'''

VERIFY = r'''#requires -Version 5.1
[CmdletBinding()]param([string]$PackageRoot=$PSScriptRoot)
Set-StrictMode -Version Latest;$ErrorActionPreference='Stop';$meta=Get-Content -Raw -LiteralPath (Join-Path $PackageRoot 'release-manifest.json')|ConvertFrom-Json
if($meta.product_name -ne 'Forwarder' -or $meta.release_stage -ne 'UAT' -or $meta.application_version -ne '1.10.0' -or $meta.git_tag -ne 'forwarder-uat-v1.10.0' -or $meta.database_revision -ne '20260926_fixed_shipment_responsible_expert'){throw 'release identity mismatch'}
$expected=@{};foreach($line in Get-Content -LiteralPath (Join-Path $PackageRoot 'SHA256SUMS.txt')){$parts=$line -split '  ',2;if($parts.Count -ne 2 -or $parts[1] -match '^/|\.\.|^[A-Za-z]:'){throw 'malformed checksum'};$expected[$parts[1]]=$true;$path=Join-Path $PackageRoot $parts[1];if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw 'missing package file '+$parts[1]};if((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $parts[0]){throw 'checksum mismatch '+$parts[1]}}
foreach($file in Get-ChildItem -LiteralPath $PackageRoot -Recurse -File){$relative=$file.FullName.Substring($PackageRoot.TrimEnd('\').Length+1).Replace('\','/');if($relative -ne 'SHA256SUMS.txt' -and -not $expected.ContainsKey($relative)){throw 'unexpected package file '+$relative}}
Write-Output 'PACKAGE_LAYOUT=PASS';Write-Output 'PACKAGE_CHECKSUMS=PASS';Write-Output 'VERSION_IDENTITY_CONSISTENT=YES';Write-Output 'PACKAGE_SOURCE_SHA_VERIFIED=YES'
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if run(["git", "status", "--porcelain"], repo):
        raise RuntimeError("release source worktree must be clean")
    source_sha = run(["git", "rev-parse", "HEAD"], repo)
    if run(["git", "merge-base", BASE_SHA, source_sha], repo) != BASE_SHA:
        raise RuntimeError("release source is not based on the accepted product SHA")
    short_sha = source_sha[:12]
    package_name = f"Forwarder-UAT-v{VERSION}-{short_sha}"
    output_root = args.output_root.resolve()
    package_dir = output_root / package_name
    zip_path = output_root / f"{package_name}.zip"
    if package_dir.exists() or zip_path.exists():
        raise RuntimeError("refusing to overwrite an existing UAT release")

    with tempfile.TemporaryDirectory(prefix="forwarder-uat-source-") as temporary:
        archive = Path(temporary) / "source.zip"
        with archive.open("wb") as stream:
            subprocess.run(["git", "archive", "--format=zip", source_sha], cwd=repo, check=True, stdout=stream)
        source = Path(temporary) / "source"
        source.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(source)

        package = json.loads((source / "package.json").read_text(encoding="utf-8"))
        backend_tree = ast.parse((source / "backend/__init__.py").read_text(encoding="utf-8"))
        backend_version = next(ast.literal_eval(node.value) for node in backend_tree.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets))
        if package["version"] != VERSION or backend_version != VERSION:
            raise RuntimeError("authoritative version sources are inconsistent")
        _, heads = revision_graph(source / "backend/migrations/versions")
        if heads != [DATABASE_HEAD]:
            raise RuntimeError(f"expected one database head {DATABASE_HEAD}, got {heads}")

        build_env = os.environ.copy()
        build_env["VITE_API_URL"] = "__FORWARDER_SAME_ORIGIN__"
        subprocess.run(["npm.cmd" if os.name == "nt" else "npm", "run", "build"], cwd=repo, env=build_env, check=True)

        package_dir.mkdir(parents=True)
        for name in ("backend", "contracts"):
            shutil.copytree(source / name, package_dir / name, ignore=shutil.ignore_patterns("__pycache__", "tests", "Dockerfile", "docker-compose*"))
        shutil.copytree(repo / "dist", package_dir / "dist")
        for name in ("manage.py", "requirements-release.txt", "package.json", "verify_package_secrets.py"):
            shutil.copy2(source / name, package_dir / name)
        runtime = repo / "release-candidates" / RUNTIME_NAME
        runtime_manifest = Path(str(runtime) + ".manifest.json")
        if not runtime.is_file() or sha256(runtime) != RUNTIME_SHA256:
            raise RuntimeError("approved Windows runtime is unavailable or changed")
        if not runtime_manifest.is_file():
            raise RuntimeError("approved Windows runtime manifest is unavailable")
        with zipfile.ZipFile(runtime) as bundle:
            bundle.extractall(package_dir / "runtime")
        verify_runtime_tree(package_dir / "runtime", runtime_manifest)
        shutil.copy2(runtime_manifest, package_dir / "runtime-manifest.json")

        frontend_build_id = sha256(package_dir / "dist/index.html")[:16]
        built_at = datetime.now(timezone.utc).isoformat()
        manifest = {
            "schema": "forwarder-uat-release-manifest-v1",
            "product_name": "Forwarder",
            "release_stage": "UAT",
            "previous_product_version": PREVIOUS_VERSION,
            "application_version": VERSION,
            "frontend_version": VERSION,
            "backend_version": VERSION,
            "accepted_product_base_sha": BASE_SHA,
            "release_source_sha": source_sha,
            "application_commit": source_sha,
            "git_commit": source_sha,
            "git_tag": RELEASE_TAG,
            "tag_target_sha": source_sha,
            "database_revision": DATABASE_HEAD,
            "alembic_head_count": 1,
            "build_date": built_at,
            "release_id": RELEASE_ID,
            "package_filename": zip_path.name,
            "frontend_build_id": frontend_build_id,
            "runtime_entrypoint": "START-UAT.ps1",
            "runtime_id": "Forwarder-Windows-Runtime-S7-RC-a257669-r4",
            "runtime_sha256": RUNTIME_SHA256,
            "historical_security_remediation": HISTORICAL_SECURITY_REMEDIATION,
            "reference_impact": "NONE",
            "production_accessed": False,
        }
        (package_dir / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (package_dir / "uat_gateway.py").write_text(GATEWAY, encoding="utf-8")
        (package_dir / "START-UAT.ps1").write_text(START, encoding="utf-8-sig")
        (package_dir / "STOP-UAT.ps1").write_text(STOP, encoding="utf-8-sig")
        (package_dir / "VERIFY-PACKAGE.ps1").write_text(VERIFY, encoding="utf-8-sig")
        (package_dir / "README-UAT.md").write_text(
            f"# Forwarder UAT v{VERSION}\n\nThis immutable package is for a non-Production Customer UAT session. Verify with `VERIFY-PACKAGE.ps1`, migrate an owned loopback database named `forwarder_uat_*` to `{DATABASE_HEAD}`, then start with `START-UAT.ps1`. Credentials are provisioned outside Git by the approved UAT fixture runner.\n",
            encoding="utf-8",
        )

        payload = []
        for path in sorted(item for item in package_dir.rglob("*") if item.is_file()):
            payload.append({"path": path.relative_to(package_dir).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
        (package_dir / "PACKAGE-INVENTORY.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        files = sorted(item for item in package_dir.rglob("*") if item.is_file())
        (package_dir / "SHA256SUMS.txt").write_text("\n".join(f"{sha256(path)}  {path.relative_to(package_dir).as_posix()}" for path in files) + "\n", encoding="utf-8")

        output_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "x", zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for path in sorted(item for item in package_dir.rglob("*") if item.is_file()):
                bundle.write(path, path.relative_to(package_dir).as_posix())
        sidecar = Path(str(zip_path) + ".sha256")
        sidecar.write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="forwarder-uat-verify-") as temporary:
        extracted = Path(temporary) / "package"
        with zipfile.ZipFile(zip_path) as bundle:
            bundle.extractall(extracted)
        for line in (extracted / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
            expected, relative = line.split("  ", 1)
            target = extracted / relative
            if not target.is_file() or sha256(target) != expected:
                raise RuntimeError(f"extracted checksum verification failed: {relative}")
        verify_runtime_tree(extracted / "runtime", extracted / "runtime-manifest.json")
        # The approved third-party runtime contains ordinary library examples
        # using words such as "password".  It is verified byte-for-byte above;
        # the Forwarder secret policy scanner therefore evaluates the product
        # payload while the dependency runtime remains governed by its own
        # complete manifest and pinned archive hash.
        shutil.rmtree(extracted / "runtime")
        subprocess.run([sys.executable, str(extracted / "verify_package_secrets.py"), str(extracted)], cwd=extracted, check=True)

    result = {
        "release_id": RELEASE_ID,
        "release_source_sha": source_sha,
        "release_tag": RELEASE_TAG,
        "database_head": DATABASE_HEAD,
        "package_path": str(zip_path),
        "package_sha256": sha256(zip_path),
        "package_size": zip_path.stat().st_size,
        "package_directory": str(package_dir),
    }
    (output_root / f"{package_name}.build-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
