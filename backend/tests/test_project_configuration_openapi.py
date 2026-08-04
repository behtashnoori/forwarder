import re
from pathlib import Path

from backend import create_app


OPENAPI = Path(__file__).resolve().parents[2] / "docs" / "openapi" / "openapi.yaml"
METHODS = {"get", "post", "patch", "put", "delete"}


def _release_path(path):
    return (
        "/configuration/" in path
        or path.startswith("/api/internal/project-configuration/")
        or path == "/api/internal/milestone-types"
        or path.startswith("/api/admin/milestone-types")
    )


def _documented_routes(text):
    routes, current = {}, None
    for line in text.splitlines():
        path = re.match(r"^  (/api/[^:]+):\s*$", line)
        if path:
            current = path.group(1)
            if _release_path(current):
                routes[current] = set()
            continue
        method = re.match(r"^    (get|post|patch|put|delete):", line)
        if current in routes and method:
            routes[current].add(method.group(1).upper())
    return routes


def _runtime_routes():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    routes = {}
    for rule in app.url_map.iter_rules():
        path = re.sub(r"<(?:(?:string|uuid):)?([^>]+)>", r"{\1}", str(rule))
        if _release_path(path):
            routes[path] = set(rule.methods) - {"HEAD", "OPTIONS"}
    return routes


def test_release_180_openapi_runtime_exact_parity_and_schemas():
    text = OPENAPI.read_text(encoding="utf-8")
    assert re.search(r"^  version: 1\.8\.0$", text, re.MULTILINE)
    documented, runtime = _documented_routes(text), _runtime_routes()
    assert documented == runtime
    required = {
        "ProjectServiceCreate", "ProjectServiceUpdate", "ProjectServiceResponse",
        "ProjectServiceListResponse", "ProjectDocumentRequirementCreate",
        "ProjectDocumentRequirementUpdate", "ProjectDocumentRequirementResponse",
        "ProjectDocumentRequirementListResponse", "ProjectMilestoneDefinitionCreate",
        "ProjectMilestoneDefinitionUpdate", "ProjectMilestoneDefinitionResponse",
        "ProjectMilestoneDefinitionListResponse", "ServiceTypeSelectorItem",
        "DocumentDefinitionSelectorItem", "MilestoneTypeSelectorItem",
        "ProjectLogisticsPointSelectorItem", "SelectorListResponse",
        "ProjectMilestoneReorderRequest", "ProjectMilestoneReorderResponse",
        "ProjectConfigurationPage", "ProjectConfigurationError",
        "ProjectConfigurationValidationError", "ProjectConfigurationConflictError",
        "ProjectConfigurationDuplicateError", "ProjectConfigurationNotFoundError",
        "MilestoneTypeCreate", "MilestoneTypeUpdate",
    }
    schemas = set(re.findall(r"^    ([A-Za-z][A-Za-z0-9]+):\s*$", text, re.MULTILINE))
    assert required <= schemas
    assert "/configuration/{resource}" not in text
    release_schema_text = text[text.index("    ProjectConfigurationPage:"):text.index("paths:")]
    assert "additionalProperties: true" not in release_schema_text
    forbidden = re.compile(r"^\s+(?:id|project_id|service_type_id|document_definition_id|milestone_type_id|project_logistics_point_id):", re.MULTILINE)
    assert not forbidden.search(release_schema_text)
