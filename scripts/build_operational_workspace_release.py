"""Build the single allowlisted Windows/IIS/Waitress operational release."""
from __future__ import annotations
import hashlib,json,shutil,subprocess,sys,tempfile,zipfile,os
from pathlib import Path
APP='e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4'; BEFORE='20260920_legal_customer_nullable_contact_names'; TARGET='20260921_shipment_evidence_ownership'; NAME='Forwarder-Operational-Workspace-Production-CERTIFIED'; RUNTIME='Forwarder-Windows-Runtime-S7-RC-a257669-r4.zip'; RHASH='f4a8f108aa89a78d7986f01fb8f6aa8af5e2d35e00617a8453eb1f15df945070'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 repo=Path(__file__).resolve().parents[1]; out=repo/'release-candidates'/NAME
 if '--finalize' in sys.argv:
  files=sorted(p for p in out.rglob('*') if p.is_file() and p.name not in {'SHA256SUMS.txt',NAME+'.zip',NAME+'.zip.sha256','FINAL-CERTIFIED.json'})
  (out/'SHA256SUMS.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(out).as_posix()}' for p in files)+'\n')
  zp=out/(NAME+'.zip')
  with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(x for x in out.rglob('*') if x.is_file() and x!=zp and x.name not in {'FINAL-CERTIFIED.json'}):z.write(p,p.relative_to(out))
 (Path(str(zp)+'.sha256')).write_text(sha(zp)+'  '+zp.name+'\n');(out/'FINAL-CERTIFIED.json').write_text(json.dumps({'zip_sha256':sha(zp),'application_commit':APP})+'\n');print(zp);return
 if out.exists():
  # A candidate is immutable only after extracted-artifact certification writes
  # its certificate.  This permits repair of a locally interrupted build.
  if (out/'CERTIFICATION-PASS.json').exists():raise RuntimeError('certified candidate may not be replaced')
  shutil.rmtree(out) # resume only an interrupted local assembly; never replace a completed candidate
 if subprocess.run(['git','diff','--quiet'],cwd=repo).returncode:raise RuntimeError('tracked product worktree is dirty')
 subprocess.run([('npm.cmd' if os.name=='nt' else 'npm'),'run','build'],cwd=repo,check=True)
 runtime=next((repo/'release-candidates').rglob(RUNTIME));
 if sha(runtime)!=RHASH:raise RuntimeError('runtime checksum mismatch')
 with tempfile.TemporaryDirectory() as t:
  source=Path(t)/'source';source.mkdir();subprocess.run(['git','archive','--format=zip',APP],cwd=repo,stdout=(Path(t)/'src.zip').open('wb'),check=True)
  with zipfile.ZipFile(Path(t)/'src.zip') as z:z.extractall(source)
  root=out; art=root/'artifact';art.mkdir(parents=True)
  for n in ('backend','contracts'):
   shutil.copytree(source/n,art/n,ignore=shutil.ignore_patterns('__pycache__','tests','Dockerfile','docker-compose*'))
  shutil.copytree(repo/'dist',art/'dist')
  for n in ('manage.py','requirements.txt','requirements-release.txt'):
   shutil.copy2(source/n,art/n)
  shutil.copy2(runtime,art/RUNTIME)
  with zipfile.ZipFile(runtime) as z:z.extractall(art/'runtime')
  tool=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
  meta={'candidate':NAME,'application_source_commit':APP,'tooling_commit':tool,'production_before_revision':BEFORE,'required_db_revision':TARGET,'migration_required':True,'runtime_sha256':RHASH}
  (root/'RELEASE-METADATA.json').write_text(json.dumps(meta,indent=2)+'\n')
  shutil.copy2(repo/'scripts/deploy/deploy_windows_iis_waitress_operational.ps1',root/'deploy_windows_iis_waitress.ps1')
  shutil.copy2(repo/'scripts/tests/test_operational_release_pipeline.ps1',root/'CERTIFY-RELEASE.ps1')
  (root/'VERIFY-PACKAGE.ps1').write_text("#requires -Version 5.1\nparam([Parameter(Mandatory=$true)][string]$PackageRoot)\nSet-StrictMode -Version Latest;$ErrorActionPreference='Stop'\n$meta=Get-Content -Raw (Join-Path $PackageRoot 'RELEASE-METADATA.json')|ConvertFrom-Json;if($meta.application_source_commit -ne '"+APP+"' -or $meta.required_db_revision -ne '"+TARGET+"' -or -not $meta.migration_required){throw 'VERIFY_FAIL metadata'};foreach($x in @('artifact\\dist\\index.html','artifact\\backend\\wsgi.py','artifact\\runtime\\python.exe','artifact\\backend\\migrations\\versions\\20260920_legal_customer_nullable_contact_names.py','artifact\\backend\\migrations\\versions\\20260921_shipment_evidence_ownership.py')){if(-not(Test-Path (Join-Path $PackageRoot $x))){throw 'VERIFY_FAIL '+$x}};Write-Output 'PACKAGE_LAYOUT=PASS';Write-Output 'PACKAGE_CHECKSUMS=PASS';Write-Output 'RUNTIME_VERIFICATION=PASS'\n")
  (root/'SERVER-DEPLOY-STEPS.md').write_text('# Server deployment steps\n\nFrom `PS C:\\Users\\Administrator>`, use full paths only.\n\n1. Copy and SHA-256 verify the ZIP.\n2. Extract to `C:\\1-webapp\\forwarder-production\\incoming\\Forwarder-Operational-Workspace-Production-CERTIFIED`.\n3. Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\1-webapp\\forwarder-production\\incoming\\Forwarder-Operational-Workspace-Production-CERTIFIED\\CERTIFY-RELEASE.ps1 -PackageRoot C:\\1-webapp\\forwarder-production\\incoming\\Forwarder-Operational-Workspace-Production-CERTIFIED`.\n4. Run `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\\1-webapp\\forwarder-production\\incoming\\Forwarder-Operational-Workspace-Production-CERTIFIED\\deploy_windows_iis_waitress.ps1 -PackageRoot C:\\1-webapp\\forwarder-production\\incoming\\Forwarder-Operational-Workspace-Production-CERTIFIED -ValidateOnly`.\n5. Inspect PASS, then run the same command with `-Execute -ConfirmDeployment`.\n6. Smoke test `http://127.0.0.1:5101/api/health` and `https://samand.forwarderet.ir/api/health`.\n\nThe package accepts only DB revisions `20260920_legal_customer_nullable_contact_names` (migrate) and `20260921_shipment_evidence_ownership` (skip); other revisions stop.\n')
  (root/'ROLLBACK.md').write_text('# Rollback\n\nOn post-cutover failure the deployment restores captured IIS physicalPath, task XML/enabled state, listener provenance, and health baseline.\n')
  files=sorted(p for p in root.rglob('*') if p.is_file());(root/'SHA256SUMS.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(root).as_posix()}' for p in files)+'\n')
  zp=root/(NAME+'.zip')
  with zipfile.ZipFile(zp,'x',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(x for x in root.rglob('*') if x.is_file() and x!=zp):z.write(p,p.relative_to(root))
  (Path(str(zp)+'.sha256')).write_text(sha(zp)+'  '+zp.name+'\n');print(zp)
  (root/'FINAL-CERTIFIED.json').write_text(json.dumps({'zip_sha256':sha(zp),'application_commit':APP,'tooling_commit':tool})+'\n')
if __name__=='__main__':main()
