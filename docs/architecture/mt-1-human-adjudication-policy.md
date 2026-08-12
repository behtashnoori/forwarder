# MT-1 human adjudication policy

> **Dataset-specific status (2026-08-12):** This general real-data policy remains
> in force, but it is not applicable to the hash-bound 135-row `SYNTHETIC_ONLY`
> dataset. Review packages are historical evidence and must not receive invented
> Organization IDs.

Human mapping is reviewed evidence, never an override. There is no precedence,
default tenant, session fallback, or inference from names, companies, email,
users, departments, phone numbers, or free text. Only stable entity type and
positive internal ID identify a decision subject.

Allowed decisions are `ASSIGN_TO_ORGANIZATION`, `KEEP_QUARANTINED`,
`RETIRE_INACTIVE_LEGACY_ROW`, `REDESIGN_REQUIRED`, and
`NEEDS_MORE_EVIDENCE`. Assignment requires a valid existing Organization ID
and an authoritative evidence reference. Retirement is policy disposition only
and deletes nothing. `REDESIGN_REQUIRED` is the natural default consideration
for structurally ambiguous singleton/platform-like state such as
`ReferralAutoAssignState`; it is not an ownership assignment.

Every approved decision requires two distinct reviewers, timestamp, positive
decision version, stable decision ID, and evidence reference. A successor names
its predecessor; superseded history remains auditable. Later conflict evidence
cannot be erased by an earlier human assignment. Any row without explicit,
validated approval remains quarantined. Approval of a review row does not
itself apply a mapping, clear quarantine, migrate data, or authorize backfill.

`decision_status` is one of `PENDING`, `IN_REVIEW`, `APPROVED`, `REJECTED`, or
`SUPERSEDED`. Only `APPROVED` decisions may be considered for a future mapping
translation, and that translation requires separate schema validation,
analyzer rerun, PostgreSQL certification, and independent security review.
