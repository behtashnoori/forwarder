# Control Tower Scalability Closure — Build Evidence

Date: 2026-09-21
Worktree: `D:\1-webapp\15-forwarder-golden-20260921`
Feature branch: `codex/control-tower-scalability`

## A. LPAF Governance Gate

The slice used the ACTIVE LPAF v2.2 Architecture Framework and mandatory Agent
Entry Protocol at Level B, with the reviewed v2.3 Product Integration and
`REFERENCE_IMPACT` gate applied as the Forwarder strong default. LPAF v2.4 was
not adopted. Mission, outcome, scope, authority, capability owner, Systems of
Record, actors, tenant/data scope, product journey, state/read-model/attention
owners, upstream/downstream chains, module and public-contract boundaries,
dependencies, API/schema/compatibility/authorization/performance/acceptance,
negative authorization, browser, and release impacts were identified before
Build in `docs/architecture/control-tower-scalability-v1.md`.

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_BY_ADR_051
```

The smallest authoritative reconciliation was committed before runtime Build:
ADR-051, the PDR-019 addendum, and the architecture/decision indexes authorize
the bounded server-side replacement without changing Control Tower product
meaning.

## B. Starting State

- Required and observed canonical parent:
  `2bb69bcc38ec9c8c0ffa1e27b64fcc052ee19c07`.
- Canonical branch/upstream: `integration/golden-controlled` and
  `github/integration/golden-controlled`.
- Starting local/remote ahead-behind: `0/0`; starting worktree: clean.
- Feature branch was created from the exact canonical parent and was not
  pushed.
- Design commit: `66a44df573f13e91aa2def966fa6ee8c282dd0a6`.
- Reference commit: `68cfa5c445106a4ee76a8add72c488d3338d1dd7`.
- Starting Alembic graph: one head,
  `20260925_quote_communication`.
- Ancestry contained D1/D2 Control Tower, Optional Multi-Cargo, Documents, Dual
  Calendar, Combined Transport, Simple Quote Communication, governed
  geography/private points, fixed-responsibility references, and dormant
  Notification foundation/lifecycle.

## C. Previous 100-Shipment Safety Ceiling

D1 loaded the complete authorized active Shipment population, rejected row 101,
evaluated all attention sources in Python, sorted the complete result, and only
then filtered/windowed it. `MAX_SUMMARY_SHIPMENTS=100` and
`ControlTowerPopulationLimit` correctly returned sanitized
`503 EVALUATION_UNAVAILABLE` instead of presenting a truncated list as complete.
The value was a technical safety ceiling, never a business, tenant-plan, or
supported-Shipment limit.

The ceiling constant and exception are removed. A population count greater than
100 is no longer a failure condition. Genuine authority, lineage, source,
detail-parity, or composition failure remains fail-closed with no items.

## D. Existing D1/D2 Contract

The existing endpoint, item allowlist, attention levels (`urgent`, `follow_up`,
`review`), reason translations, route/request-transport distinction, tracking
projection, responsible-Expert presentation, detail destination, private
`no-store` response, and stable error meanings are preserved. D2 continues on
the existing Golden route and shell with explicit loading, empty, denied,
unavailable, and general-error states. Shipment Detail is not copied or
reimplemented.

Existing D1 actor policy remains authoritative: current persisted active actor,
exactly one active membership, active organization, capability, eligible
Shipment lifecycle, tenant fence, and D1 responsibility root. Platform Admin
does not become a tenant operator, and same-organization membership alone does
not grant Expert rows.

## E. Scalability Design

`backend/services/control_tower_query.py` implements a request-time relational
attention index. It is a read query, not a materialized second System of Record.
The pipeline is:

1. authorized active population;
2. certified owner/request lineage;
3. optional authorized-field search;
4. normalized existing delay, exception, recognized work, readiness, and
   verified OIP promotion reasons;
5. one canonical rank tuple per Shipment;
6. complete aggregate metadata;
7. one bounded ordered SQL window; and
8. existing D1 detailed hydration/revalidation for only selected identities.

PostgreSQL is the governed release engine. SQLite retains a complete,
no-ceiling compatibility evaluator for broad repository tests; it is not used
as release-scale performance evidence.

## F. Query Population / Authorization

Authorization predicates are inside the population CTE before search,
attention sources, counts, ordering, offset, or limit. Foreign rows therefore
cannot alter items, totals, attention counts, page fullness, cursor state, or
error differentiation. The selected page is reloaded through the current scope
service and actor/responsibility is revalidated before route/tracking/source
hydration and again before serialization. Relational rank versus detailed D1
evaluation mismatch returns unavailable rather than partial success.

Owned PostgreSQL negative controls proved 25 foreign active rows do not affect
the 500-row tenant total; the foreign owning Expert sees exactly 25 own-tenant
rows; one same-tenant owning Expert sees exactly 250; Platform Admin is denied;
and membership revocation immediately denies the Expert.

## G. Attention / Aggregate Semantics

The relational reason query preserves D1 attention sources and rank meaning.
Selected-page detailed D1 evaluation is an executable parity check. Global
metadata comes from the complete authorized/search-matching ranked query:

- `summary.total` is the complete displayed population after the optional
  attention filter;
- `summary.attentionCounts` contains complete urgent/follow-up/review counts
  before the optional attention filter; and
- neither value is calculated from `items.length`.

At 500 active rows, the exact aggregate was 50 urgent, 450 follow-up, and zero
review. Filtering urgent returned total 50 while retaining those complete
global counts. A verified OIP promotion was selected as urgent and matched the
detailed page evaluator.

## H. Pagination / Windowing

Default page size remains 25; accepted range is 1 through 100 and no unlimited
page exists. The signed opaque v2 cursor binds actor ID, normalized page size,
attention filter, normalized search, and next offset. Explicit page metadata is:
`limit`, `offset`, `returned`, `hasMore`, and `nextCursor`.

The contract is a truthful query-time view, not snapshot isolation across a
browser session. Each response is internally current. A lifecycle mutation
between requests produced a truthful second-page total of 499 and offset 25.
Static traversal of all 500 rows with page size 100 produced 500 unique
Shipment references with no missing or duplicate identity.

## I. Search / Filters

Search is server-side, whitespace-normalized, limited to 100 Unicode code
points, and restricted to already-governed Shipment reference, Request
reference, and responsible-Expert display name. SQL escaping treats `%`, `_`,
and `\` as text. Search and attention predicates operate only within the
authorized population.

Browser and automated checks proved exact Shipment search, owner-name search,
urgent/follow-up/all filters, complete totals, and reset to the first page when
search/filter changes. Clearing search restores the complete population.

## J. Deterministic Ordering

The stable order remains:

```text
attention rank ASC
due bucket ASC
earlier due_at ASC NULLS LAST
earlier onset_at ASC NULLS LAST
Shipment public identity ASC
```

The public Shipment UUID is the final authoritative tie-breaker. Repeated first
pages over static data were identical; complete static traversal had no
duplicates or omissions.

## K. API Contract

The single additive endpoint remains:

```text
GET /api/control-tower/shipments
page_size=1..100 (default 25)
attention=urgent|follow_up|review (optional)
search=<normalized governed text, max 100> (optional)
cursor=<opaque signed continuation> (optional)
```

Existing item fields remain. The response adds:

```json
{
  "summary": {
    "total": 500,
    "attentionCounts": {"urgent": 50, "followUp": 450, "review": 0}
  },
  "page": {
    "limit": 25,
    "offset": 0,
    "returned": 25,
    "hasMore": true,
    "nextCursor": "opaque"
  }
}
```

Existing item fields and error meanings remain. Malformed values retain stable
400 validation/cursor errors. Genuine complete evaluation failure retains
sanitized 503 semantics and emits no misleading summary/page/items.

## L. Frontend D2 Integration

The feature-local adapter maps the additive envelope, including public
`followUp` to internal `follow_up`. The existing operational view adds a
server-backed search control, full matching total, displayed range, global
filter counts, and bounded previous/next navigation. Search/filter changes
reset pagination. A request generation guard prevents a slower old response
from replacing newer query state. Any failure clears items and metadata.

Existing Persian/RTL cards, Golden navigation, Dual Calendar formatting,
request-intent versus actual-route modes, responsible Expert, safe tracking,
and Shipment Detail destination are unchanged.

## M. Schema / Index Decision

```text
CONTROL_TOWER_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
MIGRATION_ADDED=NO
MIGRATION_MODIFIED=NO
```

Existing tenant/status/responsibility and source relationship indexes supported
the measured query. PostgreSQL `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for the
complete governed aggregate at 500 active rows measured 6.348 ms planning and
9.539 ms execution. The evidence does not justify speculative schema or index
work.

