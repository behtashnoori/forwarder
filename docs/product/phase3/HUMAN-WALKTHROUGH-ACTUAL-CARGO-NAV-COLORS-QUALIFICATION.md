# Actual Cargo save and navigation colors — qualification

Qualification date: 2026-10-02. Product candidate:
`fe20ea67d0714ed288cf48bcb8d94e9121cccc73`. Entry base:
`e5ff5e9dd70b6d05cb83321086d851e790b78946`. Schema head:
`20261017_document_type_ownership` (one head). No migration was added.

The preserved HTTP record and database snapshot show a successful Cargo PATCH
whose payload left planned quantity at 100 and Actual null. The backend already
had separate planned and Actual fields, validation, persistence, audit and read
projection. Because that request contained no changed fact, the service returned
the existing row and did not append a false event. The failure was at the human
binding boundary: adjacent placeholder-only controls made the intended fact
unclear, and the UI did not distinguish a saved change from an accepted no-op.

The existing form now presents separately labelled planned and Actual controls,
normalizes Persian and Arabic digits and decimal separators into the existing
numeric API contract, validates the bound quantity, and reports which fact was
saved. A returned unchanged version produces explicit no-change feedback.
Planned and Actual remain separate SOR fields; Actual is never inferred from
planned, requested, allocation, delivery or progress data.

The navigation correction introduces the smallest shared semantic HSL layer:
`nav-surface`, `nav-text`, `nav-text-muted`, `nav-active-surface`,
`nav-active-text`, `nav-hover-surface`, `nav-hover-text`, `nav-border`,
`nav-focus-ring`, and `nav-disabled-text`. Global Expert navigation, Shipment
workspace navigation, shared tabs, Customer navigation and Admin tabs consume
the same active, inactive, hover, focus-visible and disabled rules. Status,
warning, success and alert colors remain independent. The font system did not
change.

## Scenario matrix

| Requirement | Evidence | Result |
|---|---|---|
| A1 planned 100 / Actual unknown | Component and backend fixtures render independent values; preserved ETA Shipment is captured read-only in this state. | PASS |
| A2 save Actual | P3-02 Chrome enters localized `۸٫۵`; API returns planned 10 and Actual 8.5. Component test enters localized `۱۰۰` and verifies Actual 100. | PASS |
| A3 reload | P3-02 reopens the Shipment and verifies both persisted controls and summary. | PASS |
| A4 history | P3-02 and backend assert `actual_quantity` null→value without a planned change. | PASS |
| A5 change planned | Backend changes planned while retaining Actual. | PASS |
| A6 change Actual | Backend changes Actual while retaining planned. | PASS |
| A7 unknown | Component/backend and preserved read-only evidence retain honest unknown Actual. | PASS |
| A8 API contract | Focused API test performs planned-only then Actual-only PATCH operations and checks versions/history. | PASS |
| A9 permissions | Existing Cargo authorization tests and P3-02 restricted-owner path pass; unauthorized personas remain denied. | PASS |
| A10 tenant isolation | Existing cross-tenant Cargo read/mutation denial remains covered by focused/P3-02 tests. | PASS |
| A11 downstream | P3-11 ETA browser and focused ETA/Closure tests pass; known Actual does not remain `ACTUAL_CARGO_UNKNOWN`. | PASS |

## Navigation and accessibility

Deterministic light-theme contrast ratios are: default text/surface 11.15:1,
muted text/surface 6.61:1, active text/active surface 8.03:1, hover
text/hover surface 9.14:1, and disabled text/surface 5.24:1. All normal-text
combinations exceed WCAG AA 4.5:1. Active items also retain shape/background
and font weight, focus-visible receives a two-pixel semantic ring plus offset,
and disabled items retain readable text and a not-allowed cursor.

P3-14 Chrome verifies semantic active states across Expert and Shipment
navigation, Admin shared tabs, Customer navigation, RTL, and 390×844 narrow
width. P3-15 retains a Request detail screenshot with the shared Customer
navigation. Visual inspection confirms one blue active language, subdued
inactive text, neutral surfaces and no status-color coupling.

## Executed checks

- Focused backend: 75 passed, including Cargo lineage, Closure, ETA and guided
  operational projection.
- PostgreSQL 18: fresh base-to-head migration plus selected Cargo lineage, ETA
  and Closure contracts, 3 passed. Public tracking regression also passed.
- Frontend: 110 files / 526 tests passed. Focused frontend: 6 files / 68 tests
  passed before the final complete run.
- TypeScript, production build and structure check passed.
- ESLint: 0 errors; the repository's existing 16 warnings remain.
- Chrome: P3-02 1 passed; P3-11 4 passed; P3-14 3 passed; P3-15 core 3 passed.
- Runner identity: clean exact Product candidate, owned disposable local/UAT
  PostgreSQL 18 and Chrome, Production not accessed or mutated, no deployment or
  release.

The retained evidence root is
`D:\1-webapp\forwarder-dev\actual-cargo-nav-evidence\qualification-final-fe20ea67`.
Failed diagnostic attempts are retained outside this final directory and are
excluded from PASS. Human Product Walkthrough remains `IN_PROGRESS`; Release
Ready remains `NO`.
