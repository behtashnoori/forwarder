"""Build the separate, RC-specific DP.1 deployment package."""
from __future__ import annotations
import hashlib,json,shutil,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PACKAGE_ID='D2-VALIDATION-S7-RC-a257669-rg1-frozen-r3'
IDENTITY={'expected_application_release_id':'S7-RC-a257669-rg1-frozen','expected_application_source_sha':'a2576690364fcaf58ca7ddc6c57143c3084bbb00','expected_application_zip_sha256':'aca7a147cad97edf0e3f03d763c63471c283f62021a23a4e6a47b5e59aa88534','expected_application_zip_size':1323912,'target_alembic_head':'20260908_governed_international_geography','lpaf_version':'2.2','rollback_strategy':'KEEP_UPGRADED_DB_AND_ROLLBACK_APP','mutation_boundary':'PRECHECK_COMPLETE then READY_FOR_FIRST_MUTATION after explicit authorization'}
FILES=['README-OPERATOR.md','preflight_a257669.ps1','deploy_a257669.ps1','validate_a257669.ps1']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(output:Path):
 output.mkdir(parents=True,exist_ok=True); artifact=output/(PACKAGE_ID+'.zip');side=output/(artifact.name+'.manifest.json')
 if artifact.exists() or side.exists():raise RuntimeError('refusing to overwrite deployment package')
 with tempfile.TemporaryDirectory() as d:
  stage=Path(d); records=[]
  for name in FILES:
   src=ROOT/'scripts/deploy'/name;dst=stage/name;shutil.copy2(src,dst);records.append({'path':name,'sha256':sha(dst),'bytes':dst.stat().st_size})
  manifest={'schema':'forwarder-dp1-deployment-package-v1','deployment_package_id':PACKAGE_ID,**IDENTITY,'files':records,'required_future_inputs':['read-only preflight evidence','approved backup identity','staged application ZIP and sidecar','new target release path']}
  (stage/'deployment-manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
  with zipfile.ZipFile(artifact,'x',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(stage.iterdir()):z.write(p,p.name)
 side.write_text(json.dumps({'artifact_filename':artifact.name,'artifact_size':artifact.stat().st_size,'artifact_sha256':sha(artifact),'deployment_package_id':PACKAGE_ID},indent=2)+'\n',encoding='utf-8')
 return artifact,side
if __name__=='__main__':
 a,b=build(Path(sys.argv[1]));print(json.dumps({'artifact':str(a),'manifest':str(b),'sha256':sha(a)}))
