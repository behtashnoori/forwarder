# Phase B — Slice 1 — Governed Geography Reconciliation — 2026-09-19

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/golden-contract-freeze-phase-a` |
| Slice branch | `codex/phase-b1-governed-geography` |
| Starting HEAD | `953a67ff5820864c08bc8727f34f49ed66237527` |
| Phase A parent | `2b95c35acc12e1ba28c390a125eb51f46af7dd4b` |
| Starting cleanliness | clean |
| Golden application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` — verified ancestor |
| Engineering base | `b48e51c8d0eda00bcc7582b68da85528b14547d2` — verified ancestor |
| Database head | `20260921_shipment_evidence_ownership` |

The Phase A Markdown report, machine-readable ledger, and controlled integration plan were present and read before implementation. The slice branch was created directly from the required starting HEAD. All prerequisites matched; no stop condition was triggered.

## B. Donor Analysis

The approved runtime/catalog donor was commit `4b06ed039d72c15f10d2f114fed07fc2fdef457b`, and the qualification-only donor was `1714118340943f1dbbf99e4b25edc9ef41f817e6`. The following donor files were inspected read-only:

- `backend/international_geography_catalog.py`
- `backend/reference_data/international-geography-v2-fwd02.json`
- `backend/routes/locations.py`
- `backend/services/logistics_network_service.py`
- `backend/services/multi_unit_tracking_service.py`
- `backend/tests/test_fwd02_geography.py`
- `scripts/build_fwd02_geography_snapshot.py`
- `src/components/InternationalLocationSelector.tsx`
- `src/components/LocationForm.tsx`
- `src/lib/api.ts`
- `src/pages/RequestDetail.tsx`
- the FWD-02 README, qualification JSON, persisted-identity JSON, and remote-verification JSON evidence

Reused semantics were the exact approved catalog bytes and provenance, stable ISO/UN/LOCODE identity, additive reconciliation, inactive preservation, bounded server-side lookup, retained selection identity, and explicit untranslated-label disclosure. Donor tests informed the Golden-specific coverage and reconciliation assertions.

Rejected semantics were cumulative FWD runtime state, wholesale page/component replacement, private-point service changes, tracking-service changes, and any startup or automatic Production seed behavior. No donor branch was merged and neither donor commit was cherry-picked. `D:\1-webapp\15-forwarder` remained a read-only reference; its tracked worktree was not changed.

## C. Golden Geography Delta

| File | Reason |
| --- | --- |
| `.gitattributes` | Pins the large approved JSON catalog to LF for deterministic byte identity. |
| `backend/reference_data/international-geography-v2-fwd02.json` | Exact approved FWD-02 data artifact. |
| `backend/international_geography_catalog.py` | Strict catalog validation plus explicit plan/apply reconciliation with audit records, conflict refusal, additive writes, and no boot hook. |
| `backend/international_geography_catalog_cli.py` | Explicit operator plan/apply command with checksum, approval, environment, and additional Production confirmation requirements. |
| `backend/routes/locations.py` | Deterministic country output and opt-in bounded location search/pagination/type filtering with stable keys and label provenance. |
| `src/lib/api.ts` | Typed bounded location-page client and label/stable-key fields. |
| `src/components/InternationalLocationSelector.tsx` | Reusable 50-row server-search selector with paging, retry/error/empty distinction, stale-response protection, retained identity, and fallback disclosure. |
| `src/components/LocationForm.tsx` | Replaces full-country location loading with bounded origin/destination selectors and searchable country choices. |
| `src/pages/NewOperation.tsx` | Uses the same bounded selector while preserving existing private-facility and identity payload behavior. |
| `src/components/RouteAuthoringSection.tsx` | Uses the bounded selector and continues to emit the canonical `international_city` identity; private points remain separate. |
| `backend/tests/test_phase_b1_governed_geography.py` | Catalog, reconciliation, identity, inactive, conflict, lookup, fallback, and request round-trip contracts. |
| `src/tests/components/InternationalLocationSelector.test.tsx` | Search/paging/selection, retry/empty, stale-response, and fallback UI contracts. |
| `src/tests/components/LocationForm.destination.test.tsx` | Adapts existing request-flow coverage to the paged client without changing submitted IDs. |
| `src/tests/components/LocationForm.geography.test.ts` | Proves the public form uses the bounded selector and retains identity payloads. |
| `src/tests/pages/NewOperation.test.tsx` | Adapts operational-create coverage to the paged selector. |
| `src/tests/components/RouteAuthoringSection.test.tsx` | Proves paged selection emits the canonical route-authoring identity. |
| `docs/operational/evidence/phase-b1-governed-geography-20260919.md` | Human-readable slice evidence. |
| `docs/operational/evidence/phase-b1-governed-geography-20260919.json` | Compact machine-readable catalog and qualification evidence. |

