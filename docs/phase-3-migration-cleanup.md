# Phase 3 Migration Cleanup

Date: 2026-05-18

## 1. Scope

Phase 3 was limited to migration path cleanup and release-safety documentation. No migration was generated, no database model was changed, no schema operation was run, no API behavior was changed, no business logic was changed, and no frontend file was changed.

The only non-migration-path code adjustment was a startup safety fallback in `backend/config.py` so the already-declared `python-dotenv` dependency being absent in this execution environment does not prevent non-destructive checks from running. That change only preserves existing `.env` loading behavior through a tiny local parser when `python-dotenv` is unavailable; it does not change schema, migrations, API behavior, or business logic.

## 2. Before

| Item | Before state |
|---|---|
| Canonical migration path | `backend/migrations` was documented as canonical and contained Alembic config, env, template, and the active version chain. |
| Root migration path | Root `migrations/` still existed with `alembic.ini`, `env.py`, `script.py.mako`, and 7 version files. |
| Structure check warning | `npm run check:structure` warned that root `migrations/versions` contained version files and root `migrations/alembic.ini` existed. |
| Migration ambiguity | Operators could accidentally point Alembic tooling at root `migrations/` instead of canonical `backend/migrations`. |
| `pytest -q` before Phase 3 edits | Initial before command stopped during collection because `python-dotenv` was declared in requirements but absent from this execution environment. This was fixed without adding a dependency or changing migration/schema behavior. |
| Phase 2 quality baseline | Phase 2 recorded `pytest -q`, `npm run lint`, `npm run build`, and `npm run check:structure` passing, with existing lint/build/structure warnings. |

## 3. Migration Inventory

