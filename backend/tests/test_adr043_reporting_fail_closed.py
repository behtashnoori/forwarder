"""ADR-043 reporting authority is explicit; ordinary Experts remain denied."""
from backend.tests.test_admin_panel_read_contract import admin_panel_app, _auth_headers


def test_reporting_and_export_surfaces_deny_experts_under_companion_decision(admin_panel_app):
    client = admin_panel_app["app"].test_client()
    headers = _auth_headers(admin_panel_app["expert_token"])
    for path in (
        "/api/admin/dashboard",
        "/api/admin/reports/assignment-summary",
        "/api/admin/reports/overview?period=weekly",
        "/api/admin/reports/export.xlsx?period=weekly",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 403
        assert response.get_json() == {"error": "Management reporting access is not authorized."}
