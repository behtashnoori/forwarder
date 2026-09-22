# Forwarder v1.10.0 Release-Gate Contract Reconciliation — 2026-09-22

## Governance, mission, and authority

The active normative baseline is LPAF v2.2 with its mandatory Agent Entry Protocol. This is a Level B Production-release tooling mission. Applicable lifecycle stages are M0/M1, M6, M7, and M9: establish authority and current facts, preserve exact candidate identity, prove recovery separately from success, keep Production decisions human-reserved, and promote the discovered gate defect into regression control. The reviewed v2.3 Product Integration / `REFERENCE_IMPACT` guidance is applied as a strong default.

The mission was limited to the read-only collector, backup/restore evidence contract, validate-only/deployer gates, operator bundles, tests, and handoff. Product runtime, business behavior, migrations, reference/master data, and Production state were out of scope and unchanged. Codex did not access Production and did not execute deployment.

## Facts, assumptions, unknowns, and decisions

**FACT:** the operator-reported fresh collector result had `collector_status=PASS`, `collection_errors=0`, restore evidence present/available, `restore_evidence.state=VERIFIED_METADATA`, and no Production mutation, but still reported `fresh_deployment_window_backup_present=false` and aggregate `BLOCKED_FRESH_BACKUP_AND_RESTORE_PROOF_REQUIRED`.

**FACT:** the transferred pre-Execute dump is 946282 bytes with SHA256 `96399479ee125d2e21402b7f8d77b2d269933c2baf8d786164930b226bc341ea`. Its backup evidence and isolated restore evidence bind to that same hash. The restore evidence records the exact baseline and target revisions, the five-migration sequence, post-migration assertions, ADR-047 PASS, disposable database removal, and no Production access/mutation/deployment.

**FACT:** the collector initialized `fresh_deployment_window_backup_present=false` and had no transition capable of making it true. Its aggregate nevertheless required the field. The deployer checked only `collector_status`, not the blocked aggregate, and created another backup only after entering Execute and containing writers.

**FACT:** the original twelve-phase deployment plan requires a fresh backup after writer containment and before migration. The later restore-proof procedure separately requires an exact Production-derived backup and isolated restore/migration rehearsal before validate-only. These are two different moments and purposes.

**FACT:** the proven Production environment uses the SQLAlchemy `postgresql+psycopg2://` URL form. The deployer's post-migration read-only verifier still accepted only plain PostgreSQL URL schemes, which would have failed after migration. The same bounded correction now supports the proven URL and passes `sslmode` through `PGSSLMODE` without exposing credentials.

**ASSUMPTION:** the human operator preserves the existing exact dump, backup evidence, hash/catalog sidecars, and restore-evidence sidecar under the approved protected backup root for the corrected collector rerun.

**UNKNOWN:** a corrected live `r5` collector result does not yet exist. The future Execute-time backup timestamp, SHA256, and size are necessarily unknown until writers are contained and that checkpoint is created. Human GO, maintenance-window authority, and Execute authorization remain absent.

**DECISION NEEDED:** after `r5` returns `READY_FOR_SEPARATE_GO_REVIEW`, the release authority must separately decide whether preparation may advance to zero-mutation validate-only. Validate-only PASS is not Execute authority.

## Authoritative contract decision

Option 3 is selected: represent two explicit, non-interchangeable gates.

Option 1 alone is rejected because treating the restore-proven pre-Execute dump as though it were the later deployment-window checkpoint would make the collector assert a future fact. Option 2 as a universal requirement is not the existing v1.10.0 plan: it would require writers to remain contained while the exact second dump is transferred and restored before migration. That stronger policy remains available to the release authority, but it is not silently invented here.

The authoritative sequence is:

1. The read-only collector proves current runtime/database/configuration facts and an exact, fresh Production dump whose backup evidence and isolated restore/migration proof all match the dump's calculated SHA256 and fixed release identities.
2. Only then may it report `deployment_prerequisite_status=READY_FOR_SEPARATE_GO_REVIEW`. It must still report `fresh_deployment_window_backup_present=false` because Execute has not begun.
3. Validate-only accepts only that aggregate READY state and the underlying exact-dump proof fields. It remains zero mutation.
4. Separate human GO and maintenance-window authority remain mandatory.
5. Execute contains writers, records containment time, creates a new backup, and refuses migration unless the new checkpoint was created after containment and passes exact baseline revision, PostgreSQL major, size, SHA256, sidecar, catalog, owner, retention, path, and zero-mutation checks.
6. The deployment baseline records both identities: the pre-Execute restore-proven dump hash and the Execute-time rollback-checkpoint path/hash/size/timestamp.

The isolated restore requirement is not weakened or bypassed. It is made stronger by calculating the source dump hash in the collector and validating the complete backup and restore contracts instead of accepting metadata shape alone. The Execute-time checkpoint also remains mandatory; it no longer falsely blocks the earlier gate before it can exist.

## Explicit reconciliation

