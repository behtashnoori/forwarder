# FWD-02 — Governed geography and location selection integrity

## Mission entry (2026-09-16, before implementation)

Owner/authority: mission issuer, Forwarder Product/Architecture owner. One agent;
rigor B; pilot review at this slice's qualification. Scope is reference lookup,
request selection/persistence and existing ADR-035 tracking compatibility.
No Production, external sources, atlas imports, provider calls or new ownership.

FACT: `D:/1-webapp/forwarder-dev`, clean initial worktree, origin
`https://github.com/behtashnoori/forwarder.git`; local and remote FWD-01 HEAD
`d7cbedf9ec7416b83aeb6313aa095462a20e441d`. Only this worktree is registered.
FWD-02 did not exist locally/remotely; created from that exact commit.
Branch: `feature/fwd-02-location-integrity`. FWD-01 remains an ancestor.
UNKNOWN: customer environment, database contents, applied imports and Production
identity. Customer reports are not proof of a defect on this baseline.

## APPLICABLE_LPAF_RULES

`LPAF_V2_4_PILOT = ADOPTED` for FWD-02 only. Global ACTIVE remains v2.2.
Framework root: `D:/1-webapp/29-lpaf/29-lpaf (1)/29-lpaf`.
Read index, v2.2 framework/entry protocol, v2.4 main/entry protocol, owner approval,
changelog, four lesson candidates and identity re-attestation. Current v2.4
SHA256 verified: `217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397`.
Re-attestation binds this to original approved content via link-only repairs.
Applicable: v2.2 §§5–8,10–13; v2.4 MOD-03, READ-02, QUAL-01–05, ADOPT-01/02;
v2.3 product-integration journey/reference gates §§2–7 used as limited pilot
guidance, not global activation. No conflict identified. Workflow, analytics,
attention, file and AI engines are N/A: no such capability is added here.

## Ownership and plan

- PRIMARY_MODULE_AND_OWNER: General Geography reference owner for Country /
  InternationalCity; Logistics Network for tenant LogisticsPoint and type;
  Commercial owns request references; ADR-035 tracking owns immutable snapshots.
- ALLOWED_DEPENDENCIES: existing public lookup services/API → UI; tracking command
  validates tenant point then stores its snapshot. No cross-domain master write,
  shared catalog merge, map SDK or arbitrary SQL/AI API.
- FRAMEWORK_REFERENCE_IMPACT: NONE; Architecture/Business Owner; actual v2.2/v2.4
  paths above; product-specific lookup repair does not amend framework.
- PROJECT_REFERENCE_IMPACT: UPDATE_REQUIRED; Forwarder Architecture Owner;
  `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md` section 10 is stale about
  implemented ADR-035 convergence. Record bounded lookup contract and data gaps.
- TARGET_ACTORS_AND_DATA_SCOPES: public/customer request geography is shared
  reference data; authorized expert lookup uses active server-derived tenant
  membership and `logistics_point.read`; customer tracking sees allowlisted
  transaction snapshots, never the organization's catalog. Project associations
  remain independent. Historical inactive selections remain readable.
- QUALIFICATION_PLAN: disposable in-memory SQLite only for backend tests, isolated
  synthetic browser environment; geography seed idempotency and exact coverage,
  beyond-page tracking lookup/search/tenant denial, snapshot persistence and
  deactivation, UI loading/empty/error/denied/race/pagination tests, affected and
  full regression, RTL desktop/mobile real-role browser UAT, static checks,
  architecture gate and secret scan. Never infer UAT PASS from API tests.

No schema or temporal contract change is planned. ADR-005/025/026/028/035 and
existing services supply accepted ownership; no parallel ADR is needed for
lookup pagination/error handling. No new canonical/legacy bridge is introduced.
Rollback is reverting the bounded UI/API additions, retaining every identity and
snapshot. No data rollback is needed. Independent fixes continue despite gaps.

## Discovery / REUSE–EXTEND–NEW

