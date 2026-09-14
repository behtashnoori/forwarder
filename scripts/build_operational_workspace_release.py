"""Build the single allowlisted Windows/IIS/Waitress operational release."""
from __future__ import annotations
import ast,hashlib,json,shutil,subprocess,sys,tempfile,zipfile,os
from pathlib import Path
APP='e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4'; BEFORE='20260920_legal_customer_nullable_contact_names'; TARGET='20260921_shipment_evidence_ownership'; NAME='Forwarder-Operational-Workspace-Production-CERTIFIED'; RUNTIME_PACKAGE='Forwarder-Windows-Runtime.zip'; RHASH='f4a8f108aa89a78d7986f01fb8f6aa8af5e2d35e00617a8453eb1f15df945070'
STALE=('S7-RC','S8-RC','a9ed9ae','20260908_governed_international_geography','NO Alembic upgrade in S8')
STATE_REQUIRED=('ALL_RELEASE_STATE_VARIABLES_AUDITED=YES','UNINITIALIZED_GLOBAL_READS=0','UNINITIALIZED_SCRIPT_READS=0','STATE_LIFECYCLE_AUDIT=PASS','FRESH_PROCESS_VALIDATEONLY=PASS','STRICTMODE_FRESH_PROCESS=PASS','ARBITRARY_CWD_VALIDATEONLY=PASS','AMBIENT_GLOBAL_STATE_INDEPENDENCE=PASS','REPEATED_INVOCATION_MATRIX=PASS','ROLLBACK_FAILURE_REPORTING=PASS','QUALIFICATION_ESCAPE_ROOT_CAUSE_CLOSED=YES','REGRESSION_TEST_ADDED=YES','REAL_EXECUTE_CODEPATH=PASS')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def active_lineage_gate(root, tooling_commit):
 expected={'candidate':NAME,'application_source_commit':APP,'tooling_commit':tooling_commit,'production_before_revision':BEFORE,'required_db_revision':TARGET,'migration_required':True,'runtime_sha256':RHASH}
 for name in ('RELEASE-METADATA.json','artifact/release-manifest.json'):
  if json.loads((root/name).read_text(encoding='utf-8'))!=expected:raise RuntimeError('release metadata mismatch: '+name)
 for name in ('VERIFY-PACKAGE.ps1','CERTIFY-RELEASE.ps1','QUALIFY-REAL-VALIDATEONLY.ps1','QUALIFY-REAL-EXECUTE.ps1','deploy_windows_iis_waitress.ps1','SERVER-DEPLOY-STEPS.md','ROLLBACK.md'):
  content=(root/name).read_text(encoding='utf-8')
  if any(token.lower() in content.lower() for token in STALE):raise RuntimeError('stale active release lineage: '+name)
  if name.endswith('.ps1') and '20260908_governed_international_geography' in content:raise RuntimeError('stale revision in script: '+name)
 if APP not in (root/'VERIFY-PACKAGE.ps1').read_text(encoding='utf-8'):raise RuntimeError('application verification missing')
 return expected
def migration_inventory_gate(root,repo):
 base='backend/migrations/versions'
 names={p for p in subprocess.check_output(['git','ls-tree','-r','--name-only',APP,base],cwd=repo,text=True).splitlines() if p.endswith('.py')}
 found={p.relative_to(root/'artifact').as_posix() for p in (root/'artifact'/base).glob('*.py')}
 if found!=names:raise RuntimeError('package migration inventory differs from frozen application commit')
 graph={}
 for name in names:
  content=subprocess.check_output(['git','show',APP+':'+name],cwd=repo)
  if (root/'artifact'/name).read_bytes().replace(b'\r\n',b'\n')!=content.replace(b'\r\n',b'\n'):raise RuntimeError('migration content differs from frozen application commit: '+name)
  variables={}
  for statement in ast.parse(content).body:
   if isinstance(statement,ast.Assign):
    for target in statement.targets:
     if isinstance(target,ast.Name) and target.id in ('revision','down_revision'):variables[target.id]=ast.literal_eval(statement.value)
  if 'revision' in variables:graph[variables['revision']]=variables.get('down_revision')
 referenced={parent for value in graph.values() for parent in (value if isinstance(value,(list,tuple)) else (value,)) if parent}
 if set(graph)-referenced!={TARGET}:raise RuntimeError('migration graph has an unexpected head')
