"""Bind completed checks to the exact clean Product; only write evidence/docs."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path(r'D:\1-webapp\forwarder-dev\phase3-p3-11-explainable-eta')
OUT = ROOT.parent / 'p311-qualification-c0e35a7-20260926'
PRODUCT = 'c0e35a7845f9749ec574a3e29ed5ec81ada87979'
DEST = ROOT / 'docs/operational/evidence/phase3-p3-11-resume-20260926'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf-8').strip()

assert git('rev-parse', 'HEAD') == PRODUCT and not git('status', '--porcelain')
backend = read(OUT / 'backend/result.json')
frontend = read(OUT / 'frontend/result.json')
static = read(OUT / 'static/result.json')
runtime = read(OUT / 'owned-runtime/result.json')
assert backend['status'] == frontend['status'] == 'PASS'
front_report = read(OUT / 'frontend/vitest.json')
assert front_report['numTotalTests'] == front_report['numPassedTests'] == 446
assert front_report['numFailedTests'] == 0 and len(front_report['testResults']) == 93
assert backend['product_sha'] == frontend['product_sha'] == runtime['product_sha'] == PRODUCT
assert backend['source_unchanged'] and frontend['source_unchanged'] and not runtime['dirty_source']
assert backend['expected_collected_tests'] == backend['executed_testcases'] == 1680
assert backend['counts']['passed'] == 1559 and backend['counts']['failed'] == 0
assert len(static) == 9 and all(r['status'] == 'PASS' and r['product_sha'] == PRODUCT for r in static)
expected = {'PostgreSQL 18', 'P3-01 through P3-05 PostgreSQL', 'Public Tracking PostgreSQL',
            *[f'{n} Chrome' for n in ['P311', 'P313', 'P312', 'P310', 'P309', 'P303', 'P301', 'P308', 'P307', 'P306', 'MT3']]}
assert {r['name'] for r in runtime['results']} == expected
assert all(r['status'] == 'PASS' for r in runtime['results']) and runtime['stopped']
assert runtime['schema'] == '20261012_phase3_cargo_eta'
assert not Path(runtime['runtime']).exists(), 'Record any actual cleanup exception explicitly before collecting'
visual = read(OUT / 'visual-qa.json')
assert visual['product_sha'] == PRODUCT and visual['status'] == 'PASS'

counts = {}
for path in (OUT / 'owned-runtime').glob('*browser.log'):
    matches = re.findall(r'(\d+) passed', path.read_text(encoding='utf-8-sig'))
    assert matches, path
    counts[path.name.removesuffix('-browser.log')] = int(matches[-1])
assert counts['P311'] == 3 and len(counts) == 11
pg_counts = {}
for name in ['postgresql.log', 'postgresql-regressions.log', 'postgresql-public.log']:
    matches = re.findall(r'(\d+) passed', (OUT / 'owned-runtime' / name).read_text(encoding='utf-8-sig'))
    assert matches, name
    pg_counts[name] = int(matches[-1])

summary = {'product_sha': PRODUCT, 'status': 'PASS', 'backend': backend['counts'],
    'backend_discovered_and_executed': 1680, 'frontend_passed': 446, 'frontend_files': 93,
    'static_gates': 9, 'chrome': counts, 'postgresql': pg_counts,
    'alembic_head': runtime['schema'], 'alembic_head_count': 1,
    'global_product_validation': 'EVIDENCE_PENDING', 'integrated_product_journeys': 'NOT_RUN',
    'human_product_walkthrough': 'NOT_RUN', 'release_ready': False,
    'p3_14_started': False, 'p3_15_started': False, 'production_accessed': False,
    'production_mutated': False, 'deployment_performed': False, 'release_created': False}
(OUT / 'qualification-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
reconciliation = read(OUT / 'reconciliation-draft.json')
reconciliation['qualification_status'] = 'PASS'
reconciliation['product_authority_reconciliation_status'] = 'PASS'
reconciliation['reference_reconciliation'] = 'PASS'
reconciliation['reference_impact'] = 'NONE'
reconciliation['final_source_frontend_initial_attempt'] = 'Earlier 9aa3321 only: timeouts retained; unchanged source passed after PG stopped. All 446 tests passed again on final c0e35a7.'
for item in reconciliation['product_authority_reconciliation']:
    if 'evidence' in item:
        item['evidence'] = 'source-integrity.json and completed full exact-source regression results'
(OUT / 'reconciliation.json').write_text(json.dumps(reconciliation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

# Preserve evidence bytes across Windows/Linux checkouts; hashes bind raw outputs.
(DEST / '.gitattributes').write_text('# Keep raw evidence bytes; recognize Windows CRLF as line endings.\n* -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n# Raw tool logs retain their emitted spaces and final blank lines.\n*.log -whitespace\n', encoding='utf-8')
for directory in ['backend', 'frontend', 'static', 'owned-runtime', 'prior-attempts']:
    shutil.copytree(OUT / directory, DEST / directory, dirs_exist_ok=True)
for name in ['source-integrity.json', 'toolchain.json', 'test-coverage-summary.json', 'qualification-summary.json', 'reconciliation.json', 'visual-qa.json', 'cleanup-summary.json']:
    shutil.copyfile(OUT / name, DEST / name)
harnesses = DEST / 'harnesses'
harnesses.mkdir(exist_ok=True)
for name in ['run-owned-backend-partitions.py', 'p311-run-final-static.ps1', 'p311-run-final-frontend.ps1', 'p311-collect-final-evidence.py', 'p311-finalize-coverage.py']:
    shutil.copyfile(ROOT.parent / name, harnesses / name)
# Normalize an extra terminal blank line in the replay wrapper, not raw logs.
wrapper = harnesses / 'p311-run-final-static.ps1'
wrapper.write_bytes(wrapper.read_bytes().rstrip(b'\r\n') + b'\n')
manifest = {'product_sha': PRODUCT, 'files': {p.relative_to(DEST).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted(DEST.rglob('*')) if p.is_file() and p.name != 'manifest.json'}}
(DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary))
