# Human Walkthrough Customer Request Hardening — Mission and Product Authority

- Date: 2026-09-27 (Asia/Tehran)
- Governing baseline: `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`
- Mission type: governed post-final-candidate hardening
- Rigor / capability route: `Level B / Sol`
- Product owner authority: the explicit attached mission titled
  `Forwarder — HUMAN WALKTHROUGH BOUNDED RELEASE HARDENING`
- Verified source: `integration/golden-controlled@4f4080cb1fd6970ec37a03f291162652fbb687af`
- Historical pre-hardening Product SHA:
  `b1a8f4fafb89e4e8e9b2f35ffcb79bc98c7ec86a`
- Required schema identity: one Alembic head,
  `20261012_phase3_cargo_eta`; `MIGRATION_REQUIRED=NO`

## Mission contract

Outcome: correct only the six Product Owner-observed Customer Request defects,
re-qualify the changed candidate, integrate it by fast-forward only when all
mandatory gates pass, and update the owned local walkthrough runtime without
resetting or replacing its database.

Actors: authenticated Customer, anonymous Customer, current Request assignee,
Organization Admin, and the Product Owner continuing the walkthrough.

In scope:

- customer-safe current Request-assignee display name on authenticated create
  confirmation and private Request detail;
- truthful pending-assignment presentation when no current assignee exists;
- restoration of already-stored submitted Request facts in private detail;
- direct existing domestic/international chooser from the Customer portal;
- session-aware Customer header entry and the authorized portal navigation order;
- approved transport-selection wording and local selector overflow correction;
- focused/full automated qualification, current-candidate journey rerun,
  evidence reconciliation, controlled canonical integration, and preservation
  restart of the local human-walkthrough runtime.

Out of scope and protected:

- AI, agents, GPS, new roles, new domain capabilities, new Request history,
  public tracking expansion, anonymous-account requirements, signup-host policy,
  domestic geography, Quote semantics, Request/Shipment identity, Shipment owner,
  assignment rules, database schema/data migration, unified login, sticky header,
  back-to-top, marketing redesign, and unproven Admin KPI redesign;
- Production access, credentials, database, deployment, migration, release, or
  release creation;
- mutation of the Product Owner's Customer, submitted Request, assignment, Quote,
  organization hostname, Province seed, or other walkthrough business data.

Stop conditions: any schema requirement; missing Product authority; changed or
dirty canonical identity; unrelated merge; inability to isolate qualification;
or a required gate that is not PASS. Human walkthrough remains `IN_PROGRESS`
and may never be set to PASS by this mission.

Definition of done: the six bounded defects are implemented without schema
change, security/privacy and preservation tests pass, full backend/frontend and
critical browser journeys pass on one exact clean candidate, evidence is bound
to Product and evidence SHAs, canonical fast-forwards with GitHub `0/0`, and the
owned walkthrough services run the new canonical code against the preserved DB.

## Entry evidence: FACT / ASSUMPTION / UNKNOWN

### FACT

- Canonical local and `github/integration/golden-controlled` both resolved to
  `4f4080cb1fd6970ec37a03f291162652fbb687af` after fetch; ahead/behind was `0/0`.
- The canonical checkout was clean and the historical Product SHA is an ancestor.
- Alembic reported exactly `20261012_phase3_cargo_eta (head)`.
- `ShipmentRequest.assigned_to` is the current Request assignment SOR and its
  `assigned_expert.full_name` is the minimal approved display source.
- Request create, referral assignment, and commit already occur in one governed
  transaction; the response is built only after commit returns.
- The current private Customer detail response omits route, current assignee,
  and special instructions even though the source Request already stores them.
- The current portal CTA points to `/`, the header always says Customer login,
  and portal navigation orders shipments before requests.

### ASSUMPTION

- No Product meaning beyond the exact mission wording is needed. Presentation,
  component extraction, narrow DTO shape, responsive layout, and test structure
  are delegated technical choices.

### UNKNOWN TO CLOSE DURING VERIFY

- Exact browser/CSS source of the observed horizontal overflow.
- Final exact candidate/evidence SHAs and owned qualification runtime identities.
- Whether any shared header change forces additional journey reruns beyond the
  complete P3-15 automated critical set already required by the mission.

## Product Authority Record

| Required field | Record |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Only `HW-DEFECT-001`, `HW-DEFECT-002`, `HW-UX-005`, `HW-UX-006`, `HW-UX-007`, and `HW-UX-008` exactly as described in the Product Owner mission. |
| `DELEGATED_TECHNICAL_CHOICES` | Minimal additive customer DTOs, safe serializer helpers, reuse/extraction of the existing chooser, local component CSS/layout, tests, fixtures, owned qualification topology, and evidence layout. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | All items listed in Out of scope above; especially anonymous intake, public tracking allowlist, Quote/history behavior, tenant/hostname binding, assignment rules, Shipment owner, and existing walkthrough records. |
| `DECISIONS_NEEDED` | None at entry. Any unexpected schema need or Product ambiguity becomes `DECISION_NEEDED / ARCHITECTURE_REVIEW_REQUIRED` and stops affected work. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner through the explicit bounded hardening mission; LPAF v2.7 for governance. |
| `APPROVAL_REFERENCE` | Attached request `Forwarder — HUMAN WALKTHROUGH BOUNDED RELEASE HARDENING`, sections 1–46. |

## Journey impact and verification contract

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
DIRECTLY_AFFECTED_JOURNEYS=FWD-J01,FWD-J02,FWD-J03,FWD-J08,FWD-IPJ-01,FWD-IPJ-03,FWD-IPJ-04
ADJACENT_REGRESSION=FWD-J06
REQUIRED_SLICE_RERUN=customer-request-hardening focused backend/frontend/browser set
REQUIRED_INTEGRATED_RERUN=FWD-J01..J09,FWD-IPJ-01..04
HUMAN_WALKTHROUGH_RERUN=PRODUCT_OWNER_CONTINUES; RESULT_IN_PROGRESS
```

Every material observable difference must be reconciled at Verify as
`AUTHORIZED`, `PRESERVED`, `VIOLATION`, or `UNKNOWN`. A `VIOLATION` or `UNKNOWN`
blocks integration. Automated PASS does not grant Human Product Walkthrough PASS
or Release Ready.