## N. PostgreSQL Large-Population Evidence

An owned PostgreSQL 18 cluster on loopback port 55432 and disposable database
`forwarder_control_tower_build` was migrated from empty to the one canonical
head. The fixture contained 500 active same-tenant Shipments, 50 terminal
same-tenant Shipments, 25 active foreign-tenant Shipments, two same-tenant
owners, manager, foreign owner, Platform Admin, mixed delay/exception facts,
50 critical route work items with plans/legs/checkpoints, five canonical
tracking projections, one accepted-Quote/Request lineage with an unresolved
readiness requirement, and one verified OIP promotion.

Required active populations `0, 1, 99, 100, 101, 250, 500` all returned
complete correct totals/counts; 101 did not return the former ceiling 503.
Search, filters, full 500 traversal, mutation between pages, membership
revocation, foreign isolation, manager and owning-Expert scope all passed.
Request-reference search also selected the accepted-Quote Shipment. The
dedicated result was `1 passed` in 355.57 seconds including full schema
migration, fixture generation, all population scenarios, traversal, and plan
measurement. A 1000+ population was not run; 500 is the highest qualified
population and is stated as such. After qualification, the PostgreSQL process
was stopped and the complete disposable cluster directory was removed.

## O. Query / Performance Evidence

At 500 active rows on the owned workstation:

