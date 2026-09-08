"""OpenAPI, Flask routing, and frontend-client parity for the dashboard correction slice."""
from pathlib import Path

import yaml

from backend import create_app


ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "/api/v2/dashboards": {"get"},
    "/api/v2/dashboards/{public_id}": {"get", "patch"},
    "/api/v2/dashboards/system/{system_id}/clone": {"post"},
    "/api/v2/dashboards/{public_id}/archive": {"post"},
    "/api/v2/dashboards/{public_id}/restore": {"post"},
    "/api/v2/saved-views/{public_id}/dashboard-snapshot": {"post"},
    "/api/v2/analytics/semantic-registry": {"get"},
}


def _openapi():
    return yaml.safe_load((ROOT / "docs" / "openapi" / "openapi.yaml").read_text(encoding="utf-8"))


def _flask_path(rule: str) -> str:
    return rule.replace("<string:public_id>", "{public_id}").replace("<string:system_id>", "{system_id}")


def test_corrective_routes_match_checked_in_openapi_methods():
    document = _openapi()
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}, skip_startup=True)
    runtime = {}
    for rule in app.url_map.iter_rules():
        runtime.setdefault(_flask_path(rule.rule), set()).update(
            method.lower() for method in rule.methods - {"HEAD", "OPTIONS"}
        )
    for path, methods in EXPECTED.items():
        assert methods <= set(document["paths"][path])
        assert methods <= runtime[path]


def test_frontend_client_calls_the_same_dashboard_contract():
    client = (ROOT / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    for fragment in (
        '"/api/v2/dashboards"',
        '`/api/v2/dashboards/${encodeURIComponent(publicId)}`',
        '`/api/v2/dashboards/system/${encodeURIComponent(systemId)}/clone`',
        '`/api/v2/dashboards/${encodeURIComponent(publicId)}/archive`',
        '`/api/v2/dashboards/${encodeURIComponent(publicId)}/restore`',
        '`/api/v2/saved-views/${encodeURIComponent(publicId)}/dashboard-snapshot`',
        '"/api/v2/analytics/semantic-registry"',
    ):
        assert fragment in client
