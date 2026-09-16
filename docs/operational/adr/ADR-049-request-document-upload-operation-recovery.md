# ADR-049: Request document upload operation recovery

- Status: PROPOSED — OWNER ACCEPTANCE REQUIRED
- Authority: NO RECOVERY IMPLEMENTATION AUTHORITY
- Date: 2026-09-16
- Owners: Architecture/Business Owner; `case_document_service` maintainer
- Domain: bounded existing ShipmentRequest document upload orchestration

## 1. Context and problem

The [original proposal](../evidence/fwd-07-document-attachments/PROPOSED-UPLOAD-RECOVERY-ADR.md), SHA256 `A88834429A659F7ED6A4959C5DA940D42D5D8A644C596333F138140590D72F53`, remains unchanged. [Lost-response evidence](../evidence/fwd-07-document-attachments/CONTINUATION-20260916.md) and [safety report](../evidence/fwd-07-document-attachments/SAFETY-20260916-6e9eb4df52b4/FINAL-REPORT.md) report a real backend commit/201 followed by dropped delivery; retry created another attachment. Historical browser environment correlation is unproven; this observation is not a new correlated runtime qualification.

A lost response means unknown outcome. Filename/checksum cannot infer user intent. All decisions below are proposals, not existing Accepted semantics. ADR-010 supplies general replay/conflict principles; ADR-006/011/014/015/016 and current authorization/document contracts remain binding. LPAF v2.2 is globally active; v2.4 is owner-approved pilot only. Mother framework impact: NONE. Project architecture impact: this new proposal/index entry only. Reference28 mapping remains NOT_PROVEN under the existing bounded FWD-07 deferral.

## 2. Ownership and boundary

`case_document_service` owns operations, durable receipts, public command/query contracts and DB transaction coordination. `CaseDocumentRequirement` remains logical document owner; `CaseDocumentFile` remains file/version metadata owned by the source request; private storage owns bytes. Miscellaneous files retain their existing request ownership and null requirement. No invented requirement is created for them.

Use a new document-owned operation table. Do not reuse `OperationalIdempotency` or tracking receipts directly: their current tracking seam covers transactional metadata results, not byte staging, claims, storage crashes or document replacement. Private storage exposes operation-scoped staging/promote/verify/cleanup primitives to the document owner; UI never writes ORM or storage truth. No generic queue/recovery framework is proposed.

## 3. Identity and payload binding

Before network send, the authenticated UI generates a cryptographically random UUID v4 per selected file, canonical lowercase 36-character form, validates version/variant, computes SHA256/length, and durably records the pending manifest before sending. Scope: trusted tenant, authorized request, requirement or miscellaneous discriminator, APPEND/REPLACE, explicit replaced-file identity, and initiating authenticated actor. Server uniqueness is `(organization_id, operation_uuid)`; reusing a tenant key with another target/action/actor conflicts after authorization. Cross-tenant queries are non-disclosing. Collision requires a fresh deliberate operation only after establishing that this unsent identity collided; never rotate an unknown sent identity automatically.

Proposed prepare command: `POST /api/expert/requests/{request}/document-upload-operations`, with identity and fixed manifest. Request names here describe the proposed expert seam, not implemented routes. Fingerprint is SHA256 of versioned UTF-8 canonical JSON: sorted keys, no insignificant whitespace, NFC strings, existing effective filename sanitization, title/description trimming/null rules, byte SHA256, byte length, validated format, effective metadata, target, action and replacement target. Record normalization version 1. Reject unknown effect-bearing fields. Server recomputes effective values; client digest/format are claims until server validates received bytes, size, extension and content. Multipart transport boundaries and server-generated timestamps/storage keys are excluded.

Prepare returns 201 RESERVED, or 200 for same key/same manifest; same key/different effective payload returns 409 OPERATION_PAYLOAD_CONFLICT without modifying the original. The byte-send command uses the same identity. Different received bytes fail closed with 409, preserving the operation binding; no attachment results. Correcting a definitively rejected payload is an explicitly new operation. Independent identical append always uses a new UUID and remains permitted. No global/cross-tenant checksum deduplication.

## 4. Lifecycle and API results