| Window | SQL statements | End-to-end response composition |
| --- | ---: | ---: |
| 25 | 89 | 11.153 s |
| 100 | 87 | 11.353 s |

Both windows deliberately contain the accepted-Quote readiness branch. The
wider page did not increase statement count, and a focused one-versus-ten
accepted-Quote regression also held the query count constant, proving detailed
readiness and page hydration are batched rather than per-row N+1. The complete
governed aggregate plan executed in 9.539 ms; the larger end-to-end time is
dominated by current D1 detailed page construction/revalidation and canonical
tracking/source composition. SQL per request still evaluates matching indexed
attention facts; application hydration and response size are bounded by page
size. No arbitrary Production SLA or infinite-scale claim is made.

## P. Negative Authorization

Direct tests and the full suite prove:

- other-tenant items and population do not affect rows or counts;
- same-organization Expert sees only the governed D1 responsibility population;
- inactive/revoked membership fails closed;
- Platform Admin does not become an implicit tenant operator;
- guessed search content cannot select scope or leak a foreign count;
- cursor actor/filter/search/page mismatch is rejected;
- page authorization occurs before windowing; and
- selected-page responsibility changes fail the read rather than returning a
  partial page.

## Q. Browser Evidence

The real Vite frontend and real backend ran against the owned PostgreSQL 18
fixture.

- **Journey A — Manager/Admin:** normal login/home navigation to Control Tower;
  truthful 500 total; page 1 and page 2 ranges; later-page UUID Shipment Detail
  opened successfully with route/history facts; returned to Control Tower.
- **Journey B — Search/filter:** exact later-page UUID search returned one row;
  urgent returned 50, follow-up returned 450, all restored 500; each change
  reset to the first range.
- **Journey C — owning Expert:** normal sign-out/login/navigation; Owner A saw
  exactly 250 and no Owner B row.
- **Journey D — responsive RTL:** desktop and explicit 390x844 viewport; main
  `dir=rtl`; client width and scroll width both 385; previous/next controls
  remained present. The override was reset afterward.
- **Journey E — controlled failure:** one owned fixture Shipment responsibility
  was temporarily made invalid. Refresh returned the understandable complete-
  evaluation-unavailable state and no stale cards or partial total. The row was
  immediately restored, retry recovered the 500 total, and no Production/shared
  data was involved.

## R. Cross-Capability Regression

Shipment Detail drilldown, Dual Calendar, request transport versus actual route
(including Combined intent separation), Simple Quote Communication, Documents,
optional Cargo, assigned-work/fixed-responsibility boundaries, geography/private
locations, tracking, and dormant Notification behavior passed within the full
backend/frontend suites. The focused frontend/cross-capability rerun passed 59
tests across eight files, including Shipment Detail, transport, Quote
Communication, Documents, Cargo, and the Control Tower adapter/view/route.
Control Tower produces no NotificationAction, NotificationAttempt, outbox work,
or delivery activation.

## S. Full Regression

| Gate | Result |
| --- | --- |
| Focused Control Tower backend | `189 passed` |
| Dedicated PostgreSQL 18 scale qualification | `1 passed` |
| Full backend | `1,315 passed, 101 skipped, 1 expected xfail`, zero failures, 512.86 s |
| Focused frontend/cross-capability | `8 files / 59 tests passed` |
| Full frontend | `72 files / 356 tests passed`, zero failures |
| TypeScript | PASS, zero diagnostics |
| ESLint | PASS, zero errors; 13 existing warnings |
| Production build | PASS, Vite 6.4.3; 2,547 modules transformed |
| Python compilation | PASS |
| Backend determinism check | PASS |
| Repository structure check | PASS |
| Release/source/package/architecture cohort | `53 passed, 1 expected xfail` |
| Diff whitespace check | PASS |

