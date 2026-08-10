# Forwarder v1.9.1 Slice 6.3 final acceptance

## Classification

`PRODUCT DEFECT REMAINS — SLICE 7 NO-GO`

Passing controlled run: `P1B-UAT-20260810192958531797` at application commit
`7c5eb9f0624a1f924c4471f20dada548ce5b6449`.

## Acceptance matrix

| Scenario | Result | Evidence or reproducible defect |
|---|---|---|
| Quote browser creation | PASS | Chromium selected an eligible quote, completed the shared form, submitted through UI, reached detail with source/customer/request/quote lineage, found the operation in the list, and confirmed the quote was removed from the selector. |
| Deep-link normal | FAIL | Runner has no Request Detail navigation case. Category 1 HARNESS/FIXTURE. |
| Deep-link refresh | FAIL | Runner has no refresh case. Category 1 HARNESS/FIXTURE. |
| Deep-link history | FAIL | Runner has no back/forward case. Category 1 HARNESS/FIXTURE. |
| Deep-link stale | FAIL | Runner has no stale deep-link browser case. Category 1 HARNESS/FIXTURE. |
| Domestic origin | PASS | Chromium selected canonical Province and completed direct round-trip. |
| Domestic destination | PASS | Chromium selected canonical Province and completed direct round-trip. |
| Non-Iran origin | FAIL | No Chromium Country→InternationalCity payload case. Category 1 HARNESS/FIXTURE. |
| Iran origin | FAIL | No complete Chromium required-error/history/payload case. Category 1 HARNESS/FIXTURE. |
| Non-Iran destination | FAIL | No Chromium Country→InternationalCity payload case. Category 1 HARNESS/FIXTURE. |
| Iran destination city | FAIL | No independent Chromium typed-city round-trip. Category 1 HARNESS/FIXTURE. |
| Iran destination port | FAIL | No independent Chromium typed-port round-trip. Category 1 HARNESS/FIXTURE. |
| Iran destination customs | FAIL | No independent Chromium typed-customs round-trip. Category 1 HARNESS/FIXTURE. |
| Duplicate disambiguation | FAIL | Runner does not assert duplicate type/province labels and canonical selection. Category 1 HARNESS/FIXTURE. |
| Persian RTL | FAIL | Work Queue and major detail headings were localized, but detail actions/timeline column labels and economics sub-surface still contain hardcoded English. Category 2 PRESENTATION/I18N. |
| English LTR | PASS | Browser baseline and quote/direct flows passed with explicit English locale. |
| Viewport 360 | PASS | No horizontal overflow; version visible. |
| Viewport 390 | PASS | No horizontal overflow; version visible; screenshot retained. |
| Viewport 412 | PASS | No horizontal overflow; version visible. |
| Viewport 768 | PASS | No horizontal overflow; version visible. |
| Viewport 1440 | PASS | No horizontal overflow; version visible. |
| Keyboard semantics | FAIL | Component semantics pass, but complete Chromium keyboard traversal is absent. Category 1 HARNESS/FIXTURE. |
| Direct Documents/MDPM | PASS | Detail renders localized explicit Not applicable state. |
| Direct economics | FAIL | Browser assertion absent. Category 1 HARNESS/FIXTURE. |
| Direct FX | FAIL | Browser assertion absent. Category 1 HARNESS/FIXTURE. |
| Direct OIP | FAIL | Work Queue navigation passes; OIP detail/state assertion absent. Category 1 HARNESS/FIXTURE. |
| Direct lifecycle | PASS | Browser-created direct detail loads route and milestone lifecycle surface. |
| Quote Documents/MDPM | FAIL | Browser assertion absent. Category 1 HARNESS/FIXTURE. |
| Quote economics | FAIL | Browser assertion absent. Category 1 HARNESS/FIXTURE. |
| Quote FX | FAIL | Browser assertion absent. Category 1 HARNESS/FIXTURE. |
| Quote OIP | FAIL | Browser assertion absent. Category 1 HARNESS/FIXTURE. |
| Quote lifecycle | PASS | Browser-created quote detail loads route and milestone lifecycle surface. |
| Browser transport recovery | FAIL | HTTP replay passes but response-drop/retry through UI is absent. Category 1 HARNESS/FIXTURE. |
| Stale quote conflict | FAIL | HTTP 409 passes but Browser A/Actor B UX case is absent. Category 1 HARNESS/FIXTURE. |
| Identity MATCH | PASS | Visible `Forwarder 1.9.1` and support projection passed. |
| Identity MISMATCH | FAIL | Controlled Chromium state absent. Category 1 HARNESS/FIXTURE. |
| Backend unavailable | FAIL | Real-browser unavailable state absent. Category 1 HARNESS/FIXTURE. |
| Identity unavailable | FAIL | Controlled Chromium state absent. Category 1 HARNESS/FIXTURE. |

Every mandatory row is explicitly PASS or FAIL. No backend contract or
architecture defect was found. The remaining failures are authorized
presentation and harness defects, but they are not closed in this slice.

## Environment and cleanup

- PostgreSQL 18 private loopback cluster: port 55469
- Backend/frontend: loopback ports 57099 / 5211
- Migration current/head: `20260819_v191_acceptance_corrections`
- Python 3.13; Node 24.11.0; Playwright 1.57.0; Chromium bundle 1200
- Personas: direct-only, explicit quote-only, legacy quote, combined, neither,
  admin/support
- Harness stopped Chromium, backend, Vite, dropped the disposable database,
  and stopped private PostgreSQL. Production was untouched.
