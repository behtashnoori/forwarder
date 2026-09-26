from pathlib import Path
import hashlib
import json
import shutil

base = Path('D:/1-webapp/forwarder-dev')
final = base / 'p313-qualification-c091490-20260926'
dest = final / 'preliminary'
paths = [base / name for name in (
    'p313-owner-unit-first.log','p313-owner-unit-second.log',
    'p313-owner-unit-expanded.log','p313-owner-unit-expanded-2.log',
    'p313-final-backend-focused.log','p313-authority-regression.log',
    'p313-frontend-focused.log','p313-frontend-full-preliminary.log',
    'p313-frontend-focused-2.log','p313-typescript-app.log','p313-openapi-order-focused.log')]
for folder in ('p313-pg-probe-1-20260926','p313-pg-probe-2-20260926','p313-pg-probe-3-20260926',
    'p313-pg-regressions-preliminary-20260926','p313-browser-probe-1-20260926',
    'p313-browser-regressions-preliminary-20260926','p313-static-preliminary-20260926'):
    directory = base / folder
    assert directory.is_dir()
    paths.extend(path for path in directory.iterdir() if path.is_file() and
        (path.name in {'result.json','postgres-stop.log'} or path.name.startswith('postgresql') or
         path.name.endswith('-browser.log') or folder == 'p313-static-preliminary-20260926'))
previous = base / 'p313-qualification-212d01f-20260926'
paths.extend(previous / name for name in ('source-identity.json','frontend-result.json','frontend-full.log',
    'visual-review.md','backend-full/result.json','backend-full/plan.json','backend-full/collection.log',
    'backend-full/cleanup.json','static/result.json','owned-runtime/result.json',
    'owned-runtime/postgresql.log','owned-runtime/postgresql-regressions.log',
    'owned-runtime/postgresql-public.log','owned-runtime/postgres-stop.log'))
paths.extend(path for path in (previous / 'backend-full').glob('group-*/*') if path.is_file())
paths.extend((previous / 'owned-runtime').glob('*-browser.log'))
manifest = []
for path in paths:
    assert path.is_file(), path
    relative = path.relative_to(base)
    target = dest / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    manifest.append({'original_path':str(path),'retained_path':str(target.relative_to(final)).replace('\\','/'),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'final_qualification':False})
attempts = {
    'scope':'Preliminary dirty-source diagnosis only; final Product is c0914906af6675c016d5b77d51ecc8a0c05c0b72.',
    'failures_retained':[
        'First owner unit run had 16 failures from the fixture calling nonexistent create_shipment instead of existing create_direct; corrected fixture then 16 passed. Expanded run had four fixture/schema failures: SLA actor context/process name, closure field, empty Tower attention fixture and YAML anchor collision; corrected without weakening authority, then 21 passed.',
        'PG probe 1 startup create_all conflicted with historical schema; skip_startup=True restored exclusive migration ownership.',
        'Focused/full frontend exposed retry-test interaction and old current-owner wording assertion; fixed. An unchanged NewOperation 1-second selector wait failed under concurrent load, then passed focused and final full runs without source/assertion/timeout change.',
        'First browser Customer screenshot captured loading; final browser waits for actual own-Cargo content.',
        'Early smoke selected inherited local test DB and DDL failed/rolled back before seed; environment note preserved in Product entry evidence.'
    ],
    'successes_not_substituted_for_final':[
        'Expanded owner unit 21 passed; authority subset 32 passed; broader backend subset 59 passed.',
        'Focused frontend rerun 62 passed; app/node types, lint/build preliminary passed.',
        'Owned PG probes 2/3 passed; preliminary PG regressions 14 passed.',
        'Preliminary browser regressions 15 passed, captured old dirty HEAD; source changed during that run, so not final Product evidence.'
    ],
    'previous_exact_source':{
        'product_sha':'212d01fa19979e520f8ba9d4a5b4cefd9248cb9e',
        'status':'FAILED_QUALIFICATION_NOT_INTEGRATED',
        'backend':'1534 passed, 120 skipped, one ProjectConfiguration OpenAPI text-range failure; all 1655 cases executed.',
        'other_gates':'441 frontend / 14 PostgreSQL / 15 Chrome / nine static gates passed, but this source is not final PASS.',
        'correction':'Move the owner-transfer schema block before ProjectConfigurationPage; parsed YAML equality verified; no runtime/test/assertion change. Focused 22 tests passed.',
        'cleanup':'Owned PostgreSQL/browser runtime removed. Host automatic approval rejected stopped backend fixture deletion as blocked by policy; exact cleanup.json retained, no deletion retry.'
    },
    'files':manifest
}
(final / 'prior-attempts.json').write_text(json.dumps(attempts, indent=2)+'\n',encoding='utf-8')
harnesses = final / 'harnesses'
harnesses.mkdir(exist_ok=True)
for name in ('run-owned-backend-partitions.py','p313-run-final-frontend.ps1','p313-run-final-static.ps1','p313-retain-preliminary-evidence.py','p313-collect-final-evidence.py'):
    shutil.copyfile(base / name, harnesses / name)
print(f'Retained {len(paths)} preliminary evidence files; no Product source changed.')