Warnings are the repository's existing Python deprecations, Fast Refresh/hook
advisories, stale Browserslist data, and large-bundle advisory. They are not new
functional failures. A development qualification exposed that detailed
readiness composition still used a per-Shipment query bundle and that the first
measurement compared pages with different source mixes. Readiness was batched,
an explicit one-versus-ten regression was added, and the owned PostgreSQL
fixture was made like-for-like. The final non-growth contract passed at 89 then
87 statements. Under concurrent full-frontend load, one existing optional-Cargo
interaction exceeded Vitest's five-second per-test default; a test-only
15-second allowance was added, its isolated measured body completed in 2.813
seconds, and the default full suite then passed 356/356. No product behavior or
failure was suppressed.

## T. Database / Alembic Contract

Owned PostgreSQL migration `current` and `check` both reported:

```text
current=20260925_quote_communication
heads=20260925_quote_communication
pending=no
ALEMBIC_HEAD_COUNT=1
```

No migration, model column, business-state field, index, seed, or backfill is
part of this slice.

## U. Reference Re-check

Immediately before Freeze, the complete active LPAF v2.2 framework, Agent Entry
Protocol, v2.3 Product Integration gate, Control Tower design, ADR-051, PDR-019,
D1 evidence, D2 evidence, Forwarder architecture baseline, ADR-047 ownership
reference, S6 Golden journeys, and Post-D2 gap review were re-read against the
final runtime, API, tests, database, browser, and evidence.

Runtime and references agree on authorized population, existing attention
meaning, complete global metadata, bounded query-time windows, query-time rather
than snapshot consistency, fail-closed genuine error behavior, D2 presentation,
one database head, and no schema/state/Notification change.

```text
REFERENCE_IMPACT_FINAL=NONE
REFERENCE_ALIGNMENT=PASS
USER_JOURNEY=PASS
NAVIGATION_DISCOVERABILITY=PASS
RBAC_REACHABILITY=PASS
CROSS_SLICE_INTEGRATION=PASS
PRODUCT_SURFACE=PASS
REFERENCE_DOCUMENT_UPDATE=PASS
```

## V. Scope Integrity

```text
CONTROL_TOWER_100_CEILING_STATUS=REMOVED
CONTROL_TOWER_RELEASE_SCALABILITY_GAP=CLOSED

CONTROL_TOWER_PARTIAL_POPULATION_PRESENTED_AS_COMPLETE=NO
CONTROL_TOWER_AUTHORIZATION_BEFORE_WINDOWING=YES
CONTROL_TOWER_GLOBAL_KPI_FROM_PAGE_LENGTH=NO
CONTROL_TOWER_DETERMINISTIC_ORDERING=YES
CONTROL_TOWER_SERVER_SIDE_WINDOWING=YES

CONTROL_TOWER_BUSINESS_SEMANTICS_CHANGED=NO
CONTROL_TOWER_ATTENTION_MEANING_CHANGED=NO

EXPERT_OWNERSHIP_CHANGED=NO
CARGO_OPTIONALITY_CHANGED=NO
DOCUMENTS_BEHAVIOR_CHANGED=NO
DUAL_CALENDAR_BEHAVIOR_CHANGED=NO
COMBINED_TRANSPORT_BEHAVIOR_CHANGED=NO
QUOTE_COMMUNICATION_BEHAVIOR_CHANGED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO

PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO

CONTROL_TOWER_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
```

No deployment, Production access/change, Notification activation,
modularization, or Product Acceptance Closure was performed.

## W. Remaining Scale Limits

- Qualification proves the governed contract through 500 active rows, not
  unbounded or infinite scale. A 1000+ dataset remains useful future headroom
  evidence but is not claimed here.
- Page size is intentionally bounded to 100; default is 25.
- Offset continuation is signed and deterministic for a query-time state but
  deep offsets can cost more than early pages. It is not a historical snapshot.
- Database source/ranking work scales with matching indexed facts. Existing D1
  detailed composition is bounded by page size but remains the dominant local
  response cost; measurements are workstation evidence, not a Production SLA.
- PostgreSQL 18 is release authority; SQLite is functional compatibility only.

These are explicit bounded release characteristics, not a reinstated business
population ceiling.

## X. Verdict

PASS — CONTROL TOWER SCALABILITY COMPLETE
