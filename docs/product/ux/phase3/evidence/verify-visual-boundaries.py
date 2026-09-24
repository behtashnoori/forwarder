"""Read-only preservation qualification; writes only this mission's evidence JSON."""
from pathlib import Path
import hashlib
import json
import subprocess
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[5]
v2 = Path('D:/1-webapp/forwarder-dev/phase3-ux-prototype-revision-v2')
canonical = Path('D:/1-webapp/15-forwarder-golden-20260921')
artifact = '32d5a14ae70f0b74747f4ab4c3a7bea185002dc5'
base = 'docs/product/ux/phase3/'
def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()

preserved = [base+'prototype/app.js', base+'prototype/styles.css', base+'STORYTELLING-AUDIT-V2.md',
             base+'MICROCOPY-AUDIT-V2.md', base+'SCREEN-INVENTORY.md', base+'STATE-MATRIX.md',
             'docs/product/FORWARDER-OPERATIONAL-SHIPMENT-PRODUCT-CONTRACT-V1-FA.md',
             'docs/product/FORWARDER-PRODUCT-ACCEPTANCE-JOURNEYS-V1.1-FA.md']
checks = []
for file in preserved:
    same = (root/file).read_bytes() == (v2/file).read_bytes()
    assert same, file+' differs from V2'
    checks.append({'file': file, 'result': 'BYTE_IDENTICAL', 'sha256': sha(root/file)})

assert git(v2,'rev-parse','HEAD') == 'dd02ae58b58fb83fa539863c66b2e46f02c35bda'
assert git(canonical,'rev-parse','HEAD') == 'd83b1aa7c0011221188e753c0f38d2058859400b'
assert not git(v2,'status','--porcelain') and not git(canonical,'status','--porcelain')
subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor',git(v2,'rev-parse','HEAD'),'HEAD'],check=True)
changed = git(root,'diff','--name-only',git(canonical,'rev-parse','HEAD'),'HEAD').splitlines()
assert all(x.startswith('docs/product/ux/') for x in changed)
for file in (root/base/'evidence/browser').glob('*'):
    if file.is_file(): assert file.read_bytes() == (v2/base/'evidence/browser'/file.name).read_bytes()
for file in (root/base/'evidence/browser-v2').glob('*'):
    if file.is_file(): assert file.read_bytes() == (v2/base/'evidence/browser-v2'/file.name).read_bytes()

results = {}
for report in ['result.json','visual-review.json']:
    result = json.loads((Path(__file__).parent/'browser-v2-1'/report).read_text(encoding='utf-8'))
    assert result['result'] == 'PASS'
    for file, expected in result['hashes'].items():
        assert sha(root/base/'prototype'/file) == expected, file+' evidence stale'
    results[report] = {'result': 'PASS', 'checks': len(result['checks']), 'testedAt': result['testedAt']}

artifact_files = ['index.html','app.js','styles.css','visual-v2-1.css','assets/Vazirmatn.ttf',
                  'verify-visual-v2-1.mjs','review-visual-v2-1.mjs','reference-current.html','reference-current.css']
for file in artifact_files:
    relative = base+'prototype/'+file
    assert git(root,'hash-object',relative) == git(root,'rev-parse',artifact+':'+relative), file+' differs from qualified artifact'

output = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'repositoryHeadAtCheck': git(root,'rev-parse','HEAD'),
          'visualArtifactCommit': artifact, 'canonicalHead': git(canonical,'rev-parse','HEAD'),
          'v2Head': git(v2,'rev-parse','HEAD'), 'canonicalClean': True, 'v2Clean': True,
          'runtimeChangedPaths': [], 'preservation': checks, 'historicalBrowserEvidence': 'BYTE_IDENTICAL',
          'sourceAndEvidenceHashesCurrent': True, 'results': results, 'result': 'PASS'}
(Path(__file__).parent/'browser-v2-1/boundaries.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':'PASS','preservedFiles':len(checks),'artifactCommit':artifact}))