| Chain | Disposition | Evidence / finding |
| --- | --- | --- |
| Shared countries and international places | REUSE | `seed_international_data.py`, `international-geography-v1.json`, `/api/countries`, `/api/international-cities` |
| Tenant master and tracking write/history | REUSE | ADR-035, `logistics_network_service.tracking_selector`, `multi_unit_tracking_service`; already implemented |
| Tracking query/UI pagination and failures | EXTEND | API defaults to 20, client sends only q, UI drops pagination; catch converts errors to empty; no response race guard |
| Parallel catalog, registry, ownership, migration | NEW: NONE | Existing authorities suffice for independent code fixes |

A: checked-in international seed/snapshot has no Italy/Norway records. Country
endpoint requires active country with active InternationalCity continuation.
Do not remove this applicability rule or invent locations to make countries
appear. DATA_COVERAGE_GAP; no approved replacement source found in scoped inputs.
B: approved geography snapshot supplies exactly IRTHR, IRIKA, IRBND for Iran.
International-city API returns all active rows, not a hardcoded three-item limit.
IranPort, domestic City and private LogisticsPoint are distinct authorities and
cannot be relabeled/imported as InternationalCity merely to expand this list.
DATA_COVERAGE_GAP; comprehensive coverage and Production repair are not claimed.
C: baseline already supports tenant private points, but browsing is capped at
the first 20 in the UI and failures look empty. Search can find later points;
customer incident attribution remains UNKNOWN pending environment evidence.

## Entry-time gaps (superseded where stated below)

- `FORWARDER-HISTORICAL-REPLAY-001 = BLOCKED_MISSING_EXTERNAL_EVIDENCE`.
- `PRODUCTION_IDENTITY = UNKNOWN`.
- Geography coverage needs a recoverable approved input from Reference Data Owner
  before mission acceptance; no new external source is authorized. Review at
  FWD-02 completion; this is a blocker for A/B acceptance, not a waiver.
- Untested framework rules remain EVIDENCE_PENDING.

Implementation and verification results will be appended below. No COMPLETE,
commit, push or browser PASS is implied by this entry record.


## Owner steering and final scope

The entry above is chronological evidence, not the final coverage decision.
The owner subsequently explicitly authorized searching and using worldwide
standards, naming UN/FIATA as possibilities. The owner then clarified that Italy
and Norway were examples: the intended scope is comprehensive worldwide coverage.
This supersedes the initial external-source prohibition and the intermediate
three-country/single-function profile. No FIATA dataset was assumed or used.
The source-availability blocker is resolved by the official UNECE publication.
No external runtime lookup, production import or new geography owner was added.

## Final reference source and exact scope

