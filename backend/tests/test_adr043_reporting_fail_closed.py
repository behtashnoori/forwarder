"""ADR-043: aggregate, report, and export surfaces have no accepted delegation."""
from backend.tests.test_admin_panel_read_contract import admin_panel_app, _auth_headers


def test_reporting_and_export_surfaces_fail_closed_pending_companion_adr(admin_panel_app):
    client = admin_panel_app["app"].test_client()
    headers = _auth_headers(admin_panel_app["admin_token"])
    for path in (
        "/api/admin/dashboard",
        "/api/admin/reports/assignment-summary",
        "/api/admin/reports/overview?period=weekly",
        "/api/admin/reports/export.xlsx?period=weekly",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 403
        assert "Reporting and export oversight" in response.get_json()["error"]