No tracking, notification, quote, document, Control Tower, cargo, transport, date, counter, or numeric-formatting behavior was changed. No compiled output is included.

## D. Catalog Provenance

| Property | Verified value |
| --- | --- |
| Dataset identity | `forwarder-international-geography-v2-fwd02` |
| Snapshot version | `2025-1` |
| Checked-in JSON SHA256 | `b3e71f12f7c9cc8a9c5061a9df0ed67f085636bc84bd7120400694adab2d48ca` |
| Source archive SHA256 | `ad409fc7149b10f98d61190c34d9daf78b78bb8b31464cc66de1a89d09b01b5d` |
| Source authority | ISO 3166-1 alpha-2 countries; UNECE UN/LOCODE 2025-1 locations |
| Source license | UNECE UN/CEFACT CC BY 4.0 |
| Country count | 249 |
| Location count | 115,208 |
| Iran locations | 154 |
| Italy locations | 5,799; present |
| Norway locations | 1,142; present |
| Type breakdown | 102,894 city/locality; 7,062 port; 5,252 airport |
| Duplicate records/stable keys | 0; unique |
| Invalid records | 0 |

The catalog is used offline only. Runtime networking is forbidden by the catalog policy and no record was invented from model knowledge.

## E. Reconciliation Semantics

Countries match by exact ISO alpha-2 code; international locations match by exact UN/LOCODE. A stable key already attached to another country, duplicate rows for the same key, or an unbound same-country legacy name is a conflict requiring reviewed mapping. Conflicts refuse all catalog writes.

The reconciler inserts missing countries and locations only. Existing rows are counted unchanged; it never updates labels, provenance, keys, tenant ownership, or lifecycle state, and it never deletes or reactivates a row. The plan is read-only. Apply requires the pinned checksum, named operator, approval reference, explicit environment, and clean unit of work. Catalog rows are written in one transaction and each attempt has a persistent `ReferenceDataSeedRun` audit result.

The full 249-country/115,208-location disposable rehearsal began with the existing Golden v1 rows and an inactive Tehran identity:

| Run | Created countries | Created locations | Unchanged countries | Unchanged locations | Updated | Skipped/conflicts | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| First apply | 247 | 115,204 | 2 | 4 | 0 | 0 | succeeded in 1.569 s |
| Second apply | 0 | 0 | 249 | 115,208 | 0 | 0 | succeeded/no-op in 0.323 s |

The inactive Tehran row retained the same database ID, country, labels, v1 provenance, and inactive state across both applies. A separate deliberate cross-country/legacy-name conflict rehearsal returned `refused` with zero catalog row writes.

## F. Authorization / Private Points

Private logistics-point models, routes, authorization, and services were not changed. They remain tenant-owned rather than global reference data. Existing active same-tenant visibility, wrong-tenant denial, inactive-point refusal, safe public/customer projection, and immutable snapshot contracts passed in the focused logistics/tracking regression set. New selectors alter only governed `Country`/`InternationalCity` lookups and continue to keep private facility selection on its existing path.

## G. Frontend Behavior

All changed Golden selectors use the reusable paged lookup with a 50-row page, server-side name/UN/LOCODE search, deterministic next/previous paging, country search, explicit loading/failure/empty states, and cancellation of stale country/query responses. A selected object is retained even when it is not on the current page, so its numeric governed ID remains the submitted identity.

Focused coverage proves Italy (`ITGOA`) and Norway (`NOOSL`) are searchable/selectable, Iran exposes more than the former three entries, and old Golden identities keep their IDs. The request test creates a Norway-to-Italy request, reads the persisted country/location foreign keys back unchanged, and verifies review/detail uses those governed identities. Existing request destination tests continue to submit and reopen the same numeric IDs; no translated-label reverse mapping exists.

## H. Persian Label Policy

The approved v1 Persian labels are preserved for existing rows. New catalog rows use the source name in `name_fa` only as an explicit untranslated fallback; they are not represented as verified translations. API responses expose `name_fa_is_fallback` and `label_source`, and Persian selectors append `نام منبع` while explaining that equality with the source name is not a verified Persian translation. The catalog test distinguishes verified Tehran (`تهران`) from fallback Abadan (`Abadan`).

## I. Performance / Bounded Query Evidence