| State | Allowed transition and meaning |
| --- | --- |
| LOCAL_PREPARED | Client-only durable identity; prepare/send with that identity |
| RESERVED | Server bound manifest; acquire fenced claim to RECEIVING |
| RECEIVING | One claim receives/validates bytes; to STAGED, REJECTED, or reconcile after lease expiry |
| STAGED | Verified operation-owned bytes; authorized finalization to SUCCEEDED; recoverable infrastructure failure retains STAGED |
| SUCCEEDED | Immutable receipt/file result; replay never writes or reactivates |
| REJECTED | Definitive validated failure with stable code and no committed attachment; same identity cannot change payload |
| EXPIRED | Permanent non-reuse tombstone; no new write under that identity |
| UNKNOWN | Client observation only after timeout/disconnect; query/reconcile, never presume server rejection |

Proposed `GET .../document-upload-operations/{uuid}` reauthorizes and returns state. RECEIVING/STAGED return 202 with bounded Retry-After; no result is not proof of absence while the first request runs. An authenticated same-scope missing key returns 404 OPERATION_NOT_FOUND; the client may prepare that same persisted identity, never silently issue a new one. Finalized first send returns 201 and opaque file public identity/version; replay returns 200 with the same operation and file identities, `replayed=true`, and freshly projected current file status/download availability. Receipt does not contain a cached private download URL. Expired identity returns 410 OPERATION_EXPIRED and, when authorized, its historical result identity/status; never a new upload. Authorization-denied responses reveal no operation existence.

## 5. Reopen and client state

Keep minimal pending manifests in IndexedDB scoped to authenticated user and tenant: UUID, opaque request/requirement/replacement identity, action, normalization version, effective metadata, filename, byte length/digest, creation Instant and last observed state. Store no credentials, cookies, private URL/storage key or file bytes. This state is private local data, never exported to evidence. Refresh/tab closure/browser restart recovers within the same browser profile while that state exists. Logout clears scoped pending state; account/tenant switches cannot consume another scope's state. Authentication lifecycle never deletes server operations or documents.

After logout or local-state loss, an authorized initiating actor can use a bounded request-scoped operation-list query to find their pending/recent operation identities and manifest summaries for 90 days. No cross-actor receipt discovery is granted. Reauthorization and explicit user confirmation reconnect a reselected file to an operation; server verifies the full fingerprint. Reselecting bytes is needed only for RESERVED/incomplete RECEIVING with no verified durable bytes. Bytes are never presumed recoverable from the browser. If correlation cannot be established, show unresolved outcome and document inspection/support guidance; do not invent a key and label it Retry. Fresh intentional append remains a separate explicit action after warning about unresolved prior outcomes. No claim of automatic recovery across lost profiles/devices or cleared state beyond server discovery retention.

## 6. Live authorization and replacement

Prepare, byte-send, query, replay, reconcile/finalize and download independently check active actor, membership, trusted tenant, authorized request and current assignment/governed authority. A worker rechecks initiating authority before finalization; infrastructure credentials cannot supply missing user authority. Identity/old success is not capability. Revoked or reassigned original actors receive non-disclosing denial; newly assigned actors retain ordinary document access but cannot impersonate the initiating operation. Scope mutation conflicts. Expired sessions require reauthentication, not upload cancellation.

Replacement records an exact active file target within the same requirement/request/tenant. First successful finalize supersedes only that target and appends normal version/audit history atomically. A target changed by another operation causes definitive 409 REPLACEMENT_TARGET_CHANGED; no latest-version substitution. Retry of a successful replacement returns its original result even if subsequently superseded/deleted, with current availability; it never supersedes again. Current ordinary download rules decide access to historical versions. Deleted/unavailable bytes are reported unavailable; replay never restores them or advertises stale URLs.

## 7. Database/storage consistency and crashes

1. Prepare commits RESERVED manifest/identity after authorization.
2. Short row-lock transaction claims RECEIVING with random claim token, monotonically increasing generation and five-minute lease. Active claim returns 202. Heartbeat extends lease for bounded active reception; stale recovery obtains the row lock and increments generation. Every publish/finalize checks generation/token; stale workers cannot publish.
3. Receive to private generation-scoped temp path, bounded size; validate all bytes and recompute fingerprint; fsync bytes. Invalid payload durably rejects without attachment. A DB transaction records verified staging locator/digest/length and STAGED only for the current claim.
4. Lock operation and the document requirement (or request for miscellaneous); reauthorize, validate replacement/count/version and current claim. Promote verified bytes to deterministic private tenant/request/operation destination (generation appears only in staging paths) with no-overwrite semantics and durable directory synchronization, or the object-storage equivalent. A pre-existing destination must match trusted digest/length; mismatch quarantines for owner reconciliation.
5. In the same DB transaction create exactly one file, normal supersession/audit and immutable receipt fields; commit SUCCEEDED. Only then respond. DB/storage are not one atomic transaction.

