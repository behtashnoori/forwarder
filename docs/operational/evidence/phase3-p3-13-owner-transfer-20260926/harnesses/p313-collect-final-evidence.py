"""Bind P3-13 evidence to a clean immutable Product, after all gates complete."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

root = Path('D:/1-webapp/forwarder-dev/phase3-p3-13-owner-transfer')
source = Path('D:/1-webapp/forwarder-dev/p313-qualification-c091490-20260926')
target = root / 'docs/operational/evidence/phase3-p3-13-owner-transfer-20260926'
product = 'c0914906af6675c016d5b77d51ecc8a0c05c0b72'

def read(relative):
    return json.loads((source / relative).read_text(encoding='utf-8-sig'))

identity = read('source-identity.json')
frontend = read('frontend-result.json')
backend = read('backend-full/result.json')
cleanup = read('backend-full/cleanup.json')
static = read('static/result.json')
owned = read('owned-runtime/result.json')
assert identity['product_sha'] == product and identity['clean']
assert frontend['product_sha'] == backend['product_sha'] == owned['product_sha'] == product
assert frontend['status'] == backend['status'] == 'PASS'
assert frontend['source_unchanged'] and backend['source_unchanged'] and backend['owned_processes_stopped']
frontend_log = (source / 'frontend-full.log').read_text(encoding='utf-8-sig')
assert re.search(r'Test Files\s+92 passed \(92\)', frontend_log)
assert re.search(r'Tests\s+441 passed \(441\)', frontend_log)
assert backend['executed_testcases'] == backend['expected_collected_tests'] == 1655
assert backend['counts']['passed'] == 1535 and backend['counts']['skipped'] == 120
assert backend['counts']['failed'] == backend['counts']['errors'] == 0
assert cleanup['product_sha'] == product and cleanup['owned_processes_stopped']
assert cleanup['processes_absent_verified'] and cleanup['listeners_absent_verified']
assert (cleanup['runtime_removed'] and not Path(backend['runtime']).exists()) or (
    cleanup['retained_due_to_policy_rejection'] and Path(backend['runtime']).is_dir())
assert len(static) == 9 and all(row['status'] == 'PASS' and row['product_sha'] == product for row in static)
assert owned['schema'] == '20261011_phase3_owner_transfer' and not owned['dirty_source']
assert owned['stopped'] and not owned['production_accessed'] and not Path(owned['runtime']).exists()
expected = {'PostgreSQL 18', 'P3-01 through P3-05 PostgreSQL', 'Public Tracking PostgreSQL',
    *[f'{name} Chrome' for name in ('P313','P312','P310','P309','P303','P301','P308','P307','P306','MT3')]}
assert {row['name'] for row in owned['results']} == expected
assert all(row['status'] == 'PASS' for row in owned['results'])
assert subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip() == product
assert not subprocess.check_output(['git','status','--porcelain'], cwd=root, text=True).strip()

def passed(relative):
    matches = re.findall(r'(\d+) passed', (source / relative).read_text(encoding='utf-8-sig'))
    assert matches, relative
    return int(matches[-1])

pg_count = sum(passed(f'owned-runtime/{name}') for name in
    ('postgresql.log','postgresql-regressions.log','postgresql-public.log'))
browser_count = sum(passed(path.relative_to(source)) for path in (source / 'owned-runtime').glob('*-browser.log'))
assert (pg_count, browser_count) == (14, 15)
identity['final_status'] = 'PASS'
(source / 'source-identity.json').write_text(json.dumps(identity, indent=2)+'\n', encoding='utf-8')

selected = [Path(name) for name in ('source-identity.json','frontend-result.json','frontend-full.log',
    'prior-attempts.json','visual-review.md','contract-order-proof.json','backend-full/result.json','backend-full/plan.json',
    'backend-full/collection.log','backend-full/cleanup.json','owned-runtime/result.json',
    'owned-runtime/postgresql.log','owned-runtime/postgresql-regressions.log',
    'owned-runtime/postgresql-public.log','owned-runtime/postgres-stop.log',
    'owned-runtime/P313-runtime-identity.json')]
selected += [path.relative_to(source) for path in (source / 'backend-full').glob('group-*/*') if path.is_file()]
selected += [path.relative_to(source) for path in (source / 'static').iterdir() if path.is_file()]
selected += [path.relative_to(source) for path in (source / 'owned-runtime').glob('*-browser.log')]
selected += [path.relative_to(source) for path in (source / 'owned-runtime/P313-browser').rglob('*.png')]
selected += [path.relative_to(source) for path in (source / 'preliminary').rglob('*') if path.is_file()]
selected += [path.relative_to(source) for path in (source / 'harnesses').iterdir() if path.is_file()]
assert len(selected) == len(set(selected))
manifest = []
for relative in selected:
    origin, dest = source / relative, target / relative
    data = origin.read_bytes()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(origin, dest)
    manifest.append({'path':relative.as_posix(), 'sha256':hashlib.sha256(data).hexdigest(), 'bytes':len(data)})
(target / '.gitattributes').write_text('** -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n*.log -diff\n*.xml -diff\n', encoding='utf-8')
summary = {'product_sha':product, 'product_tree':identity['product_tree'], 'status':'PASS',
    'backend':backend, 'frontend_tests':441, 'frontend_files':92, 'postgresql_tests':pg_count,
    'chrome_tests':browser_count, 'static_gates':9, 'migration':'20261011_phase3_owner_transfer',
    'parent_migration':'20261010_phase3_closure', 'postgresql_browser_runtimes_removed':True,
    'backend_fixture_cleanup':cleanup, 'global_product_validation':'EVIDENCE_PENDING',
    'integrated_product_journeys':'NOT_RUN', 'human_product_walkthrough':'NOT_RUN',
    'release_ready':False, 'production_accessed':False, 'selected_evidence':manifest,
    'raw_evidence_directory':str(source)}
(target / 'qualification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({key:value for key,value in summary.items() if key not in {'selected_evidence','backend'}}, indent=2))
