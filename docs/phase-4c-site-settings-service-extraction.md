# Phase 4C Site Settings Service Extraction

Date: 2026-05-18

## 1. Scope

Phase 4C is a limited site-settings-only service layer extraction. It moves site settings defaults, settings merge/read/update behavior, upload validation/save helpers, and uploaded-file path/mimetype helpers out of `backend/routes/site_settings.py` into small service modules.

This phase does not change API URLs, HTTP methods, auth/role decorators, response contracts, status codes, frontend code, database models, schema, migrations, CORS/security configuration, upload storage paths, upload filename format, upload size limits, or unrelated backend domains.

## 2. Controlled Risk Note

Phase 3H documented a prior Codex `ENV_BLOCKED` state caused by missing Flask/backend dependencies and a package index/proxy `403 Forbidden` while resolving Flask. In this Phase 4C container, the backend dependency environment is available and `pytest -q` runs successfully.

If a future Codex or review environment re-enters the Phase 3H `ENV_BLOCKED` state, final merge still requires local/CI backend pytest evidence in a valid Python environment.

## 3. Before

Before this refactor, site settings logic lived directly in `backend/routes/site_settings.py`:

- `DEFAULT_SITE_SETTINGS` was declared in the route module.
- `_get_all_settings()` queried `SiteSetting`, merged database values over defaults, and shaped the public/admin settings payload.
- `admin_update_site_settings()` validated the JSON body, filtered allowed keys, coerced values, inserted/updated `SiteSetting`, committed, rolled back on failure, and returned merged settings.
- Upload helpers `_upload_dir()` and `_allowed_file()` plus upload validation, content-size checking, UUID-based logo filename construction, filesystem write, and URL construction lived in the route module.
- `serve_upload()` performed filename safety validation, path resolution, file existence checks, mimetype derivation, and `send_file` response handling in the route module.

Routes reviewed in this phase were limited to `backend/routes/site_settings.py`.

Pre-change checks:

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS_WITH_WARNINGS | 51 passed, 53 existing warnings. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors before changes. |

## 4. Service Design

| Service file | Function | Previous location | Responsibility | Behavior impact |
|---|---|---|---|---|
| `backend/services/settings_service.py` | `get_default_settings()` | `backend/routes/site_settings.py` | Return a copy of editable site setting defaults. | None; default keys/values preserved. |
| `backend/services/settings_service.py` | `merge_settings_with_defaults(stored_settings)` | `_get_all_settings()` in `backend/routes/site_settings.py` | Merge stored values over defaults while preserving unknown stored keys. | None; merge behavior preserved. |
| `backend/services/settings_service.py` | `get_public_settings()` | `_get_all_settings()` in `backend/routes/site_settings.py` | Query `SiteSetting` and return merged public settings. | None; public response shape preserved. |
| `backend/services/settings_service.py` | `get_admin_settings()` | `_get_all_settings()` in `backend/routes/site_settings.py` | Return merged settings for the admin form. | None; admin response shape preserved. |
| `backend/services/settings_service.py` | `is_settings_payload(payload)` | `admin_update_site_settings()` | Validate that the update body is an object after existing `request.get_json() or {}` handling. | None; invalid-body 400 behavior preserved. |
| `backend/services/settings_service.py` | `normalize_settings_payload(payload)` | `admin_update_site_settings()` | Filter allowed keys and preserve current string/`None` coercion behavior. | None; unknown keys continue to be ignored. |
| `backend/services/settings_service.py` | `update_settings(payload)` | `admin_update_site_settings()` | Upsert editable settings, commit, and return merged settings. | None; persistence and response preserved. |
| `backend/services/settings_service.py` | `rollback_settings_update()` | `admin_update_site_settings()` | Roll back failed settings update transactions. | None; route error behavior preserved. |
| `backend/services/upload_service.py` | `upload_dir()` | `_upload_dir()` | Resolve/create the instance upload directory. | None; same `current_app.instance_path/uploads` path. |
| `backend/services/upload_service.py` | `allowed_file(filename)` | `_allowed_file()` | Validate upload extension. | None; allowed extensions preserved. |
| `backend/services/upload_service.py` | `save_logo_upload(file)` | `admin_upload_logo()` | Validate selected file, extension, size, generate logo filename, write file, and return URL/error. | None; upload behavior, size limit, filename pattern, and URL shape preserved. |
| `backend/services/upload_service.py` | `is_valid_uploaded_filename(filename)` | `serve_upload()` | Validate uploaded filename against traversal and allowed-character rules. | None; invalid filename behavior preserved. |
| `backend/services/upload_service.py` | `uploaded_file_path(filename)` | `serve_upload()` | Resolve uploaded file path. | None; storage path preserved. |
| `backend/services/upload_service.py` | `uploaded_file_exists(filename)` | `serve_upload()` | Check whether the uploaded file exists on disk. | None; file-not-found behavior preserved. |
| `backend/services/upload_service.py` | `uploaded_file_mime_type(filename)` | `serve_upload()` | Derive mimetype for served files. | None; mimetype behavior preserved. |

