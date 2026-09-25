# P3-08 — partial Cargo delivery qualified; controlled integration authorized

Date: 2026-09-26 Asia/Tehran; raw UTC execution times are retained. LPAF v2.7 / rigor C;
capability need Astra is recorded without claiming an actual runtime model setting.
Authority: explicit five-stage Product Owner mission §§31–44 and ADR-064, recorded
before implementation. Dependencies P3-02/03/05/06 were integrated at verified entry;
P3-07 is not a functional dependency.

- Product SHA: `48fa69b70af1bcf06fc5a9783b98fdf54de7a18c`.
- Canonical base: `682e83ed3a51badb3938d66dbd337e8e10e57797`.
- Evidence SHA: this evidence-only descendant, identified by its integration receipt.
- Branch: `codex/phase3-p3-08-partial-delivery`.
- Sole Alembic head: `20261008_phase3_cargo_delivery`.
- Actual parent: `20261007_phase3_reported_facts`; historical migrations unchanged.

## Behavior and authority

One immutable CargoDelivery SOR records same-tenant Shipment, real Cargo ownership,
destination, positive quantity, exact Cargo UOM snapshot, aware occurrence, backend
recording time and actor. Corrections append a full successor with revision,
predecessor and supplied reason. Original facts and exact file-version evidence
remain. Effective totals sum current correction leaves independently for each Cargo.

Synthetic A: known actual 100, deliveries 60 + 35 = 95 / remaining 5; correction
60 → 58 produces 93 / remaining 7; separate 9 produces 102 / excess 2 and succeeds.
B remains 25 / delivered 0. A separate reproducible clean-Product in-memory
scenario assigns all 25 B units to an in-progress ExecutionUnit and proves that
A delivery/correction leaves B quantities, allocation, Unit lifecycle/version,
Shipment state/version and work items unchanged. Its source and result are retained.
Full A delivery also leaves B and Shipment unchanged.
No requested/planned/known-actual, allocation, lifecycle, Action or closure mutation
is performed. Unknown actual remains unknown, and old completed/delivered lifecycle
states create no Delivery. Unknown real Cargo ownership denies new commands.

Only the active fixed owning Expert writes. Organization Admin remains oversight
read-only; same-organization peer, Platform Admin and cross-tenant commands deny.
Shipment/Cargo row locks, actor/payload-bound command identity and expected revision
distinguish replay from two genuine deliveries. PostgreSQL concurrent same-key
requests return one fact, separate keys retain both facts, and competing corrections
accept one successor and reject the stale request. Tenant/Cargo/UOM composite FKs,
unique successor and database/ORM immutability protect persistence.

DELIVERY is a real typed P3-06 document context. Its exact CaseDocumentFile link is
appended atomically with context attachment/revision, using existing private storage.
Explicit current same-Cargo evidence can also be selected on a command. The original
link survives corrections and file replacement; new replacement starts INTERNAL.
Current visibility and live DN10 authorization govern every Customer projection and
download. A sees permitted current A bytes with a generic safe filename; B, revoked
A, old replaced versions and a new INTERNAL version deny. A historical evidence
association never grants read authority. Full Customer Shipment UI remains P3-09.

Persian Expert UI separates per-Cargo summaries, current delivery cards and secondary
correction history. Destination and occurrence are explicit; quantity discrepancy is
prominent and nonblocking. Evidence upload targets the exact selected Delivery.
Retry retains its command identity. Owner/read-only, empty, unknown, error and
loading states are available, with responsive desktop/mobile layout.

## Exact-Product evidence

`P3_08_QUALIFICATION=PASS`. The explicit mission authorizes controlled canonical
fast-forward, github push/fetch and 0/0 after this evidence commit. The receipt and
next slice entry establish exact evidence/canonical identities without inventing a
self-referential commit SHA. [Recoverable bundle](phase3-p3-08-cargo-delivery-20260926/qualification.json)
contains logs, identities, screenshots and SHA-256 hashes.

| Gate | Result |
| --- | --- |
| Full backend | PASS: 1459 passed / 116 environment-dependent skips / zero failures or errors; 1372.15 seconds. Required PostgreSQL proofs ran separately. |
| Full frontend | PASS: 88 files / 414 tests; 284.48 seconds. |
| PostgreSQL 18 | PASS: four Delivery/report/DN10/document tests plus five P3-01..05 regressions. Legacy preservation, empty downgrade/re-upgrade, populated rollback refusal, true concurrency, tenant/UOM FK and transaction rollback verified. |
| Normal Chrome | PASS: P3-08 partial/correction/exact-byte download/excess/reopen; P3-07, two P3-06/DN10 journeys and P3-01..05. Nine tests; final browser run follows the completed backend. |
| Visual review | PASS: final desktop 1280×720 and mobile 390×844; readable separate Cargo cards, discrepancy warning and no horizontal overflow/header overlap. |
| TypeScript/lint/build | PASS: direct app and Node projects, zero lint errors / 13 existing warnings, existing build chunk-size and Browserslist data-age advisories. |
| Contract/security/static | PASS: entire OpenAPI parse, exact new-route parity and operational namespace tests, tenant inventory, architecture, structure, determinism, diff. |
| Identity/secrets | PASS: 60 changed Git blobs and 13 built files hashed; zero changed-scope secret findings. |

The numeric request-generation cleanup now uses explicit assignment with identical invalidation behavior, resolving its hook warning; only the thirteen pre-existing warnings remain.

Prequalification diagnostics are explicitly separate in `prequalification.json`.
An initial test fixture used an unsupported Shipment lifecycle value and the first
browser assertion referenced an absent response field; both were corrected against
existing contracts before Product freeze. No runtime defect was waived and none of
those dirty-source results substitutes for the clean Product gates above.

Superseded Product `461de820278edeb76a40287efe00cfaecab40fa8` passed frontend but
its full backend was stopped incomplete when concurrency review identified a real
stale-file issue. PostgreSQL reproduced it: context revision accepted an exact file
already superseded by another committed transaction. The repair takes the shared
Shipment lock, reauthorizes the owner and refreshes/locks file before context,
matching Delivery/upload/replacement ordering. The regression now denies with 404,
leaves context/version unchanged and adds no evidence. Failed reproduction and
supersession records are retained; all final gates rerun on the new Product above.

## References and limits

ADR-064, architecture/decision indexes, architecture baseline, tenant inventory,
OpenAPI, current document contract, mission authority and current plan are reconciled.
Reference-impact ownership: LPAF framework baseline NONE; Forwarder Product and
architecture owners' current references updated. `REFERENCE_RECONCILIATION=PASS`;
`REFERENCE_IMPACT=NONE`; protected behavior `PRESERVED` in the recorded scope.
`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`: FWD-J02/J04/J08/J09 and FWD-IPJ-04.

`GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`; `INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN`;
`HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN`; `RELEASE_READY=NO`. P3-09 and P3-10 remain
behind their mission gates. P3-11..15, Production, deployment and release NOT_STARTED/NO.
Old applications do not understand DELIVERY context; rollback after new facts is
unsupported without separately governed reconciliation. No destructive downgrade
is used to erase history.

All final owned servers stopped and the exact temporary runtime directory was removed.
The earlier stopped DN10 directory remains because automatic host approval rejected
its deletion with reason `blocked by policy`; exact path and no-bypass record remain
in qualification.json.
