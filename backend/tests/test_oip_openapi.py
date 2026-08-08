"""Exact OIP runtime/OpenAPI parity and normative contract assertions."""
import re
from pathlib import Path

from backend import create_app

OPENAPI=Path(__file__).resolve().parents[2]/"docs"/"openapi"/"openapi.yaml"

def test_oip_openapi_exact_runtime_parity_and_contract():
    text=OPENAPI.read_text(encoding="utf-8");documented={};current=None
    for line in text.splitlines():
        if re.match(r"^  /api/",line) and not line.startswith("  /api/oip"):
            current=None
        match=re.match(r"^  (/api/oip[^:]*):\s*$",line)
        if match: current=match.group(1);documented[current]=set();continue
        method=re.match(r"^    (get|post|patch|put|delete):",line)
        if current and method: documented[current].add(method.group(1).upper())
    app=create_app({"TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:"})
    runtime={}
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith("oip."):
            path=re.sub(r"<(?:(?:string|uuid):)?([^>]+)>",r"{\1}",str(rule));runtime[path]=set(rule.methods)-{"HEAD","OPTIONS"}
    assert documented==runtime
    for required in ("Opaque Situation public ID","expected_version","ACTION_GAP","Recommendation","DecisionContext","freshness","projection version","INACTIVE_UNCONFIGURED","OPEN, ACKNOWLEDGED, IN_PROGRESS, SNOOZED, RESOLVED, DISMISSED, and EXPIRED"):
        assert required in text
