# Proposed ADR: FWD-07 upload operation recovery

- Status: PROPOSED — no implementation authority
- Date: 2026-09-16
- Owners: Architecture/Business Owner; request document service owner
- Affected domain: existing request document upload orchestration and durability

## Context

The existing upload endpoint commits each CaseDocumentFile independently. CaseDocumentRequirement owns the logical requirement; private storage owns bytes. Browser fault injection forwarded a real upload, received 201, then dropped delivery. The UI declared the operation failed and advised selecting failed files again. Reopening showed the committed file; following that advice added a second active attachment with identical bytes and filename. Both downloads matched the source bytes. No upload endpoint was mocked.

## Problem

A lost response is an unknown result, not a definite rejection. No persisted operation identity currently distinguishes retry of one operation from an intentional new append. Filename/checksum matching cannot establish intent because intentional same-name/same-content append is valid. Mission sections 6 and 2 reserve consequential recovery-contract decisions. CODEX-DEVELOPMENT-GATE requires a proposal before architecture changes.

## Decision

PROPOSED FOR OWNER ACCEPTANCE ONLY: authorize an additive per-file operation identity contract within the existing request document service. A client keeps one identity across recovery of an unknown outcome; a deliberate append receives a new identity, even for identical bytes/name. Within trusted tenant/request/requirement/action scope, the server returns the original durable attachment for a replay without writing a second attachment. A reused identity with different content/action fails closed. Recovery must recheck current authorization; revocation cannot expose the old result. UI distinguishes saved, definite failure and unknown, retaining recoverable operation state. No DocumentArtifact/DocumentAttachment adoption, new permission, customer access, scanner waiver or FWD-08 work is proposed.

## Alternatives

- Blanket checksum/name deduplication: rejects legitimate independent append.
- Refresh and tell the user to inspect: does not prove which operation committed when identical attachments are permitted.
- Blind retry or text-only guidance: reproduced duplicate attachment.
- Remove retry assertions: conceals the acceptance gap.

## Consequences

Safe recovery requires durable correlation and explicit UI/API semantics. Storage/metadata concurrency, operation retention and reload recovery need qualification. This continuation does not select a schema or implement the proposal.

## Compatibility

An additive contract must specify behavior for older clients without an operation identity. Existing append/replacement semantics remain explicit. Acceptance does not activate proposed ADR-020.

## Migration impact

Likely additive durable operation metadata/uniqueness; exact design, retention, migration order and rollback compatibility require review. No migration executed by this continuation.

## Security/tenant impact

Trusted membership and authorized request parent remain authoritative. Operation identities are not capabilities. Replays require request-time authorization; scope/content mismatches fail closed. No token, cookie, storage key or private payload belongs in committed evidence.

## Operational impact

Unknown outcomes need bounded recovery and observable correlation without logging file content or credentials. No production or deployment authority is requested.

## Rollback

Retain committed files/history and correlation evidence. Older-runtime behavior and safe disabling of recovery require an accepted rollout/rollback plan; never delete successful attachments to hide retries.

## Validation

Real browser lost response after commit; same-operation replay creates one attachment; intentional identical append creates two; changed payload identity rejection; reload/reopen recovery; PostgreSQL races; storage/metadata rollback; authorization and revoked replay/download; desktop/mobile RTL and truthful per-file states.

## Supersedes / superseded by

- Supersedes: none
- Superseded by: none

## Status history

- 2026-09-16: PROPOSED after real controlled browser evidence. Minimum human action: accept or revise this bounded recovery contract and authorize its implementation; no environment/login intervention is needed.
