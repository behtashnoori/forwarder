"""Run the complete backend suite in two disjoint module groups, without plugins.

No assertion, timeout, runtime source, or test is changed. Each subprocess owns
its pytest base directory, and all discovered modules are included exactly once.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
p.add_argument('--workspace', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--product', required=True)
args = p.parse_args()
root = args.workspace.resolve()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=True)
def git(*values):
    return subprocess.check_output(['git', *values], cwd=root, text=True).strip()
assert git('rev-parse','HEAD') == args.product and not git('status','--porcelain')
files = sorted(subprocess.check_output(['rg','--files','backend/tests','-g','test*.py'],cwd=root,text=True).splitlines())
groups = [files[::2], files[1::2]]
assert len(files) == len(set(files)) and sorted(groups[0]+groups[1]) == files
environment = os.environ.copy()
for name in list(environment):
    if 'POSTGRES_URL' in name or name in {'MT3_TEST_DATABASE_URL','E2E_DATABASE_URL'}:
        environment.pop(name)
environment.update(APP_ENV='testing', DATABASE_URL='sqlite:///:memory:', TEST_DATABASE_URL='sqlite:///:memory:',
    SECRET_KEY='owned-partition-test-secret', JWT_SECRET_KEY='owned-partition-jwt-secret',
    PYTHONIOENCODING='utf-8')
collected = subprocess.run([sys.executable,'-m','pytest','backend/tests','--collect-only','-q','--disable-warnings'],
    cwd=root,env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace')
(output/'collection.log').write_text(collected.stdout+'\n'+collected.stderr,encoding='utf-8')
assert collected.returncode == 0
matches = re.findall(r'(\d+) tests? collected', collected.stdout)
assert matches, 'Cannot establish complete collection count'
expected_count = int(matches[-1])
runtime = Path(tempfile.gettempdir()).resolve() / ('forwarder-owned-backend-'+uuid.uuid4().hex)
runtime.mkdir()
plan = {'product_sha':args.product, 'tree':git('show','-s','--format=%T','HEAD'),
    'expected_collected_tests':expected_count, 'runtime':str(runtime), 'groups':groups,
    'module_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
    'environment':'testing; synthetic in-memory DATABASE_URL and TEST_DATABASE_URL; synthetic secrets; owned PostgreSQL opt-ins unset',
    'started_at':datetime.now(timezone.utc).isoformat()}
(output/'plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
children = []
results = []
try:
    for index, modules in enumerate(groups):
        directory = output/f'group-{index+1}'
        directory.mkdir()
        stdout = (directory/'stdout.log').open('w',encoding='utf-8')
        stderr = (directory/'stderr.log').open('w',encoding='utf-8')
        command = [sys.executable,'-u','-m','pytest',*modules,'--disable-warnings','--tb=short',
            '--basetemp',str(runtime/f'group-{index+1}'),'--junitxml',str(directory/'junit.xml')]
        child = subprocess.Popen(command,cwd=root,env=environment,stdout=stdout,stderr=stderr)
        children.append((child,stdout,stderr,directory))
        print(f'Started group {index+1}: {len(modules)} modules; PID {child.pid}',flush=True)
    while any(child.poll() is None for child,*_ in children):
        time.sleep(.5)
    for index,(child,stdout,stderr,directory) in enumerate(children):
        stdout.close(); stderr.close()
        log = (directory/'stdout.log').read_text(encoding='utf-8',errors='replace')
        summary = list(re.finditer(r'=+\s*([^\r\n]+?)\s+in ([\d.]+)s(?: \([^)]+\))?\s*=+',log))
        counts = {}
        if summary:
            counts = {name:int(count) for count,name in re.findall(r'(\d+) (passed|failed|skipped|xfailed|xpassed|warnings?|errors?)',summary[-1].group(1))}
        cases = list(ET.parse(directory/'junit.xml').iter('testcase')) if (directory/'junit.xml').exists() else []
        record = {'group':index+1,'product_sha':args.product,'exit_code':child.returncode,
            'summary':summary[-1].group(1) if summary else None,'counts':counts,'junit_testcases':len(cases),
            'status':'PASS' if child.returncode == 0 and summary and cases else 'FAIL_OR_INCOMPLETE'}
        (directory/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        results.append(record)
        print(json.dumps(record),flush=True)
    total = {name:sum(row['counts'].get(name,0) for row in results) for name in ('passed','failed','skipped','errors','warnings')}
    covered = sum(row['junit_testcases'] for row in results)
    result = {'product_sha':args.product,'status':'PASS' if covered == expected_count and all(row['status']=='PASS' for row in results) else 'FAIL_OR_INCOMPLETE',
        'counts':total,'expected_collected_tests':expected_count,'executed_testcases':covered,
        'groups':results,'source_unchanged':git('rev-parse','HEAD') == args.product and not git('status','--porcelain'),
        'finished_at':datetime.now(timezone.utc).isoformat(),'owned_processes_stopped':True,
        'runtime':str(runtime),'temporary_fixtures_retained':True}
    if not result['source_unchanged']: result['status']='SOURCE_CHANGED'
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)
finally:
    for child,stdout,stderr,directory in children:
        if child.poll() is None:
            child.terminate(); child.wait(timeout=30)
        stdout.close(); stderr.close()
sys.exit(0 if result['status']=='PASS' else 1)