| Path | Revision id | Down revision | Description | Canonical/deprecated | Action |
|---|---|---|---|---|---|
| `backend/migrations/versions/20240917_initial_schema.py` | `20240917_initial_schema` | `None` | Initial schema for shipment request service. | Canonical | Kept in `backend/migrations`. |
| `backend/migrations/versions/20240918_add_shipment_request_log.py` | `20240918_add_shipment_request_log` | `20240917_initial_schema` | Add shipment request log table. | Canonical | Kept in `backend/migrations`. |
| `backend/migrations/versions/20240919_add_code_to_province.py` | `20240919_add_code_to_province` | `20240918_add_shipment_request_log` | Add code column to province. | Canonical | Kept in `backend/migrations`. |
| `backend/migrations/versions/20240920_add_transport_method_to_shipment_request.py` | `20240920_add_transport_method_to_shipment_request` | `20240919_add_code_to_province` | Add transport_method to shipment_request. | Canonical | Kept; supersedes older divergent root copy. |
| `backend/migrations/versions/20240922_make_transport_method_nullable.py` | `20240922_make_transport_method_nullable` | `20240920_add_transport_method_to_shipment_request` | Make transport_method nullable. | Canonical | Kept; supersedes older divergent root copy. |
| `backend/migrations/versions/20240923_add_cargo_details.py` | `20240923_add_cargo_details` | `20240922_make_transport_method_nullable` | Add cargo details to shipment_request. | Canonical | Kept; root copy differed only by trailing blank lines. |
| `backend/migrations/versions/20240924_add_customer_name_fields.py` | `20240924_add_customer_name_fields` | `20240923_add_cargo_details` | Add customer name fields to shipment_request. | Canonical | Kept. |
| `backend/migrations/versions/20240924_add_expert_console_fields.py` | `20240924_add_expert_console_fields` | `20240924_add_customer_name_fields` | Add expert console fields to shipment_request. | Canonical branch | Kept and merged by `20250220_merge_final`. |
| `backend/migrations/versions/20240924_add_expert_console_tables.py` | `20240924_add_expert_console_tables` | `20240924_add_customer_name_fields` | Add expert console tables and fields. | Canonical branch | Kept and merged through canonical chain. |
| `backend/migrations/versions/20240925_add_crm_models.py` | `20240925_add_crm_models` | `20240924_add_expert_console_tables` | Add CRM models. | Canonical | Kept. |
| `backend/migrations/versions/20240925_add_performance_indexes.py` | `20240925_add_performance_indexes` | `20240925_add_crm_models` | Add performance indexes. | Canonical | Kept. |
| `backend/migrations/versions/20240925_add_data_integrity_constraints.py` | `20240925_add_data_integrity_constraints` | `20240925_add_performance_indexes` | Add data integrity constraints. | Canonical | Kept. |
| `backend/migrations/versions/20240925_fix_customer_shipment_relationship.py` | `20240925_fix_customer_shipment_relationship` | `20240925_add_data_integrity_constraints` | Fix customer-shipment relationship. | Canonical | Kept. |
| `backend/migrations/versions/20240926_add_password_to_expert_user.py` | `20240926_add_password_to_expert_user` | `20240925_fix_customer_shipment_relationship` | Add password to expert user. | Canonical | Kept. |
| `backend/migrations/versions/20250101_add_crm_hierarchy_system.py` | `20250101_add_crm_hierarchy_system` | `20240926_add_password_to_expert_user` | Add CRM hierarchy system. | Canonical | Kept. |
| `backend/migrations/versions/20251006_124249_add_international_shipping_fields.py` | `20251006_124249` | `20250101_add_crm_hierarchy_system` | Add international shipping fields. | Canonical | Kept. |
| `backend/migrations/versions/20250110_add_international_models.py` | `20250110_add_international_models` | `20251006_124249` | Add international shipping models. | Canonical | Kept. |
| `backend/migrations/versions/20250115_add_iran_ports_models.py` | `20250115_add_iran_ports_models` | `20250110_add_international_models` | Add Iran ports and mappings. | Canonical | Kept. |
| `backend/migrations/versions/20250115_add_iran_entry_point_fields.py` | `20250115_add_iran_entry_point_fields` | `20250115_add_iran_ports_models` | Add Iran entry point fields. | Canonical branch | Kept and merged by `20250220_merge_heads`. |
| `backend/migrations/versions/20250120_add_separate_transport_methods.py` | `20250120_add_separate_transport_methods` | `20250115_add_iran_ports_models` | Add separate transport methods. | Canonical branch | Kept. |
| `backend/migrations/versions/20250120_add_customer_gamification_system.py` | `20250120_add_customer_gamification_system` | `20250120_add_separate_transport_methods` | Add customer gamification system. | Canonical | Kept. |
| `backend/migrations/versions/20250220_add_tracking_code_to_shipment_request.py` | `20250220_add_tracking_code` | `20250120_add_customer_gamification_system` | Add public tracking code. | Canonical branch | Kept and merged by `20250220_merge_heads`. |
| `backend/migrations/versions/20250220_merge_heads.py` | `20250220_merge_heads` | `20250220_add_tracking_code`, `20250115_add_iran_entry_point_fields` | Merge tracking and Iran entry branches. | Canonical merge | Kept. |
| `backend/migrations/versions/20250220_merge_final_heads.py` | `20250220_merge_final` | `20250220_merge_heads`, `20240924_add_expert_console_fields` | Merge final heads. | Canonical merge | Kept. |
| `backend/migrations/versions/20250221_add_referral_rule_tables.py` | `20250221_referral` | `20250220_merge_final` | Add referral rule/state/log tables. | Canonical | Kept. |
| `backend/migrations/versions/20250221_auto_assign_state_and_nullable_rule.py` | `20250221_auto` | `20250221_referral` | Add auto-assign state and nullable referral rule. | Canonical | Kept. |
| `backend/migrations/versions/20250221_add_site_setting.py` | `20250221_site` | `20250221_auto` | Add site_setting table. | Canonical | Kept. |
| `backend/migrations/versions/20250223_add_expert_quote.py` | `20250223_quote` | `20250221_site` | Add expert_quote table. | Canonical | Kept. |
| `backend/migrations/versions/20250223_fix_expert_quote_autoincrement.py` | `20250223_quote_fix` | `20250223_quote` | Fix expert_quote id autoincrement. | Canonical | Kept. |
| `backend/migrations/versions/20250223_ensure_expert_quote_table.py` | `20250223_ensure_quote` | `20250223_quote_fix` | Ensure expert_quote table exists idempotently. | Canonical head | Kept. |
| `migrations/versions/20240917_initial_schema.py` | `20240917_initial_schema` | `None` | Initial schema for shipment request service. | Deprecated root | Archived as exact duplicate. |
| `migrations/versions/20240918_add_shipment_request_log.py` | `20240918_add_shipment_request_log` | `20240917_initial_schema` | Add shipment request log table. | Deprecated root | Archived as exact duplicate. |
| `migrations/versions/20240919_add_code_to_province.py` | `20240919_add_code_to_province` | `20240918_add_shipment_request_log` | Add code column to province. | Deprecated root | Archived as exact duplicate. |
| `migrations/versions/20240920_add_transport_method_to_shipment_request.py` | `20240920_add_transport_method_to_shipment_request` | `20240919_add_code_to_province` | Add transport_method to shipment_request. | Deprecated divergent root | Archived; canonical backend copy supersedes it. |
| `migrations/versions/20240922_make_transport_method_nullable.py` | `20240922_make_transport_method_nullable` | `20240920_add_transport_method_to_shipment_request` | Make transport_method nullable. | Deprecated divergent root | Archived; canonical backend copy supersedes it. |
| `migrations/versions/20240923_add_cargo_details.py` | `20240923_add_cargo_details` | `20240922_make_transport_method_nullable` | Add cargo details to shipment_request. | Deprecated near-duplicate root | Archived; canonical backend copy supersedes it. |
| `migrations/versions/54ea21ea0d9f_add_transport_method_columns.py` | `54ea21ea0d9f` | `20240923_add_cargo_details` | add_transport_method_columns. | Deprecated root-only | Archived, not deleted; broad autogenerated operations are retained for history/DBA review but removed from executable migration path. |