| Crash interval | Durable remainder; responsible recovery |
| --- | --- |
| Before prepare commit | No operation/result; repeat same prepare identity |
| After prepare/claim, before verified stage | RESERVED/RECEIVING; partial generation bytes only; stale-claim recovery fences owner and requires same bytes if incomplete |
| After temp fsync, before STAGED commit | Unreferenced generation bytes; fenced document reconciler validates against bound manifest before adopting or deleting only that generation |
| After STAGED commit, before promotion | Verified staged bytes; authorized owner resumes same operation |
| After promotion, before DB commit | Deterministic orphan final bytes; locked reconciler verifies and resumes original identity; no second final effective file |
| After DB commit, before/lost response | SUCCEEDED/file/receipt/audit durable; query/replay returns same file without storage write |
| Later missing/corrupt committed bytes | Keep receipt/history; unavailable/integrity incident, never silently create another attachment |

Unique file-to-operation relation and locked generation checks prevent two effective attachments under PostgreSQL races. Filesystem losers may leave fenced temporary generations. All generations share one no-overwrite final destination for that operation; a valid orphan there is reused, never promoted to another final key. Thus races cannot create two final byte objects or effective relationships for one operation. Operation-scoped reconciliation runs through the document owner on recovery/admin maintenance, not a new general job engine. Cleanup requires fenced ownership and positive absence of committed references, respects holds, and never deletes committed bytes/history. No cleanup is authorized here.

## 8. Compatibility, retention and expiry

Older clients without identity retain existing append/replacement behavior but receive no recovery guarantee. Retry guidance must describe unknown outcome and prohibit automatic resend; do not imply deduplication. Deploy additive backend first, then identity-aware UI under a bounded flag. N-1 cannot process identity-bearing commands: rollout disables them explicitly rather than stripping the identity and falling through. Existing owner/permission/lifecycle remains unchanged.

Propose 90 days of full operation manifest/discovery from prepare to cover extended request workflows without browser byte retention; completed receipt and minimal non-reuse tombstone persist with document audit history, with no automatic deletion in this slice. Five-minute claims are concurrency leases, not operation/document expiry. After 90 days incomplete operations become EXPIRED only after fenced reconciliation establishes no committed result; uncertain storage/DB outcomes remain pending reconciliation. Expiry may remove rich manifest/discovery eligibility, never key/hash/scope/result correlation or document history. Late retries return historical result/410 and cannot create duplicates. Closing a window/network timeout never expires a document. This policy requires Owner acceptance; it is not acceptance of general PDR-011 retention/purge.

## 9. Proposed schema, migration and rollback

New `case_document_upload_operation`, owned exclusively by the document service:

| Fields | Proposed types/constraints |
| --- | --- |
| id; operation_uuid | BIGINT PK; UUID NOT NULL, unique with organization_id |
| organization_id; request_id | BIGINT NOT NULL trusted tenant/request references; restrictive deletion, no cascade cleanup |
| requirement_id; target_kind | nullable BIGINT requirement reference; VARCHAR(16) REQUIREMENT/MISC; check requirement null iff MISC |
| actor_id; authority_snapshot | internal actor reference nullable on existing permitted actor deletion; immutable non-secret JSON authority context, never replay authority |
| action; replacement_file_id | VARCHAR(8) APPEND/REPLACE; scoped file reference required iff REPLACE |
| fingerprint_version; payload_hash; bytes_sha256; bytes_length; manifest | SMALLINT=1; CHAR(64) hashes; positive BIGINT length; private JSON effective manifest |
| state; claim_generation; claim_token; lease_until | constrained VARCHAR(16); BIGINT >=0; nullable UUID; nullable timestamptz with coherent claim envelope |
| staged_locator; final_locator | nullable private TEXT, internally generated, never public/evidence |
| result_file_id; receipt_version; completed_at; failure_code | nullable scoped file reference UNIQUE; SMALLINT; timestamptz; bounded VARCHAR(64); SUCCEEDED requires result/receipt/completion |
| created_at; updated_at; expires_at | NOT NULL timestamptz UTC Instants; 90-day window is Duration |

