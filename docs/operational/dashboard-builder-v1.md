# Personal Dashboard Builder v1

## Purpose

The Builder edits an owner-accessible, active personal dashboard through `/dashboards/:public_id/edit`. System dashboards remain source-controlled and clone-only. Archived, foreign, and unsupported-version dashboards are not editable.

## Architecture

React Query owns the persisted dashboard and semantic registry. A local reducer owns the unsaved name, description, definition, selection, validation, dirty, saving, error, and conflict states. Opening a panel or selecting a widget never makes the draft dirty.

Preview passes the validated local `DashboardDefinition` to the same dashboard runtime used by the System Control Tower and persisted personal dashboards. It does not save or create a revision. Invalid definitions do not reach the analytics execution path.

The semantic registry supplies executable metrics and compatible dimensions, time roles, time grains, and filters. The Builder does not contain a second metric catalog. Both the frontend validator and backend validator remain enforcement boundaries; the server is authoritative.

Save is explicit and sends one PATCH with `expected_version`. A successful response replaces the local baseline and becomes the React Query cache authority. Validation and network failures retain the draft. A 409 enters an explicit conflict state and never retries or overwrites automatically.

## Interaction and accessibility

The surface is intentionally small: name and description, add/configure/remove, keyboard-operable earlier/later ordering, discrete responsive sizes, global-filter selection, preview, save, and cancel. The existing accessible sheet supplies focus management. Fields have labels and async/validation states are announced. Dirty drafts are protected on cancel and browser unload.

## Non-goals

There is no autosave, organization dashboard, sharing, saved view, report/formula/SQL/theme/map/AI builder, scheduled export, custom metric, or cross-tenant copy in v1.