- Authority: [UNECE UN/LOCODE publication 2025-1](https://unlocode.unece.org/publications/),
  [official downloadable release](https://opensource.unicc.org/un/unece/uncefact/vocab-locode/-/jobs/artifacts/2025-1/download?job=package-release).
  Country codes follow ISO 3166-1 alpha-2 as represented in that publication.
- Semantics: [Recommendation 16](https://unlocode.unece.org/recommendation16/)
  and [publication encoding](https://unlocode.unece.org/docs/data-attributes/).
  Attribution: United Nations Economic Commission for Europe / UN/CEFACT,
  UN/LOCODE 2025-1, CC BY 4.0. Transformation is performed by Forwarder and is not
  a UNECE endorsement. Preserve this attribution on redistributed catalog copies.
- Source archive SHA256:
  `ad409fc7149b10f98d61190c34d9daf78b78bb8b31464cc66de1a89d09b01b5d`.
- Derived JSON SHA256:
  `b3e71f12f7c9cc8a9c5061a9df0ed67f085636bc84bd7120400694adab2d48ca`.
  The exact file is pinned to LF in `.gitattributes`. The original v1 is unchanged.
- Coverage: 249 countries/territories, all with a continuation, 115,208 unique
  locations. IR 154; IT 5,799; NO 1,142; US 20,856; DE 10,021; CN 1,666;
  BR 5,635; ZA 793; AU 2,583. No country/function shortlist remains.
- Eligibility: include AM/AA/AC/AF/AI/AS/AQ/RN/RL; exclude deletion mark X and
  other statuses. The publication has 815 QQ, 36 blank and 8 UR rows excluded
  by status, plus 19 deletion-marked rows. These are source row counts, not
  additive unique-identity counts. Duplicate alternate-name listings collapse by
  UN/LOCODE, never by name. All four original v1 records remain exactly intact.
- RN is a credible national request; RL confirms geographic existence, not
  trade relevance; AQ does not verify functions. Included does not mean all
  records carry government approval. Pending/unverified entries are not silently
  presented as approved. No promise of every village, municipality, private
  warehouse, exact terminal or current service availability is made.
- Source function/status/subdivision/coarse coordinates remain recoverable in
  the versioned input. Provenance defaults are inherited when loading, reducing
  repeated URLs without losing per-row lineage. All new names use source spelling
  as a fallback in the existing bilingual fields; no fabricated translation.
- Existing `city/port/airport` classification is reused: single maritime/air
  function can project to the corresponding category; all other/multiple functions
  use generic locality (`city`). The UI shows name and stable code, avoiding an
  unsupported claim that the location is a particular port or airport facility.

## Implementation and ownership

A: initial v1 coverage was IR/TM only, with a few historical unbound country/place
seeds elsewhere. The country endpoint correctly requires an active continuation;
no hardcoded UI exception for Italy or Norway was appropriate. The new optional
worldwide input supplies the governed continuation without bypassing lifecycle.

B: the Iran list was both data-limited and suppressed by a frontend `IR` special
case. That suppression is removed. Both request-submit paths now send stable
country and InternationalCity IDs as well as compatibility labels. Existing server
validation rejects a country/place mismatch and inactive fresh selections.

C: existing ADR-035 integration already queried tenant points but UI omitted
pagination, treated failures as empty and had no stale-response protection.
The selector now pages/searches with explicit loading/empty/error/denied/retry,
retains selected identity across pages and uses Persian/English fallback labels.
Tracking write rechecks `logistics_point.read`, active membership, active point/type
and unit tenant equality through the Logistics Network owner query. It snapshots
the point for historical/public reading, without exposing the private catalog.

Country/location lookups remain General Geography; private points remain Logistics
Network; Commercial remains request owner; tracking retains ADR-035 snapshots.
No new registry, shared/private merge, global-point adoption, schema or migration.
Stable IDs, country association, source codes, provenance, lifecycle and opaque
private IDs are map/agent-ready query inputs. Precise map coordinates, terminal
child codes, geocoding, map SDK and arbitrary SQL/LLM access are outside this slice.
No new ADR or framework amendment is needed for these existing-owner extensions.

## Optional import / recovery

ADR-028 remains governing: no automatic startup import, no seed prerequisite for
installation or deployment, and empty catalogs remain valid. Qualification used
only named disposable SQLite databases; no existing customer/development or
Production database was changed. Environment contents/identity remain unknown.

To reproduce the file offline after downloading the cited official ZIP:

```text
python scripts/build_fwd02_geography_snapshot.py <official-zip> <output-json>
```

The builder verifies the archive hash before processing. Compare the resulting
SHA256 to the pinned derived hash above. No network is used by the builder or app.

For a voluntarily requested import, an authorized operator must first attest the
specific target environment, take its normal database backup, and review
`plan_catalog()` inside that application's context with `skip_startup=True`.
`load_catalog()` validates pinned bytes and identities. Inspect creates/conflicts
before invoking `apply_catalog(expected_checksum=CATALOG_SHA256,
executed_by=<named operator>, approval_reference=<actual approval>,
environment=<attested environment>)` in a clean unit of work. Never substitute a
production URL during qualification. Audit uses existing `ReferenceDataSeedRun`.

Every pre-existing coded row retains its ID, labels, dataset and active state.
An unbound legacy same-name row or a code attached to another country refuses the
entire import and records the conflict; the old historical seed exercises this
case. A later environment-specific, reviewed identity mapping is required before
retry, not fuzzy matching or automatic reassignment. Different valid source codes
with identical names remain separate. Repeat import creates zero duplicates.
A write failure rolls back its data transaction and records failure. Do not undo
an applied catalog with destructive deletion: keep identities/history, use the
existing administrator lifecycle controls or restore the attested backup under
that environment's recovery procedure. Reverting code does not remove data.

## Qualification and browser evidence

Real browser UI, loopback Vite 5182 / Flask 5052, synthetic disposable SQLite only.
No API impersonation or administrator role was used for browser journeys.

- Initial customer journey: Italy/Fertilia to Iran/Sahand, submit/leave/reopen,
  `customer-reopen.*`, `customer-mobile.png` (intermediate bounded dataset).
- Final worldwide customer journey: US/New York (`USNYC`) to IR/Tabriz (`IRTBZ`),
  page 2 browsing then global-code search, confirmation and persisted public
  customer tracking `SR-H1IZ3E`; `global-page2.txt`, `global-mobile-form.png`,
  `global-customer-reopen.txt`, `global-customer-mobile*.png`,
  `global-customer-desktop.png`. Mobile 390x844, RTL, document width 385.
- Final worldwide Norway/Oslo (`NOOSL`) to Italy/Genova (`ITGOA`): normal country
  and code search, submit, customer read after navigation, `SR-3KOHM4`;
  `global-norway-italy-*`. Desktop 1440x900.
- Ordinary expert with actual tenant membership: page 2 private point 24 selected,
  saved, left and reopened; `expert-mobile-page2.png`, `expert-page2.txt`,
  `expert-reopen.*`. RTL mobile width 390, no horizontal overflow.
- Foreign-tenant search shows no foreign point: `expert-foreign-search.txt`.
  Revoking only the synthetic user's lookup permission displays explicit denial,
  not an empty catalog, while past snapshots remain: `expert-denied.*`.
  Public customer sees location snapshot only: `customer-private-snapshot.*`.
- The initial synthetic tracking fixture used a code without the landing page's
  required SR prefix; corrected to `SR-FWD02X` in the fixture only. This was a
  qualification-fixture correction, not a product routing defect.

Automated evidence is stored locally under ignored `instance/fwd02-qualification/`;
large logs, environment files and SQLite databases are intentionally not committed.
The final gate summary and log hashes are recorded in `qualification.json`.
The last full frontend run passed 37 files / 170 tests; TypeScript app compile,
production build and lint passed (12 existing lint warnings, existing bundle-size
warning). Worldwide geography tests passed 6, including full apply/reapply,
all-country coverage, page/search fences, lifecycle and historical conflict refusal.
Full final backend run passed 901, skipped 136, xfailed 1 in 533.26 seconds.
The skips are reported, not relabeled as passes. Existing deprecation warnings
are amplified by exercising the full 115k-row import. No test failure remains.
Rebuilding the catalog from the pinned official ZIP reproduced identical bytes.
A pre-existing economics test fixture omitted the required `margin_percentage`;
three test-only fields were filled with null to satisfy the app TypeScript gate.
No economics runtime behavior was changed.

## Final gaps and pilot disposition

The entry-time necessary-source blocker is resolved. The intermediate three-country
profile is superseded, not the final deliverable. Actual optional import into an
unknown existing environment is not claimed. Historical unbound rows require
reviewed identity mapping when such an import is requested. Source-excluded entries,
untranslated names and coarse coordinates are explicit limits, not hidden choices.
PostgreSQL-only tests require their external fixture and remain reported skips;
no schema change relies on an untested new migration.
`FORWARDER-HISTORICAL-REPLAY-001 = BLOCKED_MISSING_EXTERNAL_EVIDENCE` remains open.
`PRODUCTION_IDENTITY = UNKNOWN` remains open. Untested broader framework rules stay
EVIDENCE_PENDING. Pilot v2.4 applies only to this slice; mother LPAF is unchanged.

Commit and final fetched remote equality are reported in the delivery response and
local `remote-verification.json`; final COMPLETE requires those checks to pass.


Final browser rerun also saved private point 24 with the new write-time permission
check enabled (`global-expert-save.txt`) and, after logout, displayed its historical
snapshot on public tracking (`global-public-private-snapshot.txt`). Additional
Germany/Berlin search on mobile is captured in `global-mobile-selector.*`; the
selector fits a 390-pixel RTL viewport. Saved request country/location codes were
independently read from the same disposable database in `persisted-identities.json`.
All temporary browser overrides were reset and the test tab closed.
