# Phase 13C: Request Form UX Cleanup

## 1. Scope
This phase improves the public request form UX only. The changes focus on dropdown readability, transport-method clarity, optional province-first details, optional cargo guidance, and date-field clarity.

## 2. Customer Feedback Addressed
- Dropdown consistency: select triggers and option lists now have better RTL alignment, wrapping, and readable option height.
- Transport method clarity: domestic and international choices remain separated by request type, with clearer visible Persian labels and helper text.
- Province-first details clarity: province-only domestic submission remains supported, and county/city details are described as optional.
- Optional cargo details: cargo fields remain optional, with clearer helper text that explains unknown values can be left blank.
- Date field clarity: date fields remain optional, use the browser date input, and explain the Jalali picker limitation.
- Domestic/international readability: helper copy is more service-oriented and less technical.

## 3. Changes Made
- `src/components/LocationForm.tsx`: added local copy helpers, clarified transport method helper text, clarified optional province details, improved cargo/date helper text, and preserved Phase 13B success actions.
- `src/components/ui/select.tsx`: adjusted the shared select primitive used by the request form so selected values and dropdown options are more readable in RTL and less likely to clip.

## 4. Behavior Preservation
- Backend unchanged.
- API payload shape unchanged.
- Domestic submission preserved.
- International submission preserved.
- Province-only submission preserved.
- Full-detail submission preserved.
- Cargo optional submission preserved.
- Success/tracking/new-request/home actions preserved.

## 5. Date Handling Decision
The date submission format was not changed. The form continues to use native `type="date"` inputs, which submit the existing browser date format expected by the current frontend payload. No Jalali date-picker dependency was added in this phase. A Jalali date picker for domestic requests is deferred to a later phase.

## 6. Non-goals
- No backend change.
- No calendar dependency added.
- No notification implementation.
- No SLA.
- No priority.
- No AdminPanel or ExpertConsole changes.
- No report/export changes.

## 7. Verification
- `npm.cmd run lint`: passed with existing unrelated warnings in shared UI/context files and `UserManagement`.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
- `git -c safe.directory=D:/Projects/webapp/15-forwarder/forwarder diff --check`: passed. Git reported only line-ending normalization warnings.
- Smoke checks: local dev server served the landing page with HTTP 200. Full manual browser interaction checks were limited in this sandbox.