## 5. Changes Made

| File | Change summary | Reason | API behavior impact | Risk |
|---|---|---|---|---|
| `backend/services/settings_service.py` | Added settings defaults, merge/read/update helpers, payload normalization, and rollback helper. | Move site settings DB/default orchestration out of the route. | None intended; response contracts and allowed update keys preserved. | Low. |
| `backend/services/upload_service.py` | Added upload directory, extension validation, logo save, served filename validation, file path, and mimetype helpers. | Move upload/serve helper logic out of the route without changing upload behavior. | None intended; upload path, filename format, URL shape, limits, and mimetypes preserved. | Low/Medium because filesystem behavior is user-visible. |
| `backend/routes/site_settings.py` | Replaced inline defaults/DB/upload/serve helper logic with service calls while preserving request parsing, decorators, `jsonify`, status codes, `send_file`, and error messages. | Keep routes focused on request handling and response conversion. | None intended. | Low/Medium. |
| `docs/phase-4c-site-settings-service-extraction.md` | Added this implementation record. | Document scope, controlled risk, design, contract preservation, checks, and deferred items. | Documentation only. | Low. |

## 6. Endpoint Contract Preservation

| Endpoint | Method | Auth/role preserved? | Response shape preserved? | Upload behavior preserved? | Notes |
|---|---|---:|---:|---:|---|
| `/api/site-settings` | GET | Yes; remains public as before. | Yes. | N/A | Returns the merged flat settings object. |
| `/api/admin/site-settings` | GET | Yes; `@require_role("admin")` unchanged. | Yes. | N/A | Returns the same merged flat settings object for admin forms. |
| `/api/admin/site-settings` | PUT | Yes; `@require_role("admin")` unchanged. | Yes. | N/A | Body handling, unknown-key ignore behavior, value coercion, success response, and error messages/statuses preserved. |
| `/api/admin/upload` | POST | Yes; `@require_role("admin")` unchanged. | Yes. | Yes. | Accepts `file` or `logo`, keeps same allowed extensions, 5 MB limit, generated `logo-<12 hex>.<ext>` filename, and `/api/uploads/<filename>` URL. |
| `/api/uploads/<filename>` | GET | Yes; remains public as before. | Yes. | Yes. | Filename validation, file-not-found response, mimetype derivation, and `send_file` behavior preserved. |

## 7. After

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | PASS_WITH_WARNINGS | 51 passed, 53 existing warnings. |
| `pytest backend/tests/test_security_config.py -q` | PASS_WITH_WARNINGS | 7 passed, 9 existing warnings. |
| Site-settings-specific backend tests | NOT_RUN | No dedicated site settings test file was present. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; 17 existing warnings. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | Canonical migration structure check passed. |
| `git diff --check` | PASS | No whitespace errors. |

## 8. Deferred Items

- CRM service extraction.
- Shipment service extraction.
- Expert console service extraction.
- General repository layer.
- Model split.
- Frontend feature refactor.
- Existing lint warnings.
- CI/CD.
- OpenAPI documentation.
