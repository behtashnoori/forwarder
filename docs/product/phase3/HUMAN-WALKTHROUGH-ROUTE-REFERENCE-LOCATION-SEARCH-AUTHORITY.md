# Human Walkthrough — Route Reference canonical location search remediation

Date: 2026-09-29. Governing repository entry baseline: LPAF v2.6. Rigor:
Level B. Capability route: Sol.

## Mission and authority

Outcome: restore the Organization Admin Route Reference picker so the preserved
canonical Isfahan and Bandar Abbas identities are searchable in Persian, while
search text remains presentation-only and new Route References continue to
persist a canonical location foreign key.

The Product Owner's supplied mission authorizes the bounded search correction,
the minimum loading/empty/error/selected states, and selection of country-bound
canonical matches. It does not authorize geography or ETA redesign, Shipment IA
change, automatic Route Reference creation, historical rewrite, Production
access, deployment, or release.

## Product Authority Record

| Field | Record |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Persian search returns existing country-consistent canonical Isfahan and Bandar Abbas choices; a bound Iranian UN/LOCODE may be selected; the picker exposes explicit loading, empty, error and selected states. |
| `DELEGATED_TECHNICAL_CHOICES` | Existing source adapters, legacy Province compatibility, request composition, localized labels, tests and evidence mechanics. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | No new geography rows, name-based identity merge, unbound legacy selection, free-text endpoint identity, Route Reference auto-creation, ETA/Shipment IA change, Production, deployment or release. |
| `DECISIONS_NEEDED` | None: runtime evidence proves both canonical identities already exist and the defect is filtering/request composition rather than a missing authoritative record. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner. |
| `APPROVAL_REFERENCE` | `FORWARDER — ROUTE REFERENCE CANONICAL LOCATION SEARCH BLOCKER`, supplied 2026-09-29. |

## Current-state evidence and target chain

The preserved runtime contains canonical Province Isfahan and a canonical,
UN/LOCODE-bound `InternationalCity` Bandar Abbas. Search excluded the former
because the legacy domestic Province row has nullable Country ancestry, and the
frontend never requested the latter's source type. The target chain is:

Country -> trimmed Persian query -> eligible source search -> country check ->
localized option -> selected source identity -> canonical resolver -> persisted
`OrganizationRouteTime.origin_location_id` / `destination_location_id`.

Unbound `InternationalCity` rows remain readable historically but are not
returned or accepted for new Route References. PDA-07 target: the search and UX
differences are `AUTHORIZED`; all named out-of-scope behavior is `PRESERVED`.

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`: FWD-J06, FWD-J08, FWD-J09,
FWD-IPJ-03 and FWD-IPJ-04 require applicable regression evidence. Human Product
Walkthrough remains `IN_PROGRESS`; this remediation cannot grant its PASS.