def corruption_matrix(root,ps):
 verify=root/'VERIFY-PACKAGE.ps1'
 def rejected():
  result=subprocess.run([ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(verify),'-PackageRoot',str(root)],capture_output=True,text=True,timeout=120)
  if result.returncode==0:raise RuntimeError('corrupted package was accepted')
 for name in ('RELEASE-METADATA.json','artifact/release-manifest.json','ROLLBACK.md'):
  path=root/name;original=path.read_bytes()
  try:
   path.write_bytes(original.replace(APP.encode(),b'0'*40,1) if name.endswith('.json') else original+b'\nTAMPER\n')
   rejected()
  finally:path.write_bytes(original)
 for name in ('artifact/backend/migrations/versions/'+TARGET+'.py','artifact/runtime/python.exe'):
  path=root/name;missing=path.with_name(path.name+'.missing')
  path.rename(missing)
  try:rejected()
  finally:missing.rename(path)
 extra=root/'UNLISTED-README.md'
 try:extra.write_text('unlisted active content',encoding='utf-8');rejected()
 finally:extra.unlink(missing_ok=True)
def main():
 repo=Path(__file__).resolve().parents[1]; out=repo/'release-candidates'/NAME
 qualification=tempfile.TemporaryDirectory(prefix='forwarder-tooling-preview-') if '--preview' in sys.argv else None
 if qualification:out=Path(qualification.name)/NAME
 if not qualification:
  subprocess.run(['git','diff','--exit-code','HEAD','--','scripts/build_operational_workspace_release.py','scripts/deploy/deploy_windows_iis_waitress_operational.ps1','scripts/tests','ops/adr043-production-readonly-preflight.ps1'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
  subprocess.run(['git','diff','--exit-code',APP,'HEAD','--','backend','src','contracts','public','package.json','package-lock.json'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
 if '--finalize' in sys.argv:
  if (out/'CERTIFICATION-PASS.json').exists():raise RuntimeError('certified candidate is immutable')
  current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
  active_lineage_gate(out,current)
  files=sorted(p for p in out.rglob('*') if p.is_file() and p.name not in {'SHA256SUMS.txt',NAME+'.zip',NAME+'.zip.sha256','FINAL-CERTIFIED.json'})
  (out/'SHA256SUMS.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(out).as_posix()}' for p in files)+'\n')
  zp=out/(NAME+'.zip')
  with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(x for x in out.rglob('*') if x.is_file() and x!=zp and x.name not in {'FINAL-CERTIFIED.json'}):z.write(p,p.relative_to(out))
  (Path(str(zp)+'.sha256')).write_text(sha(zp)+'  '+zp.name+'\n')
  # Certify the bytes that will be transferred, never the build directory.
  with tempfile.TemporaryDirectory() as extraction:
   extracted=Path(extraction)/NAME
   with zipfile.ZipFile(zp) as z:z.extractall(extracted)
   for line in (extracted/'SHA256SUMS.txt').read_text().splitlines():
    expected,relative=line.split('  ',1); actual=extracted/relative
    if not actual.is_file() or sha(actual)!=expected:raise RuntimeError('extracted package checksum verification failed: '+relative)
   metadata=json.loads((extracted/'RELEASE-METADATA.json').read_text())
   if metadata != active_lineage_gate(extracted,current):raise RuntimeError('extracted package metadata verification failed')
   migration_inventory_gate(extracted,repo)
   ps='powershell.exe' if os.name=='nt' else 'pwsh'
   checks=subprocess.run([ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(extracted/'CERTIFY-RELEASE.ps1'),'-PackageRoot',str(extracted)],capture_output=True,text=True,timeout=1800)
   required=('PACKAGE_LAYOUT=PASS','PACKAGE_CHECKSUMS=PASS','FULL_EXECUTE_SIMULATION=PASS','FAILURE_INJECTION_MATRIX=PASS','ROLLBACK_MATRIX=PASS','REAL_NONFIXTURE_VALIDATEONLY=PASS','VALIDATEONLY_ZERO_MUTATION=PASS')
   if checks.returncode or any(mark not in checks.stdout for mark in required+STATE_REQUIRED):raise RuntimeError('extracted certification failed: '+checks.stdout+' '+checks.stderr)
   (repo/'qualification'/'state-lifecycle-final-certification.log').write_text(checks.stdout+'\n'+checks.stderr)
   corruption_matrix(extracted,ps)
  certificate={'zip_sha256':sha(zp),'application_commit':APP,'tooling_commit':metadata['tooling_commit'],'certified_extracted_zip':zp.name,'state_lifecycle_audit':'PASS','qualification_markers':list(required+STATE_REQUIRED),'package_corruption_matrix':'PASS'}
  (out/'CERTIFICATION-PASS.json').write_text(json.dumps(certificate,indent=2)+'\n')
  print('FINAL_PACKAGE_CERTIFICATION=PASS');print(zp);return
 if out.exists():
  # A candidate is immutable only after extracted-artifact certification writes
  # its certificate.  This permits repair of a locally interrupted build.
  if (out/'CERTIFICATION-PASS.json').exists() and '--replace-invalidated' not in sys.argv:raise RuntimeError('certified candidate may not be replaced')
  if out.resolve().parent != (repo/'release-candidates').resolve():raise RuntimeError('candidate path escaped release-candidates')
  if '--replace-invalidated' in sys.argv:
   previous_zip=out/(NAME+'.zip')
   invalidated=out.with_name(NAME+'-INVALIDATED-'+sha(previous_zip)[:12])
   if invalidated.exists():raise RuntimeError('invalidated archive already exists')
   out.rename(invalidated)
  else:shutil.rmtree(out) # only interrupted, uncertified local assembly
 if subprocess.run(['git','diff','--quiet','--','backend','src','contracts','public','package.json','package-lock.json'],cwd=repo).returncode:raise RuntimeError('tracked product worktree is dirty')
 if not qualification:subprocess.run([('npm.cmd' if os.name=='nt' else 'npm'),'run','build'],cwd=repo,check=True)
 runtime=next((p for p in (repo/'release-candidates').glob('*Runtime*.zip') if sha(p)==RHASH),None)
 if runtime is None:raise RuntimeError('allowlisted Windows runtime checksum unavailable')
 with tempfile.TemporaryDirectory() as t:
  source=Path(t)/'source';source.mkdir();subprocess.run(['git','archive','--format=zip',APP],cwd=repo,stdout=(Path(t)/'src.zip').open('wb'),check=True)
  with zipfile.ZipFile(Path(t)/'src.zip') as z:z.extractall(source)
  root=out; art=root/'artifact';art.mkdir(parents=True)
  for n in ('backend','contracts'):
   shutil.copytree(source/n,art/n,ignore=shutil.ignore_patterns('__pycache__','tests','Dockerfile','docker-compose*'))
  shutil.copytree(repo/'dist',art/'dist')
  for n in ('manage.py','requirements.txt','requirements-release.txt'):
   shutil.copy2(source/n,art/n)
  shutil.copy2(runtime,art/RUNTIME_PACKAGE)
  with zipfile.ZipFile(runtime) as z:z.extractall(art/'runtime')
  tool=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
  meta={'candidate':NAME,'application_source_commit':APP,'tooling_commit':tool,'production_before_revision':BEFORE,'required_db_revision':TARGET,'migration_required':True,'runtime_sha256':RHASH}
  (root/'RELEASE-METADATA.json').write_text(json.dumps(meta,indent=2)+'\n')
  (art/'release-manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
  shutil.copy2(repo/'scripts/deploy/deploy_windows_iis_waitress_operational.ps1',root/'deploy_windows_iis_waitress.ps1')
  shutil.copy2(repo/'scripts/tests/test_operational_release_pipeline.ps1',root/'CERTIFY-RELEASE.ps1')
  shutil.copy2(repo/'scripts/tests/test_real_nonfixture_validateonly.ps1',root/'QUALIFY-REAL-VALIDATEONLY.ps1')
  shutil.copy2(repo/'scripts/tests/test_real_execute_simulation.ps1',root/'QUALIFY-REAL-EXECUTE.ps1')
  shutil.copy2(repo/'scripts/tests/audit_release_state_lifecycle.ps1',root/'AUDIT-STATE-LIFECYCLE.ps1')
  shutil.copy2(repo/'scripts/tests/STATE-LIFECYCLE-AUDIT.md',root/'STATE-LIFECYCLE-AUDIT.md')
  verify = """#requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$PackageRoot)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop
$meta=Get-Content -Raw -LiteralPath (Join-Path $PackageRoot 'RELEASE-METADATA.json')|ConvertFrom-Json
if($meta.application_source_commit -ne '"""+APP+"""' -or $meta.tooling_commit -ne '"""+tool+"""' -or $meta.production_before_revision -ne '"""+BEFORE+"""' -or $meta.required_db_revision -ne '"""+TARGET+"""' -or -not $meta.migration_required){throw 'VERIFY_FAIL metadata'}
foreach($x in @('artifact\\dist\\index.html','artifact\\backend\\wsgi.py','artifact\\runtime\\python.exe','artifact\\Forwarder-Windows-Runtime.zip','artifact\\release-manifest.json','artifact\\backend\\migrations\\versions\\20260920_legal_customer_nullable_contact_names.py','artifact\\backend\\migrations\\versions\\20260921_shipment_evidence_ownership.py')){if(-not(Test-Path -LiteralPath (Join-Path $PackageRoot $x))){throw 'VERIFY_FAIL '+$x}}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $PackageRoot 'artifact\\release-manifest.json')|ConvertFrom-Json
if($manifest.application_source_commit -ne $meta.application_source_commit -or $manifest.tooling_commit -ne $meta.tooling_commit -or $manifest.production_before_revision -ne $meta.production_before_revision -or $manifest.required_db_revision -ne $meta.required_db_revision -or -not $manifest.migration_required){throw 'VERIFY_FAIL manifest metadata'}
$expected=@{}
foreach($line in Get-Content -LiteralPath (Join-Path $PackageRoot 'SHA256SUMS.txt')){$parts=$line -split '  ',2;if($parts.Count -ne 2 -or $parts[1] -match '^/|\\.\\.|^[A-Za-z]:'){throw 'VERIFY_FAIL malformed checksum'};if($expected.ContainsKey($parts[1])){throw 'VERIFY_FAIL duplicate checksum'};$expected[$parts[1]]=$true;$path=Join-Path $PackageRoot $parts[1].Replace('/','\\');if(-not(Test-Path -LiteralPath $path)){throw 'VERIFY_FAIL missing checksummed file '+$parts[1]};if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $parts[0].ToLowerInvariant()){throw 'VERIFY_FAIL checksum '+$parts[1]}}
foreach($file in Get-ChildItem -LiteralPath $PackageRoot -Recurse -File){$relative=$file.FullName.Substring($PackageRoot.TrimEnd('\\').Length+1).Replace('\\','/');if($relative -ne 'SHA256SUMS.txt' -and -not $expected.ContainsKey($relative)){throw 'VERIFY_FAIL unexpected package file '+$relative}}
foreach($name in @('CERTIFY-RELEASE.ps1','QUALIFY-REAL-VALIDATEONLY.ps1','QUALIFY-REAL-EXECUTE.ps1','deploy_windows_iis_waitress.ps1','SERVER-DEPLOY-STEPS.md','ROLLBACK.md')){$content=Get-Content -Raw -LiteralPath (Join-Path $PackageRoot $name);if($content -match '(?i)S[78]-RC|a9ed[0-9a-f]{3}|20260908_governed_international_|No Alembic upgrade in S[78]'){throw 'VERIFY_FAIL stale active lineage '+$name}}
Write-Output 'PACKAGE_LAYOUT=PASS';Write-Output 'PACKAGE_CHECKSUMS=PASS';Write-Output 'PACKAGE_MIGRATION_COMPLETENESS=PASS';Write-Output 'RUNTIME_VERIFICATION=PASS';Write-Output 'RELEASE_METADATA_CONSISTENT=PASS';Write-Output 'STALE_ACTIVE_RELEASE_LINEAGE=0'
"""
  (root/'VERIFY-PACKAGE.ps1').write_text(verify,encoding='utf-8')
  (root/'SERVER-DEPLOY-STEPS.md').write_text(r'''# Forwarder production deployment

Use an elevated Windows PowerShell 5.1 session. All commands are absolute and independent of the current directory. Do not run Execute unless every prior gate passes.

1. Copy `Forwarder-Operational-Workspace-Production-CERTIFIED.zip` and its `.zip.sha256` sidecar to `C:\1-webapp\forwarder-production\incoming`.
2. Verify ZIP SHA-256 against the supplied sidecar:
   `$zip = 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED.zip'`
   `$expected = (Get-Content -LiteralPath 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED.zip.sha256' -Raw).Split(' ')[0]`
   `if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ine $expected) { throw 'ZIP SHA256 mismatch' }`
3. Extract:
   `Expand-Archive -LiteralPath 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED.zip' -DestinationPath 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED'`
4. Verify package:
   `& 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED\VERIFY-PACKAGE.ps1' -PackageRoot 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED'`
5. Certify release:
   `& 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED\CERTIFY-RELEASE.ps1' -PackageRoot 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED'`
6. Read-only real ValidateOnly:
   `$root = 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED'`
   `& "$root\deploy_windows_iis_waitress.ps1" -PackageRoot $root -ValidateOnly`
7. Only if PASS, execute with explicit confirmation:
   `& 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED\deploy_windows_iis_waitress.ps1' -PackageRoot 'C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED' -Execute -ConfirmDeployment`
8. Check `http://127.0.0.1:5101/api/health` and `https://samand.forwarderet.ir/api/health`.
9. On failure, follow `C:\1-webapp\forwarder-production\incoming\Forwarder-Operational-Workspace-Production-CERTIFIED\ROLLBACK.md` and preserve the error output.

Database gate: only `20260920_legal_customer_nullable_contact_names` can migrate to `20260921_shipment_evidence_ownership`; the target itself is already current. Every other value stops. The external environment is `C:\1-webapp\forwarder-runtime\production.env`.
''',encoding='utf-8')
  (root/'ROLLBACK.md').write_text(r'''# Rollback and recovery

The deployment captures IIS physicalPath, Scheduled Task XML and enabled state, and the existing Waitress executable identity before cutover. After a cutover failure it disables the task, stops only the identified target listener, waits for port release, restores IIS and task XML/enabled state, starts the previous backend, then checks the previous listener and internal health. A failed rollback is reported distinctly and requires an operator to stop and investigate; never retry blindly.

An applied database migration is never silently downgraded. The pre-release application must be confirmed compatible with the migrated schema before relying on application rollback. Preserve the full deployment output and database backup for recovery. If a failure occurred before the cutover mutation boundary, no running service was changed.
''',encoding='utf-8')
  active_lineage_gate(root,tool)
  migration_inventory_gate(root,repo)
  files=sorted(p for p in root.rglob('*') if p.is_file());(root/'SHA256SUMS.txt').write_text('\n'.join(f'{sha(p)}  {p.relative_to(root).as_posix()}' for p in files)+'\n')
  if qualification:
   ps='powershell.exe' if os.name=='nt' else 'pwsh'
   result=subprocess.run([ps,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(root/'CERTIFY-RELEASE.ps1'),'-PackageRoot',str(root)],capture_output=True,text=True,timeout=1800)
   required=('PACKAGE_LAYOUT=PASS','PACKAGE_CHECKSUMS=PASS','FULL_EXECUTE_SIMULATION=PASS','FAILURE_INJECTION_MATRIX=PASS','ROLLBACK_MATRIX=PASS','REAL_NONFIXTURE_VALIDATEONLY=PASS','VALIDATEONLY_ZERO_MUTATION=PASS','REAL_EXECUTE_CODEPATH=PASS')
   if result.returncode or any(marker not in result.stdout for marker in required+STATE_REQUIRED):raise RuntimeError('tooling preview certification failed: '+result.stdout+' '+result.stderr)
   corruption_matrix(root,ps)
   print(result.stdout)
   print('PACKAGE_CORRUPTION_MATRIX=PASS')
   qualification.cleanup()
   return
  print('staged release content: '+str(root))
  # Final certification is deliberately a separate, post-freeze operation.
if __name__=='__main__':main()
