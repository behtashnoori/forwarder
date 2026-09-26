# P3-13 — bounded exceptional owner transfer

2026-09-26. BUILD=IMPLEMENTED; QUALIFICATION=PASS_ON_c091490; INTEGRATION=SEPARATE_CONTROLLED_RECEIPT.
LPAF v2.7 / rigor C / Astra capability. No runtime model-setting assertion.

## Product authority and actual entry

The retained mission §§48–69 and accepted ADR-069 govern this slice. Specific
Product decisions permit same-tenant active Organization Admin exceptional
transfer, mandatory reason, eligible active same-tenant Expert target, live
owner/version concurrency, immutable history and existing current authorization.
DN02_OWNER_TRANSFER_PORTION=RESOLVED_FOR_P3_13; DN09_STATUS=RESOLVED_FOR_P3_13.
Architecture acceptance: 6259830f2a5fe94798bf4183d2643bf624529c26.

Actual canonical is clean, freshly fetched and 0/0 at
c2e6140d52eda620ecaef6e255bcd591f58da2cb. P3-12 Product is d1574fa137017ac41331cf039117ab9c19e101a3;
its exact evidence and canonical integration are c2e6140. The
[entry receipt](../../operational/evidence/phase3-p3-13-entry-20260926/p312-integration-receipt.json)
records the successful approved push/fetch. P3-13 reuses its prepared independent
checkout after fast-forward to that actual canonical; no P3-11 runtime import.
The new migration must follow 20261010_phase3_closure with one linear head.

## Boundaries to implement and verify

- One named TRANSFER_OWNER capability derived from current exact Admin authority;
  authenticated actor/tenant are server-derived, never request fields. No implicit
  Platform authority, ordinary Expert transfer or document-management Admin grant.
- Current owner remains Shipment SOR. Ordinary ORM/raw owner updates remain denied.
  One narrow SECURITY DEFINER routine creates immutable history and atomically
  updates owner/version with audit/outbox; no generic bypass flag or dynamic SQL.
- Dedicated NOLOGIN function owner, no runtime membership/SET ROLE, fixed
  pg_catalog,pg_temp search path, qualified names, no PUBLIC EXECUTE or DDL grant.
  Application runtime must be a genuinely restricted role. A real restricted LOGIN
  connection, not SET ROLE from postgres, must prove the database boundary.
- Application authenticates/binds the human and authorizes the request. DB validates
  supplied active Admin/tenant/target/owner/version/chain/idempotency/atomicity. A
  compromised trusted app credential with structurally valid Admin input is outside
  the human identity guarantee; PostgreSQL human authentication is not claimed.
- Organization then Shipment then sorted actor/target/membership locks; reread after
  waits. Exact authorized replay returns one receipt; competing same predecessor
  commands have one winner. Existing owner mutation guards cannot be disabled.
- New owner receives existing normal capabilities; former owner retains only any
  independently valid permission. Current reads, downloads, commands, list,
  Workspace/Tower and delayed UI responses must use current authorization.
- Document bytes/version/actors and all old audit/event history stay unchanged.
  Transfer does not reassign Request, Quote, WorkItem, Action or SLA responsibility,
  including later background evaluation. Old-owner open-work count is informational.
- Customer DN10 identity and Cargo entitlement stay unchanged; no internal history
  or Admin reason enters Customer DTOs. Initial ownership time is not fabricated.
- Explicit administrative transfer may occur on a closed Shipment under this
  separate approved authority; closed state and its ClosureDecision stay fixed.
  No new physical operation is enabled after closure.

## Required proof and reconciliation

Mission cases A–O, restricted-role raw owner/history/routine/role misuse, genuine
concurrency waits, rollback atomicity, membership/target revocation races,
unchanged independent assignments and Customer projection, direct document access,
stale identity maps and delayed browser responses. Prove current owner capabilities
after ordinary Admin navigation, with desktop/mobile/reload/focus paths.

Empty downgrade restores the original unconditional owner guard. Any transfer
history blocks destructive downgrade before DDL; no historical owner restoration
or fabricated backfill. Shared cluster roles may remain empty and unprivileged
when other synthetic databases use them. No Production role operation.

Product/reference reconciliation will classify every material change as AUTHORIZED
or PRESERVED against the retained decisions. Tests/source/evidence are not new
Product authority. PostgreSQL 18, complete backend/frontend, affected Chrome,
OpenAPI/tenant inventory, static/governance and source-bound evidence are mandatory.
Current-head assertions must verify the complete new parent chain, while historical
slice assertions retain their historical heads.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J03/J04/J06/J08/J09;
FWD-IPJ-01/IPJ-03/IPJ-04. GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN; HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN;
RELEASE_READY=NO; PRODUCTION_UNTOUCHED=YES. P3-14/P3-15 are not authorized.

## Product/reference reconciliation (PDA-07)

