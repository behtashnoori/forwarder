from pathlib import Path
import json
import xml.etree.ElementTree as ET

out = Path(r'D:\1-webapp\forwarder-dev\p311-qualification-c0e35a7-20260926')
product = 'c0e35a7845f9749ec574a3e29ed5ec81ada87979'
backend = json.loads((out / 'backend/result.json').read_text(encoding='utf-8-sig'))
assert backend['status'] == 'PASS' and backend['product_sha'] == product
cases = [c for p in sorted((out / 'backend').glob('group-*/junit.xml')) for c in ET.parse(p).iter('testcase')]
assert len(cases) == 1680
assert len({(c.get('classname'), c.get('name')) for c in cases}) == 1680
assert not any(c.find('failure') is not None or c.find('error') is not None for c in cases)
report = {}
expected = dict(phase3_eta=24, phase3_branched_route=6, phase3_reported_facts=21,
    phase3_customer_shipment=16, phase3_route_time=15, phase3_closure=24,
    phase3_owner_transfer=21, operational_workspace=16, control_tower=185)
for name, count in expected.items():
    matched = [c for c in cases if name in c.get('classname', '')]
    report[name] = dict(passed=sum(c.find('skipped') is None for c in matched),
        optional_skipped=sum(c.find('skipped') is not None for c in matched))
    assert report[name]['passed'] == count, (name, report[name])
report['eta_cases'] = [c.get('name') for c in cases if c.get('classname') == 'backend.tests.test_phase3_eta']
assert len(report['eta_cases']) == 24
frontend = json.loads((out / 'frontend/vitest.json').read_text(encoding='utf-8-sig'))
report.update(product_sha=product, frontend_total=frontend['numTotalTests'],
    frontend_passed=frontend['numPassedTests'], frontend_eta_cases=[a['fullName']
    for t in frontend['testResults'] if t['name'].endswith('CargoEta.test.tsx') for a in t['assertionResults']])
assert len(report['frontend_eta_cases']) == 5
(out / 'test-coverage-summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if not isinstance(v,list)}))
