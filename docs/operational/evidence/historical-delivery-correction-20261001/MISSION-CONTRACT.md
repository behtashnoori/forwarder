# Historical Delivery Correction Compatibility — Mission Contract and Product Authority Record

## Governance entry

- **Mission date:** 2026-10-01 (Asia/Tehran)
- **Repository:** Forwarder
- **Governed baseline:** `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`
- **Entry level / route:** Level B remediation, Sol capability route
- **Starting Product SHA:** `fc4990f1b4b1fa7c6161fa821408165f9c727d91`
- **Finding:** `HW_DELIVERY_UX_002`
- **Known validation state:** Human Product Walkthrough = `IN_PROGRESS`; Product validation = `EVIDENCE_PENDING`

## Outcome and bounded scope

Correct the Delivery correction contract so a historical current Delivery whose destination identity consists only of `destination_text` can be superseded without retroactively binding or changing its destination. A correction that omits destination input inherits the previous destination columns and immutable snapshot exactly. An explicit replacement still requires and validates a structured destination. New Delivery behavior remains unchanged.

No walkthrough business command is authorized. Qualification uses isolated test data; after controlled source integration and runtime restart, the Product Owner remains the only actor who may retry the preserved correction.

## Facts, assumptions, unknowns, and decisions

### FACT

- The preserved current Delivery has quantity `95`, destination text `بندرعباس`, no structured location identity, revision `1`, and `is_final=false`.
- `DeliverySection` currently disables correction submission when `destination_reference` is null and always serializes a structured destination field.
- The Delivery service currently requires `destination_text` whenever a structured destination is absent, including correction commands, and therefore has no explicit “destination unchanged” command meaning.
- Delivery corrections are append-only rows linked through `supersedes_delivery_id`; model-level update/delete guards protect immutable history.
- Structured endpoint resolution already enforces Organization ownership for private logistics points.

### ASSUMPTION

- Omitting destination fields on a correction is the unambiguous command for preserving the predecessor's complete destination identity.
- Choosing a new value through the structured picker is the only supported destination-replacement action in the current UI.

### UNKNOWN

- Exact candidate qualification results remain unknown until tests and browser verification run.
- The Product Owner's manual retry result remains unknown and cannot be recorded by the agent.

### DECISIONS_NEEDED

`NONE` inside this bounded remediation. Stop if preserving omitted destination would require inference, migration, in-place mutation, weakening tenant checks, or changing new-Delivery requirements.

## Product Authority Record

### AUTHORIZED_PRODUCT_CHANGES

- Permit correction submission when an existing Delivery has no structured destination reference.
- Define omitted destination input on a correction as exact inheritance of the predecessor's `destination_text`, `destination_location_id`, `destination_logistics_point_id`, and `destination_snapshot`.
- Keep an explicit structured picker selection as destination replacement and apply the existing canonical/Organization validation to it.
- Add focused frontend, service, PostgreSQL, and read-only browser qualification for the six supplied cases.

### DELEGATED_TECHNICAL_CHOICES

- Optional command-field representation, destination-change tracking in the form, service helper boundaries, regression fixtures, and evidence packaging.

### PROTECTED_OUT_OF_SCOPE_BEHAVIOR

- Do not infer `بندرعباس` or any free text into canonical geography.
- Do not migrate, backfill, normalize, or auto-bind historical destinations.
- Do not update or delete an existing Delivery; corrections remain append-only superseding facts.
- Do not weaken canonical geography or cross-tenant logistics-point validation.
- Do not relax the structured-destination requirement in the new-Delivery UI.
- Do not alter quantity, occurrence time, destination note/text, structured identity, or finality unless the correction command explicitly changes the applicable non-destination field or explicitly replaces destination.
- Do not perform a command against the preserved Shipment or Delivery during automated qualification.
- Do not access Production, deploy, or create a release.

### APPROVING_OWNER_OR_AUTHORITY

Forwarder Product Owner through the supplied 2026-10-01 defect-remediation mission.

### APPROVAL_REFERENCE

User mission: `FORWARDER — FIX HISTORICAL DELIVERY CORRECTION BLOCKER` / `HW_DELIVERY_UX_002`.

## Journey impact and verification contract

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`

Affected areas: `FWD-J02`, `FWD-J04`, `FWD-J08`, `FWD-J09`, and `FWD-IPJ-04` Delivery correction and tenant-isolation behavior. The Product Owner-controlled critical-journey set is unchanged.

Required qualification:

1. Historical free-text Delivery, final-only correction: accepted; destination identity and all unedited facts preserved.
2. Historical free-text Delivery, quantity-only correction: accepted; destination identity preserved.
3. Historical free-text Delivery, explicit destination replacement: structured validation applies.
4. New Delivery: structured picker remains mandatory in the UI.
5. Already-structured Delivery correction: identity is inherited exactly unless intentionally replaced.
6. Cross-tenant destination replacement: refused.
7. Append-only predecessor/successor history, version conflict, authorization, frontend type/build/lint, and database preservation checks remain green.

Browser verification on the preserved runtime is read-only: confirm the existing correction form is enabled without selecting geography after the integrated runtime restarts, then cancel or leave the form without submission.

## Definition of done and stop conditions

- All six qualification cases pass on the exact candidate.
- The preserved database's normalized data-only hash and target Delivery projection match the pre-change snapshot after runtime integration and read-only browser verification.
- `WALKTHROUGH_BUSINESS_ACTIONS_PERFORMED=0` and the Product Owner retains the manual retry.
- Human Product Walkthrough remains `IN_PROGRESS`; no agent-authored human PASS, Production, deployment, or release claim is permitted.

## Entry decision

`AUTHORIZED_TO_PROCEED_WITHIN_SCOPE`

PDA-07: compatibility behavior and focused evidence are `AUTHORIZED`; destination identity, append-only history, tenant isolation, new-Delivery requirements, preserved walkthrough data, and release boundaries are `PRESERVED`.
