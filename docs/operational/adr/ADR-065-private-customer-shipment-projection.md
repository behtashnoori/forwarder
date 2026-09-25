# ADR-065 — Private Customer Shipment projection

- Status: ACCEPTED within the Product Owner's explicit mission §§45–61,
  recorded before implementation. This grants no Release or human acceptance.
- Date: 2026-09-26 Asia/Tehran. LPAF v2.7, rigor C, Astra capability need;
  no claim about the actual runtime model setting.
- Authority: [five-stage Product Authority Record](../../product/phase3/P3-06-10-MISSION-AUTHORITY.md).
- Verified canonical/local/fetched github entry:
  `6a11c2e02a3103f0bc36129bd12798842b7c39cb`, clean, ahead/behind 0/0.
  Required P3-02/05/06/07/08 integrated; P3-08 Product
  `48fa69b70af1bcf06fc5a9783b98fdf54de7a18c` qualified on fresh evidence.
  Sole schema head remains `20261008_phase3_cargo_delivery`.

## Authority, scope and preservation

AUTHORIZED: authenticated Customer list and detail of the same shared Shipment,
filtered through live DN10 grants to actual own Cargo; own quantities, relevant
simple route, delivery, exact authorized documents, safe report/timeline and
low-risk shared status. A general shared-transport label is allowed. Multiple
explicit grants yield a union without merging CRM identities; revoking one
removes only its derived facts. No new Customer command or public capability.

DELEGATED: query composition, SQL authorization, pagination, allowlisted DTOs,
freshness/in-flight invalidation, existing Persian portal components and tests.
PRESERVED: ADR-052 public Request capability and fixed allowlist; ADR-053 optional
account, anonymous Request, private Request/Quote, recovery and generation-based
session revocation; fixed Expert ownership; ADR-057 quantity meanings; ADR-058
route SOR; ADR-060 allocations; ADR-062 entitlement; ADR-063 safe effects and
location gates; ADR-064 delivery/evidence. Existing commands, SLA, Actions,
Exceptions, Workspace and Tower remain unchanged. Exact-candidate preservation
is UNKNOWN until qualification. DECISIONS_NEEDED: none within §§45–61.
ETA, closure, owner transfer, Production, deployment and release are excluded.

## Identity and query boundary

The read chain is current ACTIVE session/generation → live account/organization/
CRM entitlement query → Cargo owner → same-tenant Shipment → separately permitted
facts → explicit DTO. Request membership, matching contact text and UUID possession
are never authorization. No copied Shipment, duplicate identity or read-model
table is created. Every response is rebuilt from current domain SORs; there is
no stored watermark or deferred refresh. A failed/denied query returns no prior
projection. Existing source facts and historical migrations stay untouched.

An EXISTS own-Cargo predicate scopes Shipments before count, search, ordering or
pagination and naturally deduplicates the union. Search covers safe Shipment UUID
and own Cargo names only. Stable creation-time/UUID ordering does not expose other
Customers' recent activity. Detail repeats the same predicate; absent, guessed,
foreign and revoked identities share a non-disclosing not-found response. Counts
and page controls describe only authorized facts. Own CRM labels distinguish a
multi-grant account's Cargo; no other owner, quantity, count or private filename
is emitted. The shared boolean alone reflects multiple real Cargo owners and is
the expressly authorized disclosure, without identifying any participant.

## Source and presentation contract

Shipment contributes only opaque identity, creation instant and existing low-risk
lifecycle status, explicitly labelled as the overall file status. It does not
infer Cargo delivery or close anything. Cargo contributes its stored title/type/
UOM and distinct requested/planned/known-actual quantities; nullable facts remain
unknown, never relabelled from legacy quantity. Delivery contributes its current
effective per-Cargo summary and authorized current/corrected historical facts,
with exact currently permitted evidence. Actor, private correction reason and
internal predecessor identity are omitted through the existing safe projection.

Only each own Cargo's destination association in the active RoutePlan and that
leg's ancestors form its simplified route. Unrelated branches/checkpoints are
excluded. Public governed geography names describe main points; tenant facility
names, addresses, branch labels, carrier references and raw snapshots are not
copied. A facility is represented by its governed geographic area, with an honest
undefined label if unavailable. Missing destination association stays undefined.
This is a simplified planned route, not actual traversal or an ETA.

Reports reuse ADR-063's explicit Cargo-impact predicate before pagination and
safe message projection. Latest LOCATION reports are separately ranked per typed
scope/target after authorized impact filtering and correction exclusion; existing
own-Cargo, relevant-stage and positive current ACTUAL-unit participation gates
still apply. Multiple permitted locations remain separate reported observations,
never a last-unit-to-whole-Shipment location or GPS. History remains independent
of the latest-location selection. No internal note is sanitized into a message.

Documents use the shared P3-06 predicate, exact active version and same Shipment/
tenant before pagination. Generic safe filenames prevent cross-Customer metadata
leakage. Every download calls the existing live reauthorizing endpoint. Explicit
non-Cargo sharing remains independent, but it does not grant Shipment detail when
there is no own Cargo. Delivery evidence links alone do not authorize old bytes.

## API, freshness and compatibility

Read-only `/api/customer/shipments` and `/api/customer/shipments/{shipment_id}`
use the current signed Customer cookie. Detail has independent bounded document,
delivery and timeline pages. All success/denial responses are private/no-store.
No export, public alias, internal DTO reuse or new account prerequisite is added.

Normal portal navigation adds «حمل‌های من». List/detail clear displayed data before
reload and on hidden/pagehide; return, pageshow, focus and navigation request fresh
authorization. Abort and request-generation guards reject late stale responses,
including failures and authentication redirects. Download failure invalidates the
displayed projection. No browser persistent cache is introduced. Loading, empty,
denied, unknown and retry states remain distinct; mobile layout is required.

## Verification and references

No migration: reuse the actual head above and prove query behavior on PostgreSQL
18. Required matrix: A/B shared Shipment with distinct Cargo/routes/docs/deliveries/
safe reports, unentitled C, foreign tenant, multi-grant union/partial revocation,
account disable/session generation, direct URL, count/search/page non-disclosure,
unknown legacy facts, corrected history and disagreeing own Unit locations.
Chrome must use login and normal portal navigation, desktop/mobile, reopen/back,
Admin revoke and exact downloads. Full backend/frontend, required account/recovery/
anonymous Request/Request/Public Tracking and P3-06/07/08 regressions, TypeScript,
lint/build/OpenAPI/architecture/structure/determinism/secret checks bind exact SHA.
Source rollback removes only this new read surface; it must preserve DN10 and all
underlying source history. There is no P3-09 destructive schema rollback.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J01/J02/J08/J09, FWD-IPJ-03/IPJ-04.
LPAF framework reference impact NONE. Current Forwarder architecture, indexes,
Product projection/document contracts, plan and API require reconciliation before
integration. Historical ADR bodies remain unchanged; this explicitly enables the
previously deferred private Customer consumer of ADR-057/058/062/063/064.
Global Product EVIDENCE_PENDING; integrated journeys/human walkthrough NOT_RUN;
Release Ready NO. P3-10 retains its separate entry/qualification gate.
