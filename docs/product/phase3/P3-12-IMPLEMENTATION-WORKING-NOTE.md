# P3-12 implementation and exact-source qualification gate

Date: 2026-09-26. BUILD=IMPLEMENTED; QUALIFICATION=PASS at Product d1574fa.
This source note is retained; the [final evidence report](../../operational/evidence/phase3-p3-12-closure-status-20260926.md)
records exact Product/tree and complete qualification. Evidence SHA and controlled
canonical push/fetch are recorded separately in the integration receipt.
No earlier exploratory run is substituted for exact-source qualification.

## Authority and source identity

Retained mission and named ADR-067/068/069 acceptance apply. The Product reply
«اصلاح سوابق و ثبت دیرهنگامِ واقعیت‌های قبلی و تکمیل/اصلاح اسناد مجاز باشد؛ عملیات جدید ممنوع.»
is implemented by the [command matrix](P3-12-POST-CLOSURE-COMMAND-MATRIX.md).
Actual canonical entry is `368cd736cbffce3d62c33336868738d9086e8306` on
`integration/golden-controlled`, remote `github`, initially clean 0/0.
This branch contains architecture acceptance `6259830f2a5fe94798bf4183d2643bf624529c26`
and reviewed matrix `7f98fca1f32a2c2afd51b0889e23893180b9852e`, with no P3-11 runtime.
Rigor C / Astra capability; no claim of runtime model-selection configuration.

## Runtime contract

Policy and effective versions are explicit Org Admin configuration, with no seed,
HS rule, hidden threshold or guessed policy. GENERAL plus current applicable and
executed mode criteria combine by union; overlapping mandatory wins with all
contributing scopes retained. Missing source data is UNKNOWN. Delivery quantity,
MDPM exact current evidence, independent Exceptions and WorkItems remain their
existing sources. No-file/count shortcut, copied source ownership or auto-close.

Only completed may become closed. Normal close requires current owning Expert
and all mandatory criteria. Exceptional close requires active same-tenant Admin
and reason; unmet criteria remain visible in immutable history. Commands lock
configuration, Shipment and live actor/membership, reauthorize and reread sources
after waits. Idempotency is actor-bound. Current assessment identity rejects stale
facts/policy/version. Decision plus terminal state commit atomically.

Current source identities and summaries are pinned privately; read DTO omits
source_facts. Customer sees only the existing DN10-filtered safe projection and
closed label, never the internal checklist, Admin reason or source filenames.
UI clears stale confirmation on focus/visibility/resource changes, drops stale
responses and presents missing items first with current-source links. New-operation
controls hide after closure; historical repairs retain their existing forms.

## Persistence and rollback

Sole branch head `20261010_phase3_closure` follows actual canonical
`20261009_phase3_route_time`. Four additive empty tables, no sample configuration,
backfill, auto-close, history rewrite or existing migration edit. Immutable policy
versions require criteria at commit. Terminal SQL/ORM guards deny reopening and
closed creation without a same-transaction completed-only decision. Source-write
fences cover Cargo, current Delivery, MDPM requirement/association/assessment/exact
file, Exception, work, route plan/leg/stage, including absent insert races.

Empty downgrade/re-upgrade preserves prior data. Once policy/decision evidence
exists, downgrade refuses before DDL. N-1 after first use is unsupported; restore
an approved pre-use snapshot or roll forward. No Production operation is authorized.

## Required verification and reference reconciliation

Focused backend covers completed-only normal/exception, unknown/no policy, union,
future policy pins, stale identity, replay, no partial state, live role/tenant/active
boundaries, late facts/actual quantity/document replacement and denied new commands.
Owned PostgreSQL 18 proves upgrade/empty rollback, immutable/raw terminal guards,
absent WorkItem and document mutation before close, close before later repair,
concurrent replay and competing close. Chrome exercises ordinary Admin setup,
Expert normal close, exception with missing history, wrong predecessor, mobile
layout and private Customer view. Run all backend/frontend/static gates and affected
PostgreSQL/Chrome regressions on the clean Product commit before any integration.

Current baseline, ADR index/body, OpenAPI four-route recursive allowlists, tenant
inventory, Phase-3 plan and ADR-016 ledger are reconciled. Current-head assertions
advance; historical slice heads remain historical. Pure Cargo snapshot tests use a
module-local planned-row lock adapter; closure tests use real sessions. Initial full
prequalification failures (old head expectations, isolated test mocks, inventory
and environment selection) and subsequent diagnostic fixes remain in external logs;
they are not a final PASS. No runtime exception was hidden to make tests pass.

Pre-integration review found that manual Action creation also creates new work.
It is now denied after closure and its form is hidden; existing Action follow-up,
assignee and explicit resolution remain independent. Backend and UI tests cover
both sides. The intermediate ad11390 attempt (13 PostgreSQL and 14 Chrome passes,
static passes, frontend timeouts, interrupted full backend) is superseded in full.
Fresh qualification uses the corrected clean source; screenshots wait for the
parent detail refresh as well as the closed decision panel.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J04/J05/J06/J08/J09 and
FWD-IPJ-02/IPJ-03/IPJ-04. Slice and affected regression checks are not global
integrated journey qualification. GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
HUMAN_WALKTHROUGH=NOT_RUN; RELEASE_READY=NO; PRODUCTION_UNTOUCHED=YES.
P3-11 stop-range placement still needs Product authority; P3-13 must use fresh actual
canonical after independently qualified integration. P3-14/P3-15 are not started.
