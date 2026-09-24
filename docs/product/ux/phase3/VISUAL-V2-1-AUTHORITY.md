# Visual fidelity V2.1 — mission and authority

Date: 2026-09-25. Owner: Product Owner, explicit attached Visual Fidelity Alignment mission (sections 1–56). Scope: prototype and documentation only. Rigor B, proportionate to three-persona visual/preservation evidence; stages M0/M1/M4/M6. Requested capability: Astra/highest available reasoning; execution uses the configured session without claiming a model-setting change. Work is decomposed into source inventory, isolated CSS refinement, Chrome preservation/visual review, and evidence reconciliation.

## Entry facts and governing reference

- Canonical product: `D:/1-webapp/15-forwarder-golden-20260921`, branch `integration/golden-controlled`, clean HEAD `d83b1aa7c0011221188e753c0f38d2058859400b`.
- V2: `D:/1-webapp/forwarder-dev/phase3-ux-prototype-revision-v2`, branch `codex/phase3-ux-prototype-revision-v2`, clean HEAD `dd02ae58b58fb83fa539863c66b2e46f02c35bda`.
- Verified ancestor: `ce00433d0eff683c1b75c3d2e5e2b48dfef08d88`; canonical HEAD is also an ancestor. V2 history remains intact.
- Child: `codex/phase3-ux-visual-fidelity-v2-1`, created from that exact V2 HEAD, at `D:/1-webapp/forwarder-dev/phase3-ux-visual-fidelity-v2-1`.
- `LPAF_BASELINE=2.7`. Starting folder 15-forwarder points to 2.6; both explicitly targeted repositories point to 2.7. Canonical LPAF README, current/README and `LPAF-v2.7-BASELINE-ACCEPTANCE.md` establish owner-authorized activation on 2026-09-24 and supersession of 2.6. This resolves the entry-pointer discrepancy without changing the framework or starting repository.
- Normative workspace: `D:/1-webapp/29-lpaf/29-lpaf (1)/29-lpaf/lpaf`. Applied v2.7 framework §§3–5, 8.2, 9.1, 11–17 and matching Agent Entry Protocol. The 2.6 compatibility documents were inspected first, then superseded by activation evidence.

## Product Authority Record

| Field | Authority / boundary |
| --- | --- |
| AUTHORIZED_PRODUCT_CHANGES | Visual presentation of the existing isolated V2 only: typography, spacing, canonical visual tokens, controls, panels, navigation, tables, timeline, responsive presentation and evidence. No product behavior change. |
| DELEGATED_TECHNICAL_CHOICES | Prototype-local stylesheet, local font asset if needed, review-only reference rendering, Chrome checks and screenshots, bounded commits. |
| PROTECTED_OUT_OF_SCOPE_BEHAVIOR | V2 workflow, navigation labels/order, microcopy, actions, all app.js interactions, data/ownership, customer filtering, allocation, route, ETA, closure, permissions, roles, lifecycle; all product runtime/frontend/backend/schema/migrations; canonical checkout, production, deployment and release. |
| DECISIONS_NEEDED | No visual decision blocks preparation. Final V2.1 human approval NOT_RUN. Existing Blueprint DN-01…DN-09 remain open and are not decided here. Stop any refinement that needs changed behavior. |
| APPROVING_OWNER_OR_AUTHORITY | Product Owner through the attached mission. Only the Product Owner may grant final UX approval. |
| APPROVAL_REFERENCE | Visual Alignment mission §§1–5, 34–36, 40–41, 48–56; V2 source and STORYTELLING-AUDIT-V2.md provide recoverable preservation baseline. |

## Review truth supplied by the owner

```text
PRODUCT_FLOW=PASS
UX_STORYTELLING=PASS
RELATIONSHIP_CLARITY=PASS
MICROCOPY_DIRECTION=PASS
VISUAL_FIDELITY=NEEDS_FINAL_ALIGNMENT
V1_PRODUCT_OWNER_REVIEW=COMPLETED_NEEDS_CHANGE
V2_PRODUCT_OWNER_REVIEW=COMPLETED_CONDITIONAL_PASS_VISUAL_ALIGNMENT_REQUIRED
UX_PRODUCT_OWNER_REVIEW_V2=COMPLETED_CONDITIONAL_PASS_VISUAL_ALIGNMENT_REQUIRED
V2_1_PRODUCT_OWNER_REVIEW=NOT_RUN
UX_PRODUCT_OWNER_FINAL_APPROVAL=NOT_RUN
PROTOTYPE_DATA=SYNTHETIC_ONLY
```

ASSUMPTION: canonical tokens can improve fidelity without altering V2 behavior; verify with byte-preserved app.js, page-story preservation and fresh Chrome journeys. UNKNOWN: final human aesthetic acceptance. There is no real customer data, API, auth, database or runtime SOR in this static sample. All names, IDs and values are synthetic fixtures, never master-data authority.

## Verification and reference impact

DoD: source-derived Visual DNA inventory before styling; three journeys and state switcher pass in Chrome; desktop all pages and customer 390px visually reviewed; controls/modal/mobile/reference screenshots; no console errors, failed resources or external browser requests; no material NEEDS_CHANGE; exact candidate hashes; bounded commits and clean child branch. Preserve historical V1/V2 evidence.

`JOURNEY_IMPACT=NONE`: runtime paths, Product Contract v1, Journey Pack v1.1 and all critical FWD-J01…J09 / FWD-IPJ-01…04 meanings stay unchanged. FWD-J09/FWD-IPJ-04 are target-design context only. Prototype navigation is rerun as design evidence, not integrated runtime acceptance.

Framework reference (LPAF owner, canonical path above): NONE. Product contract and journey pack (Product Owner, docs/product): NONE. UX Blueprint/review references (Product Owner, docs/product/ux): UPDATE_REQUIRED for visual baseline and supplied review truth; reconcile on completion. Architecture, domain, release and recovery changes: NOT_APPLICABLE because only static design artifacts change. Product Complete, Release Ready, Release Complete: NO. Global Product validation remains EVIDENCE_PENDING.