## 4. Decision

- Final canonical migration path: `backend/migrations`.
- Root `migrations/` was removed from the executable project root path.
- The root migration files were not deleted; they were archived under `docs/migrations-archive/root-migrations-2026-05-18/` for historical review.
- This is safe because application startup and migration helpers already use `backend/migrations`, the canonical graph has 30 revisions, one base, one head (`20250223_ensure_quote`), and no missing `down_revision` references in the non-destructive graph check.
- Migration drift from duplicate executable migration roots is resolved because only `backend/migrations` remains in an executable Alembic location.
- A residual operational risk remains only if an existing production database has `alembic_version = 54ea21ea0d9f`; that root-only revision is archived for manual DBA review rather than discarded.

## 5. Changes Made

| File/path | Change summary | Reason | Schema impact | Risk | Notes |
|---|---|---|---|---|---|
| `migrations/` | Removed root executable migration directory by moving its files to archive. | Eliminate accidental use of deprecated Alembic path. | None. | Low; files preserved in docs archive. | No DB command was run. |
| `docs/migrations-archive/root-migrations-2026-05-18/` | Added archived copy of former root `migrations/`. | Preserve migration history and unique root-only revision for review. | None. | Low; non-executable documentation/archive path. | Do not use as Alembic script location. |
| `docs/migrations-archive/root-migrations-2026-05-18/README.md` | Documented archive purpose and root-only revision warning. | Avoid future confusion. | None. | Low. | Explicitly states canonical path. |
| `backend/config.py` | Added no-dependency `.env` parser fallback when `python-dotenv` is unavailable. | Allow non-destructive checks to run in environments missing an already-declared dependency. | None. | Low; same env-file precedence and override behavior. | No secret values are printed. |
| `docs/phase-3-migration-cleanup.md` | Added this Phase 3 record. | Document inventory, decision, checks, and remaining risks. | None. | Low. | No schema/model/API change. |

## 6. After

| Check | Result | Notes |
|---|---:|---|
| `pytest -q` | NOT_RUN_ENV | Blocked during collection because Flask is not installed in this execution environment; `python -m pip install Flask>=3.0,<4.0` could not reach the package index due 403 responses. |
| `npm run lint` | PASS_WITH_WARNINGS | 0 errors; existing 17 warnings remain. |
| `npm run build` | PASS_WITH_WARNINGS | Build passed; existing Browserslist/chunk-size warnings remain. |
| `npm run check:structure` | PASS | No root migration warnings after archive. |
| `python -m alembic -c migrations/alembic.ini heads` from `backend/` | NOT_RUN_ENV | Alembic is declared in requirements but unavailable in this execution environment. No DB connection or migration upgrade was attempted. |
| Custom read-only migration graph check | PASS | Parsed `backend/migrations/versions`: 30 revisions, one base, one head `20250223_ensure_quote`, no missing down-revision references. No DB connection used. |
| `git diff --check` | PASS | No whitespace errors. |

## 7. Remaining Risks

- Python backend dependency installation is incomplete in this execution environment (`Flask` and `alembic` unavailable), so `pytest -q` and Alembic CLI status could not complete here.
- Production DB state is unknown because no live database connection or upgrade/status command was run.
- If a production database was ever stamped with deprecated root-only revision `54ea21ea0d9f`, manual DBA review is required before any migration operation; the file is preserved in the archive for that review.
- Existing startup migration recovery logic remains outside Phase 3 scope and should be reviewed in a later release-safety phase.

## 8. Deferred Items

The following are intentionally deferred to Phase 4 or later:

- Backend domain refactor.
- Backend service layer extraction.
- Frontend feature-based refactor.
- Existing lint warnings.
- CI/CD migration safety checks.
- Production deployment hardening beyond the completed config/security basics.
- OpenAPI documentation.