| Concern | Reconciled contract |
|---|---|
| Fresh backup identity | The pre-Execute dump is accepted only when filename timestamp, protected path, evidence JSON, size, calculated SHA256, hash sidecar, catalog sidecar, host, application identities, PostgreSQL 18 identity, and exact baseline revision agree within the 8-hour freshness window. |
| Restore-proof identity | `VERIFIED_EXACT_DUMP` requires the same calculated dump SHA256/size plus exact source/target revisions, application source, frozen package SHA256, five migrations, assertions, ADR-047, disposable cleanup, and false Production access/mutation/deployment declarations. |
| Deployment-window timing | A different checkpoint is created only inside Execute after writer/listener containment and before migration. Its timestamp must be later than both containment and the restore-proven pre-Execute backup. |
| Rollback viability | The first dump supplies exact isolated recovery and migration proof. The second supplies the closest contained-state rollback point and verified archive/catalog/hash identity. Restore is never automatic; B/C recovery remains a release-owner/DBA decision with data-loss review. If exact-second-dump restore proof is required, migration must remain blocked while writers stay contained until that proof is completed. |
| Validate-only semantics | Requires aggregate READY and exact underlying proof fields, but creates no target, backup, database change, task/IIS change, or state-file change. No bypass exists. |
| Execute preconditions | Fresh collector age/host, collector PASS/no errors, exact pre-Execute backup/restore proof, runtime/database/configuration/ADR-047/capacity/topology gates, explicit deployment confirmation, restore owner, and separate human authority. Execute then has its own mandatory post-containment backup gate. |
| Fail-closed behavior | Missing/stale/malformed evidence, hash/size/path/revision/package/chronology mismatch, blocked aggregate, topology drift, or failed window backup stops before migration. Post-migration failure contains writers and requires DBA/release-owner action. |

## Bounded correction and regression promotion

- Collector `r5` calculates and exposes the latest dump SHA256, validates backup evidence and sidecars, validates the full restore/migration proof, separates the pre-Execute and Execute-time gates, and projects one internally consistent aggregate.
- Deployment tooling `r3` enforces aggregate READY and the underlying exact proof, preserves zero-mutation validate-only, records both backup identities, enforces post-containment timing, and supports the proven SQLAlchemy PostgreSQL URL plus `sslmode`.
- The frozen Product package was not rebuilt. The corrected deployer at the deployment-bundle root is the sole operator entrypoint; package-internal historical tooling is not authoritative.
- Regression coverage now proves valid exact identity, mismatched-hash rejection, blocked-aggregate rejection, validate-only zero mutation, post-containment checkpoint timing/recording, failure containment, SQLAlchemy URL handling, bundle separation, and frozen package preservation.

Qualification:

- Production release-tooling suite: `30 passed`.
- PowerShell parsing: PASS.
- Transfer-bundle builder lint: PASS.
- Independent deterministic rebuild: PASS for both final ZIP hashes.
- Product package in the deployment bundle matches the unchanged frozen package SHA256.
- Product or migration files changed: NO.
- Production access/mutation/deployment: NO / NO / NO.

## Final operator artifacts

Read-only collector bundle `r5`:

- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157-r5.zip`
- Size: `43064` bytes
- SHA256: `3cb197168ec123f955561fd85b391e8725156b671630248d1408a27c5118f0d7`
- Expanded file count: `9`
- Collector script SHA256: `2d00de1d52f02a0fb970cc462bf31f4f598353252a05a8680f9b3bb619b49bcd`

Production deployment bundle `r3` (hold until corrected collector review and separate GO):

- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r3.zip`
- Size: `23016918` bytes
- SHA256: `53b5858a692a6fb35522d5704c0c08befea6a8f0589eaa70cbbf4b5037131869`
- Expanded file count: `12`
- Authoritative deployer script SHA256: `43183f7057e93f4abfd8b6f474fecbcc6be523c8c23e9487f0ea1657f34aa08b`

Unchanged identities:

- Frozen Product package SHA256: `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`
- Backup/restore toolkit `r1` SHA256: `942fd590cb4cc3981788c179bf77e6d0cf2e8e882da727ec2b7229d79263f1b1`

Intermediate local `r4/r2` contract builds were moved to the existing superseded-release archive and are not operator inputs.

## Reference-impact re-evaluation

`REFERENCE_IMPACT_FINAL=NONE`.

Rationale: the change corrects Forwarder-specific Production release tooling and operational evidence only. It does not alter Product capability, product surface, domain/data/SOR/reference truth, architecture boundary, runtime business behavior, migration, or any Folder 29 framework document. The active LPAF v2.2 baseline and reviewed v2.3 reference-impact guidance are accurately cited; no authoritative Product reference is stale because of this tooling contract correction.

## Contract verdict and next gate

The release-gate contract is internally consistent and fail-closed. This is not a live preflight PASS, validate-only PASS, human GO, or Execute authorization.

Exact next human operator step: copy only the expanded `r5` read-only bundle to `C:\1-webapp\forwarder-production-preflight\v1.10.0-r5\`, run the one read-only collector command in the operator handoff, and return only the newly generated sanitized preflight JSON for separate GO/NO-GO review.