| Observable difference | Classification / authority |
| --- | --- |
| Reasoned same-tenant Admin transfer; exact current eligible Expert target | AUTHORIZED: mission §§48–69, ADR-069 / named acceptance 6259830 |
| Current owner changes, one receipt and version increment; first owner time unknown | AUTHORIZED: mission history/concurrency; no inferred legacy event |
| Former owner loses ownership-derived commands/downloads; target gets existing owner authority | AUTHORIZED: DN09; no new permission or persona |
| Explicit Project read remains valid, without document management | PRESERVED: current assigned-work/project policies |
| Request/Quote assignment, old and third-party Work, pinned SLA and later evaluation | PRESERVED: explicit mission prohibition on reassignment |
| File bytes, version and actor; Customer DN10/document audience | PRESERVED: ADR-061/062/065 and mission |
| Closed administrative transfer, unchanged closed decision, no new physical work | AUTHORIZED: separately named P3-13 command; P3-12 physical boundary PRESERVED |
| Resume/focus refresh and rejection of delayed obsolete responses | AUTHORIZED: current authorization requirement; no new Tower ranking or SLA |
| Candidate pagination/search and current-owner wording | AUTHORIZED presentation of the approved command; no new target eligibility |
| Explicit execution/work permissions independent of ownership | PRESERVED: no blanket removal or invented former-owner access |
| Narrow SECURITY DEFINER / NOLOGIN owner / restricted actual LOGIN | AUTHORIZED implementation of accepted ADR-069; no DB human-authentication claim |

## Mutation and background audit

- Cargo, allocation and transport-execution mutation helpers now lock/reload the
  parent before live owner authorization. Their read capability paths stay pure.
- Route mutations use the same current Expert parent fence before RoutePlan/leg
  writes. Action mutations lock and reauthorize the parent before pinning any
  newly created Action; retained Action assignees are never replaced.
- Delivery/report creation, document upload/deactivation and context revision
  already lock the parent and reauthorize after waits; those boundaries remain.
- Legacy shared-transport allocate/release also acquire the parent fence. Lock
  conflicts fail closed; no retry bypass or broadened Admin authority.
- Accepted-Quote concurrent-create fallback now repeats current Shipment read
  authorization, matching its existing early replay branches.
- `operational_execution.manage` / event create/correct/verify are independent
  explicit existing capabilities. They are not added to normal Expert baseline,
  and are not silently removed when a separately valid capability exists.
- `organization_sla_service.evaluate_organization` skips already pinned sources
  and updates evaluation state without changing responsible_user_id. Tests cover
  both old-owner and third-party Work plus repeated post-transfer SLA evaluation.
  Transfer calls no reconciliation or reassignment path.

## Preliminary evidence — not Product freeze

Owned PostgreSQL probe 1 exposed a harness startup `create_all` conflict with
historical migration head. Both app factories now pass `skip_startup=True`;
migrations exclusively create the owned schema. Probe 2 passed the base boundary;
probe 3 passed expanded revocation/concurrency/history checks. The unit expansion
initially exposed four test-fixture/schema assertions (SLA actor context/process
name, closure field name, Tower attention fixture, duplicate YAML anchor names);
they were corrected without weakening authority. 21 focused unit tests pass.
The first focused frontend run had one retry-test interaction failure. The full
preliminary run had that failure, the old fixed-owner presentation assertion, and
an unchanged NewOperation selector wait failure while the browser harness was
also running. The retry interaction and approved current-owner wording assertion
were corrected; NewOperation source/assertions/timeouts were unchanged. The focused
rerun passed all 62 tests in five files, including NewOperation.
No preliminary result is final source qualification.

The preliminary PostgreSQL regression run passed 14 tests (8 current/source
proofs, 5 P3-01..05, 1 Public Tracking). App/node type checks, lint and build
passed; lint retains 14 warnings. The broadened backend subset passed 59 tests.
Browser probe 1 passed but its Customer screenshot captured a loading state;
the screenshot now waits for actual Cargo content. Browser regressions and final
exact-source gates are pending.

A subsequent mutation audit extended the same parent lock/recheck to existing
milestone, checkpoint, route-timeline/reconciliation and generic Work resolution
commands whose authority depends on current Shipment visibility. Pure reads
remain unlocked. PostgreSQL tests exercise document, milestone and checkpoint
mutation authorization waiting behind transfer. Existing tenant-level economics,
external-reference and independently granted exception commands retain their
explicit existing policy; this task does not redefine them as owner-only.

Browser Detail retains ordinary command form behavior. On resume, any changed
Shipment version retires descendant forms (including same-name owner transfers);
unchanged focus returns preserve forms, including file chooser returns. Native
command reloads do not close the active closure section. No private owner key
or persistent authorization cache is introduced.

## Candidate source boundary

The Product candidate contains runtime, regression tests, the owned qualification
harness and the above reference reconciliation. Final qualification must name
its immutable Git Product SHA and tree; preliminary dirty-source logs are not
substitutes. Evidence-only commits may follow after all required source-bound
checks pass. Canonical fast-forward/push/fetch is authorized only after those
checks and fresh canonical identity verification.

## First exact-source attempt and document-order correction

Product 212d01fa19979e520f8ba9d4a5b4cefd9248cb9e passed 441 frontend tests,
14 PostgreSQL tests, 15 Chrome tests and nine static gates. Its complete
backend run had 1534 passes, 120 environment-dependent skips and one failure:
the legacy ProjectConfiguration OpenAPI text-range test also included the
new private owner-transfer schemas and rejected their explicit person id.
The owner-transfer schema block is moved before ProjectConfigurationPage.
Parsed YAML equality proves the API contract is unchanged; the existing
test/assertions and all runtime files are unchanged. This failed attempt
is retained and is not final qualification. A fresh Product source identity
and all required source-bound gates follow the correction.

## Final exact-source qualification

The candidate and preliminary sections above preserve the build-stage record.
Product `c0914906af6675c016d5b77d51ecc8a0c05c0b72` now passed all required
[source-bound gates](../../operational/evidence/phase3-p3-13-owner-transfer-status-20260926.md).
The evidence-only descendant changes no runtime/test/migration file. Controlled
canonical integration and push/fetch use a separate exact-SHA receipt. Global
Product validation remains EVIDENCE_PENDING; no new scope is authorized.