Receipt consists of immutable operation/scope/hash/result/completion fields in this same row, atomically written with file/audit. Add nullable unique `CaseDocumentFile.upload_operation_id` reference; enforce reciprocal result linkage at finalize and PostgreSQL scoped composite FKs for request/requirement/replacement/result ownership, adding parent composite uniqueness where needed without changing identities. Actor deletion leaves attribution unknown and prevents actor replay; never infer a replacement actor. Index request/actor/created_at for bounded authorized discovery and state/lease for reconciliation. Constraints must preserve quarantine/legacy-null envelopes of existing tables.

Design predecessor is actual sole graph head `20260916_fwd06_tracking_time`, whose predecessor is `20260916_fwd05_quote_response`; reattest before implementation if graph changes. No executable migration/schema is created now. Later explicit additive upgrade creates the table/indexes/constraints and nullable file link; old files retain null operation identity, with no filename/checksum/intent backfill. Preserve every file, relationship and audit. Rehearse existing-row preservation, empty downgrade and populated refusal. Application rollback retains schema/receipts/staging and disables new identity writes/recovery with explicit unavailable responses; never route pending identity commands through legacy upload. Database downgrade refuses before any DDL when operations/links exist. Successful attachments are never deleted to conceal duplicates.

## 10. Alternatives, consequences and operational controls

Reject blanket checksum/name deduplication, blind retry, browser-only keys and memory-only receipts. Reject direct tracking-receipt reuse and a generic recovery engine. Dedicated operation persistence costs schema, storage reconciliation, locking and client-state privacy management; it explicitly closes the byte/metadata gap while preserving intentional append. Storage durability guarantees must be qualified on the actual supported provider; unsupported atomic/no-overwrite guarantees block enablement. Logs contain opaque operation/state/code/timing only, no credentials/file content/private locators. Existing upload size/count/rate controls remain; bounded polling/backoff and prepared-operation quotas prevent receipt abuse. No deployment or Production action is authorized.

## 11. Validation after named acceptance

Real backend/private storage and run-owned PostgreSQL; no mocked backend response: forward successful upload, lose delivery after actual commit, recover same identity with exactly one attachment and matching downloaded bytes. Intentional identical name/bytes with two UUIDs creates two. Changed bytes/metadata/action/target conflicts without mutation. Test restart, refresh/reopen, logout/state-loss discovery, reselect mismatch, active first request, missing prepare, collision, expiry/late retry and explicit legacy limitation. Exercise simultaneous claims/replays, stale-worker fencing, replacement races, every crash interval above, storage failure/missing bytes, transaction rollback and scoped orphan cleanup. Revoke/reassign/cross-tenant read/replay/finalize/download must disclose no private result or revive old files. Desktop/mobile RTL display real per-file saved/definite failure/unknown/pending/expired/unavailable states. Explicit migration upgrade/history preservation/populated downgrade refusal and N/N-1 disabling require evidence. Feasibility and this plan are not runtime PASS.

## 12. Owner decision and status history

Preferred decision: accept this entire bounded contract including dedicated persistence, initiating-actor recovery, 90-day discovery and durable non-reuse history; authorize implementation separately. Alternatives: retain unresolved unknown outcomes with manual inspection and no recovery guarantee, or request another bounded design; neither closes FWD-07. Exact Owner question: “Do you accept ADR-049 at the delivered SHA256, including its retention/privacy trade-off and bounded legacy document seam, and separately authorize local implementation/qualification?” No runtime work proceeds on silence or test success.

Excluded: ADR-020 acceptance, customer visibility, scanner waiver, new permissions/product lifecycle, canonical cutover, FWD-08/maps, real messages/LLM providers, historical database remediation, release/Production. Supersedes: none. Superseded by: none. Prior Accepted records are not declared superseded.

- 2026-09-16: PROPOSED linked successor to the preserved original proposal. OWNER ACCEPTANCE NOT_RECEIVED. RECOVERY_RUNTIME_IMPLEMENTED: NO. FWD07_COMPLETE: NO.
