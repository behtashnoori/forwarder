# Forwarder v1.9.1 Slice 6.2 final browser acceptance

## Final result

`PRODUCT DEFECT REMAINS — SLICE 7 NO-GO`

Run `P1B-UAT-20260810191536339078` passed the controlled PostgreSQL 18,
backend, frontend, and Chromium baseline at application commit `fdd7005`.
All runtime processes and the disposable database were cleaned up. Production
was untouched.

## Environment

- Branch: `codex/pr-4a-dms-gate-repair`
- Application commit: `fdd700542f4a6765116608fc6c282bae8211bd0e`
- PostgreSQL: 18, private loopback cluster on port 55459
- Backend/frontend: loopback ports 57089 / 5201
- Migration current/head: `20260819_v191_acceptance_corrections`
- Python: 3.13
- Node: 24.11.0
- Playwright: 1.57.0
- Chromium: Playwright Chromium bundle 1200
- Personas: direct-only, explicit quote-only, legacy quote, combined, neither,
  and admin/support

## Required acceptance matrix

| Mandatory item | Result | Evidence / concrete defect |
|---|---|---|
| Persian localization | FAIL | New Operation and shipment list were corrected, but `OperationalWorkQueue` and portions of `OperationalShipmentDetail` still render hardcoded English in Persian mode. Reproduce by setting `forwarder.language=fa` and opening `/operations/work-queue` or an operation detail. Category 2 PRESENTATION/I18N. |
| Required/error semantics | PASS | Frontend regression verifies required canonical Customer, route, schedule and Iran Province semantics, associated field errors, `aria-invalid`, `aria-describedby`, and first-invalid focus. |
| Accepted-quote Chromium creation | FAIL | The retained Chromium runner still creates the quote-derived operation through HTTP rather than the form. This is a concrete Category 1 HARNESS/FIXTURE defect in `v191_slice6_browser_runner.mjs`. |
| Request Detail deep-link: normal | FAIL | No Chromium assertion enters New Operation from Request Detail. Category 1 HARNESS/FIXTURE defect. |
| Request Detail deep-link: refresh | FAIL | No refresh/history assertion exists in the runner. Category 1 HARNESS/FIXTURE defect. |
| Request Detail deep-link: back/forward | FAIL | No browser-history assertion exists in the runner. Category 1 HARNESS/FIXTURE defect. |
| Request Detail deep-link: stale | FAIL | Existing stale conversion proof is HTTP-only. Category 1 HARNESS/FIXTURE defect. |
| Domestic origin | PASS | Chromium direct creation selected a canonical Province and completed a detail round trip. |
| Domestic destination | PASS | Chromium direct creation selected a canonical Province and completed a detail round trip. |
| International origin non-Iran | FAIL | Missing deterministic Chromium assertion/payload capture. Category 1 HARNESS/FIXTURE defect. |
| International origin Iran | FAIL | Unit regression passes; mandatory Chromium negative/round-trip assertion is absent. Category 1 HARNESS/FIXTURE defect. |
| International destination non-Iran | FAIL | Missing deterministic Chromium assertion/payload capture. Category 1 HARNESS/FIXTURE defect. |
| International destination Iran city | FAIL | Missing independent Chromium create/round-trip. Category 1 HARNESS/FIXTURE defect. |
| International destination Iran port | FAIL | Missing independent Chromium create/round-trip. Category 1 HARNESS/FIXTURE defect. |
| International destination Iran customs | FAIL | Missing independent Chromium create/round-trip. Category 1 HARNESS/FIXTURE defect. |
| Duplicate/ineligible Iran results | FAIL | Seed and runner do not assert duplicate disambiguation or exclusion. Category 1 HARNESS/FIXTURE defect. |
| RTL/LTR locale matrix | FAIL | English baseline and width checks pass, but the hardcoded-English downstream pages make the Persian flow fail. Category 2 PRESENTATION/I18N. |
| Viewports 360/390/412/768/1440 | PASS | Chromium reports no horizontal overflow and visible version at all five widths; representative 390 screenshot retained. |
| Keyboard/accessibility semantics | FAIL | Control semantics regression passes, but the runner does not record the complete keyboard traversal/focus matrix. Category 1 HARNESS/FIXTURE defect. |
| Direct downstream | FAIL | Detail and Work Queue navigation pass; MDPM/economics/FX/OIP/lifecycle browser assertions are absent. Category 1 HARNESS/FIXTURE defect. |
| Accepted-quote downstream | FAIL | Source HTTP continuity passes; complete browser downstream assertions are absent. Category 1 HARNESS/FIXTURE defect. |
| Browser transient failure/idempotency | FAIL | Same-key HTTP replay and changed-payload conflict pass, but no post-commit browser response interruption is implemented. Category 1 HARNESS/FIXTURE defect. |
| Stale quote browser conflict | FAIL | Authoritative HTTP 409 passes, but Browser A/Actor B UX is not exercised. Category 1 HARNESS/FIXTURE defect. |
| Version MATCH | PASS | Normal/support identity projection and visible `Forwarder 1.9.1` pass in Chromium. |
| Version MISMATCH | FAIL | Automated component behavior exists, but the Slice 6.2 Chromium runner has no controlled mismatch state. Category 1 HARNESS/FIXTURE defect. |
| Version BACKEND_UNAVAILABLE | FAIL | No real-browser unavailable-state assertion. Category 1 HARNESS/FIXTURE defect. |
| Version IDENTITY_UNAVAILABLE | FAIL | No controlled Chromium identity-unavailable assertion. Category 1 HARNESS/FIXTURE defect. |

The FAIL rows are reproducible defects, not unreported or ambiguous states.
Because the localization failure is a product presentation defect and several
mandatory real-browser scenarios remain blocked by concrete harness/fixture
defects, Slice 7 remains NO-GO.

## Retained reports

- Passing controlled run: `P1B-UAT-20260810191536339078.json` and `.md`
- Browser result and screenshot: matching `-artifacts` directory
- Earlier failed attempts are retained because they document the explicit
  locale and accessible-label harness defects found and corrected during the
  slice.

## Cleanup

The passing harness report records backend/Vite termination, database drop,
and private PostgreSQL shutdown. Ports 55459, 57089, and 5201 were verified
closed. No package, tag, push, deployment, or Production access occurred.
