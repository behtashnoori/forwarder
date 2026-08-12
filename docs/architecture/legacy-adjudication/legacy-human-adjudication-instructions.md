# Legacy human adjudication instructions

Review one stable entity ID at a time. Legitimate assignment evidence must be a
durable authoritative relationship to an existing Organization, supported by a
reference another reviewer can independently verify. Do not use names, company
labels, email, phone, username, department, assignee identity, or free text.

`ASSIGN_TO_ORGANIZATION` requires a target Organization ID and evidence.
`KEEP_QUARANTINED` records that no safe ownership decision is currently
available. `NEEDS_MORE_EVIDENCE` requests bounded evidence collection without
changing quarantine. `RETIRE_INACTIVE_LEGACY_ROW` proposes policy treatment for
mechanically proven inactive/historical data and never deletes it.
`REDESIGN_REQUIRED` identifies state whose structure cannot truthfully express
tenant ownership, especially singleton/platform-like legacy records.

Reviewer 1 proposes and documents the decision. Reviewer 2 independently
checks the stable subject, evidence, target existence where applicable, and
absence of weak inference. They must be distinct people. Only then may status
become `APPROVED`, with timestamp, version, decision ID, and evidence reference.
Rejected and superseded decisions remain in history.

No row may be unquarantined merely because this workbook is completed. Approved
rows must first pass the validator and future mapping-schema translation,
analyzer rerun, PostgreSQL certification, and independent security review.
