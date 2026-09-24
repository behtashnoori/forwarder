# Forwarder repository governance

This repository operates under **LPAF v2.7 — ACTIVE / FROZEN / CANONICAL**.

Canonical LPAF workspace:

`D:\1-webapp\29-lpaf\29-lpaf (1)\29-lpaf\lpaf`

Normative documents:

1. `current\LPAF-v2.7-Architecture-Framework-FA.md`
2. `current\LPAF-v2.7-Agent-Entry-Protocol.md`
3. `LPAF-v2.7-BASELINE-ACCEPTANCE.md`

Before architecture, implementation, remediation, validation, release, or substantial planning work:

- read and apply the applicable LPAF v2.7 normative documents;
- apply LPAF capability routing, escalation, decomposition, handoff, and verification rules;
- preserve authority boundaries and current Product behavior outside the specifically approved mission scope;
- do not treat historical versions, candidates, examples, tests, or implementation evidence as normative authority.

Every product-changing mission must apply the Product Authority controls in LPAF v2.7 §5.5:

- `PDA-01`: obtain specific Product Owner approval for reserved product behavior changes;
- `PDA-02`: maintain a queryable Product Authority Record before Solution or Build;
- `PDA-03`: do not treat technical, architecture, or security constraints as product authority;
- `PDA-04`: present decision requests in plain product language with effects and alternatives;
- `PDA-05`: do not treat implementation or engineering evidence as Product approval;
- `PDA-06`: do not alter tests or references to normalize unauthorized behavior;
- `PDA-07`: reconcile every material observable difference as AUTHORIZED, PRESERVED, VIOLATION, or UNKNOWN;
- `PDA-08`: stop the affected work when specific product authority is missing.

Before Release Ready for an applicable user-facing release, this project must
maintain and use its own version-controlled critical Product Acceptance Journey
Pack (or equivalent project reference), run the applicable slice and integrated
automated Product journeys on the exact candidate, and obtain a recorded
Human Product Walkthrough result from the Product Owner or an explicitly authorized
human delegate under LPAF v2.7. An agent may prepare evidence but cannot grant
the human PASS. The actual Forwarder critical-journey list is defined only in a
separate Product mission; this instruction does not invent that list.

Canonical Forwarder Product Acceptance Journey Pack:

`docs/product/FORWARDER-PRODUCT-ACCEPTANCE-JOURNEYS-V1-FA.md`

Every future mission must apply that Pack's `JOURNEY_IMPACT` and evidence
staleness rules. Product-changing work must name affected `FWD-J*` and
`FWD-IPJ-*` journeys and the required slice, integrated, and human reruns.
`JOURNEY_IMPACT=NONE` requires an evidence-backed rationale.

Known evidence gap: global LPAF Product validation remains `EVIDENCE_PENDING`.

Task-specific instructions may further constrain a mission but must not silently redefine or weaken LPAF v2.7.