The new API path filters by active country and active location, searches server-side across Persian name, source name, and UN/LOCODE, orders deterministically, and fetches `limit + 1` rows to determine `has_more`. The frontend requests 50 rows; the API accepts 1–100 and rejects invalid type/limit/offset/search bounds. All current product selectors were moved off the former full-country transfer path.

On the full disposable 115,208-row catalog, 25 repeated bounded Italy searches for exact `ITGOA` measured 7.995 ms median and 8.66 ms p95 on local in-memory SQLite. The Italy first page returned exactly 50 rows with `has_more=true`. This is local evidence, not a hard product SLA.

## J. Tests

Pre-change focused baseline checks passed for the Golden geography/reference, private-point, location-resolver, tracking-location, and request-location paths; the baseline frontend sample was 3 files/10 tests.

| Gate | Result |
| --- | --- |
| New Phase B1 backend contract | PASS — 3 tests |
| Focused Golden backend geography/private-point/resolver/tracking set | PASS — 45 tests |
| Focused changed frontend set | PASS — 7 files, 54 tests |
| Full backend suite | PASS — 1,050 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failures |
| Full frontend suite | PASS — 58 files, 286 tests, executed in seven deterministic batches |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,537 modules transformed; output directed to a disposable directory |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Full catalog disposable apply/no-op rehearsal | PASS |
| Migration graph/current/check | PASS — one head, `pending=no` |

Phase A recorded 1,047 backend tests and 283 frontend tests. This slice adds three passing backend tests and three passing frontend tests with no test-count reduction. PostgreSQL-only suites remain accurately skipped because no explicit owned disposable PostgreSQL URL was supplied; this slice has no schema-bearing work. The one-command Vitest collector stalled on this Windows host before file execution, so the complete 58-file inventory was executed in seven non-overlapping one-worker batches; every file and all 286 tests passed.

## K. Database Contract

```text
DATABASE_HEAD =
20260921_shipment_evidence_ownership

MIGRATION_ADDED =
NO

MIGRATION_MODIFIED =
NO
```

The repository has one Alembic head. A disposable SQLite database stamped at that head returned `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=no`; both `current` and `check` exited zero. `backend/migrations` has no diff.

## L. Phase A Regression Contract

- `GCF-A-002 authentication/authorization/tenancy/assignment`: satisfied. The full backend suite and relevant auth/tenant/assignment tests passed; no authority code changed.
- `GCF-A-003 customer-request-workflow`: satisfied. Request creation, persisted location foreign keys, detail/review projection, public form tests, and the full suites passed.
- `GCF-A-007 geography-reference-data-logistics-points`: satisfied with the intended breadth delta. Stable v1 identities, inactive state, private-point boundaries, bounded projections, and immutable snapshots remain protected.

## M. Scope Integrity

```text
CONTROL_TOWER_IMPORTED=NO
OTHER_FWD_FEATURE_IMPORTED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

No deploy, push, Production endpoint, Production environment, database, process, credential, or secret was accessed. No second Phase B slice was started.

## N. Remaining Risks

- The checked-in catalog is not automatically applied anywhere. Each environment still requires a separately approved explicit plan/apply operation; Production requires its additional confirmation. This is the intended safety boundary, not incomplete runtime behavior.
- PostgreSQL-only suites were not executed without an owned disposable PostgreSQL URL. There is no schema delta; final release qualification should still repeat lookup/reconciliation performance against its owned target database.
- The backward-compatible unpaged array response remains available for legacy API consumers, while every current Golden selector uses the bounded path. A future versioned API retirement can remove that compatibility surface after external-client inventory.
- The official UNECE snapshot describes governed localities, not service availability or exact terminal/facility positions. The UI and data policy make no such claim.

## O. Verdict

PASS — GOVERNED GEOGRAPHY RECONCILIATION COMPLETE

## P. Next Goal

Derive and execute separately, only after approval, Phase B — Slice 2: shared numeric presentation. Start from this clean geography commit; inspect FWD-04 implementation `ed4026c1f07c54da1980fcea1cabcb4c1a5e289f` and mandatory correction `5994253b82e31f24dd6ec68db9c601c2aec9d7f1` as semantic/test donors; introduce a pure parser/formatter and reconcile Golden consumers while explicitly excluding identifiers, phone numbers, tracking codes, vehicle references, and UUIDs. Add no migration, make no calendar-policy decision, preserve all Golden contracts, run the focused presentation/two-timezone/RTL gates and full qualification, and keep it in its own `presentation` commit. This next slice was not executed here.
