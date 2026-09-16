# FWD-07 — Multi-file request-document attachments

Recorded 2026-09-16, Asia/Tehran. This is local implementation and qualification evidence.

## Governing record

- PRIMARY_MODULE_AND_OWNER: request document service and `CaseDocumentRequirement`; the requirement is the logical business document and `CaseDocumentFile` is one immutable physical attachment/version belonging to it. Private storage owns bytes only.
- AFFECTED_CONTRACTS: existing expert request document list, individual upload, replacement, download and delete endpoints; `CaseDocumentsTab` presentation. No new endpoint, schema, storage provider, permission, customer projection or canonical owner was introduced.
- APPLICABLE_LPAF_RULES: ACTIVE LPAF v2.2 and its Agent Entry Protocol; explicit mission pilot use of v2.4 MOD-01–03, QUAL-01–05 and ADOPT-01/02. v2.4 SHA-256 was verified as `217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397`; it remains OWNER_APPROVED / PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE. Mother framework impact: NONE. Project reference impact: UPDATE_REQUIRED (this record and decision index).
- REFERENCE_MAPPING: NOT_PROVEN. The mission’s bounded 28-AI-Rules deferral applies only to local FWD-07 development/qualification; it is neither a framework mapping nor a security or production waiver. Re-review is due at FWD-07 completion or before release, whichever occurs first.

## Focused discovery

| Need | Disposition | Owner | Change | Test |
| --- | --- | --- | --- | --- |
| One logical document with many files | EXISTS | `CaseDocumentRequirement` | Reuse `active_files` and configured max count | real API upload/reopen/download |
| Immutable physical file | EXISTS | `CaseDocumentFile` | No schema change; same-name files receive distinct generated keys | byte and digest assertions |
| Batch selection with truthful results | EXTEND | CaseDocumentsTab | Sequential independent submissions and per-file saved/failed state | component and API tests |
| Persian display filename | EXTEND | document validation | Preserve safe Unicode metadata; never use it as a storage key | real API round trip |
| Private authorized retrieval | EXISTS | case-document route/storage | Reused request access check, file/case match, private root and audit | existing authorization suite |

`append` is an ordinary new active attachment. `replace` remains the existing explicit action that supersedes the current active version. Delete behavior is unchanged. A failed file does not roll back valid prior attachments; retry means selecting only failed files. There is no new batch transaction or idempotency contract: each existing upload endpoint transaction is the durability boundary.

## Scope and security

Server-side allowlists, detected content checks, empty/oversize/path traversal controls, generated storage keys, private root, request-time authorization and audit are reused. No scanner was run: `SCANNER_STATUS=NOT_RUN`. Customer visibility is not added. Public tracking and quote bearer capabilities do not grant document access. No preview, signed URL, public URL, OCR, LLM/API, ZIP, archive extraction, new deletion authority, document approval or readiness transition is introduced.

## Qualification

Run from repository root:

```powershell
python -B -m pytest -q --tb=short --disable-warnings -p no:cacheprovider backend/tests/test_case_documents.py backend/tests/test_case_documents_fault_injection.py
npm run test:frontend -- --run src/tests/components/CaseDocumentsTab.test.tsx
npm run build
```

Focused results: backend `40 passed`; UI `3 passed`; production build passed. The API test uses the actual Flask routes, SQLite disposable database, temporary private storage, authenticated expert, persisted reopen and downloads; no upload/authorization/download API is mocked. PostgreSQL qualification and browser UAT are NOT_RUN. Existing FWD-06 timeline scope was not changed.

## Intentionally deferred

ADR-020’s proposed cross-scope `DocumentArtifact`/`DocumentAttachment` model remains proposed and is not activated. Canonical shipment/unit/event ownership, customer visibility, scanner/quarantine certification, PostgreSQL concurrency, historical migration, production identity/security, Reference 28 mapping, recipient onboarding and real customer delivery remain open.

## Continuation evidence, 2026-09-16

The historical results above remain unchanged. [Continuation report](CONTINUATION-20260916.md) records the exact selector defect, mobile reachability repair, completed two-viewport browser journey, five executed PostgreSQL race tests, gate failures and a broad-run test-database setup caveat. Final mission status is **BLOCKED_RECOVERY_CONTRACT**: a real saved upload with lost response is labeled failed, and following the retry guidance creates a duplicate attachment. See [bounded proposed decision](PROPOSED-UPLOAD-RECOVERY-ADR.md). It is not an accepted contract or ADR-020 activation. Raw traces, sessions and downloads remain outside Git.
