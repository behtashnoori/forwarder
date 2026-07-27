# گزارش Candidate Fingerprint Comparison و Bridge Topology

## نتیجه Gate — 2026-07-27

این Gate صرفاً با تحلیل فایل‌های Evidence نسخه 2.3 و بازرسی ایستای Repository انجام شد. Runner دوباره اجرا نشد، هیچ اتصال PostgreSQL برقرار نشد و هیچ migration، stamp، seed، DDL/DML، backup/restore یا دسترسی سرور انجام نشد.

توپولوژی منتخب:

`PHASE_1B_BRIDGE_NOT_FEASIBLE_FRESH_TRANSFER_REQUIRED`

هیچ‌یک از پنج Candidate در هیچ‌کدام از 9 دسته canonical با Main برابر نیست. Candidate نزدیک‌تر (`20250223_quote`) نیز 142 شیء گمشده، 202 شیء اضافه و 53 تعریف تغییرکرده دارد؛ بنابراین stamp یا marker بدون DDL تاریخچه‌ای خلاف واقع ثبت می‌کند. راه امن‌تر، ساخت پایگاه تازه در active head و انتقال کنترل‌شده داده در Gate مستقل است.

## Repository preflight

- Branch: `feature/forwarder-multileg-route-orchestration-phase1b`
- HEAD و upstream: `377e90abe1446936d8cf0eaeb9aed2998fa65c07`؛ ahead/behind برابر `0/0`
- Stage: خالی
- تغییرهای اولیه: فقط شش فایل Documentation از قبل موجود
- `git diff --check` و cached check: PASS
- Secret scan: صفر finding
- `.backend-port`: `57065`
- Persistent applied local/server: `NO / NO`

## Evidence integrity

- V2.3 runner result: exit `0`، پنج Candidate موفق از پنج، status=`EVIDENCE_COMPLETE`، بدون run error.
- Pack fingerprints: runner=`9395692f8471805e7bf204d323cdc88930c7e307a5a9cdc5a2f25e1ffbbd2161`، manifest=`31b289e95eab7ad7d17210a81eea97f56904596519d447a323855653faf12a3c`، SQL=`f0db5ac18f7c7a15aa7ba8a6332e8b4b3d383fe0b0b63e11285a26541de1d28e`؛ هر سه MATCH.
- Run summary: JSON معتبر و non-zero، schema/runner version درست، countهای `5/5/0`، final exit `0`، main/server targeted=`false`، credential prompt و database connection attempted=`true`.
- `evidence_complete`: property اصلاً وجود ندارد (در نتیجه type/value ندارد). field جایگزین `status` با مقدار string `EVIDENCE_COMPLETE` است. خروج runner از `$anyFailed` محاسبه شده و به field مفقود وابسته نیست. طبقه‌بندی: `RUN_SUMMARY_SCHEMA_DEFECT`؛ نقص presentation/schema است، نه `EXIT_PREDICATE_DEFECT`.
- Candidate summaries: هر پنج فایل non-zero و JSON معتبر، دقیقاً 26 field canonical، revision و final revision درست، create/migrate/fingerprint/cleanup همگی attempted و exit `0`، cleanup succeeded، remaining=`false`، seed=`false` و errorها null.
- Fingerprint outputs: هر پنج output و sidecar موجود و non-zero؛ مسیرها فقط از Candidate summary خوانده شدند؛ hash محاسبه‌شده با sidecar در هر پنج مورد برابر است.
- V2.3 SQL binding: runner دارای hash تأییدشده SQL است و همان `$FingerprintPath` را برای هر Candidate به `psql --file` داده است.
- Security: identity همه Candidateها disposable و در allow-list manifest است؛ هیچ‌کدام `forwarder_db` نیست. در fingerprintها credential/password/raw DSN یا row-level `INSERT/COPY` دیده نشد.
- Cleanup: دقیقاً پنج allow-list entry، بدون wildcard؛ همگی `ATTEMPTED_COMPLETE`، exit `0` و remaining=`false`.
- Main fingerprint: output/sidecar non-zero؛ whole-file hash محاسبه‌شده و ثبت‌شده هر دو `9d8e3b59ac0594e8d90c6ea4d1db3d1927eb56e985300846ac249922635223e6`. Identity=`forwarder_db`, PostgreSQL `18.0`, UTF8, read-only=`on`, revision=`54ea21ea0d9f` و `ROLLBACK` حاضر است. credential یا row-level data وجود ندارد.

## Candidate results

| Rank | Candidate | Migration | Final revision | Fingerprint | Cleanup | Remaining |
|---:|---|---|---|---|---|---|
| 1 | `20250120_add_customer_gamification_system` | PASS (0) | MATCH | generated/hash MATCH | PASS (0) | false |
| 2 | `20250220_add_tracking_code` | PASS (0) | MATCH | generated/hash MATCH | PASS (0) | false |
| 3 | `20250220_merge_heads` | PASS (0) | MATCH | generated/hash MATCH | PASS (0) | false |
| 4 | `20250220_merge_final` | PASS (0) | MATCH | generated/hash MATCH | PASS (0) | false |
| 5 | `20250223_quote` | PASS (0) | MATCH | generated/hash MATCH | PASS (0) | false |

## Fingerprint file verification

| Candidate | Output | Non-zero | Hash sidecar | Hash match | Security |
|---|---|---|---|---|---|
| `20250120_add_customer_gamification_system` | summary path | YES | `451dd3846aafce779c4a06e079729eddaed5606cc0a84931c4052ce2cd2c3147` | YES | PASS |
| `20250220_add_tracking_code` | summary path | YES | `e5095eac0e6f92dc07da497fd4cd735ca5852ec394a86a54f6a065679459e947` | YES | PASS |
| `20250220_merge_heads` | summary path | YES | `0d5274771cab4f862eb7fae4ca8201bf96a2c2b0cdf26ff1db52647f0c1d7f6e` | YES | PASS |
| `20250220_merge_final` | summary path | YES | `9bce1a55365e2ed00740b4abbb9e72d995fbc5f25feb500f9db43f1c2b8e96e6` | YES | PASS |
| `20250223_quote` | summary path | YES | `f91efcce1b9eec6447d677898e1f304d76e082fa22345d359279f1f3f5f63a5b` | YES | PASS |

## Cleanup verification

| Candidate | Disposable database | Cleanup status | Exit | Remaining |
|---|---|---|---:|---|
| `20250120_add_customer_gamification_system` | `forwarder_bridge_forensic_20250120_add_a521dc16d178` | ATTEMPTED_COMPLETE | 0 | false |
| `20250220_add_tracking_code` | `forwarder_bridge_forensic_20250220_add_a521dc16d178` | ATTEMPTED_COMPLETE | 0 | false |
| `20250220_merge_heads` | `forwarder_bridge_forensic_20250220_mer_a521dc16d178` | ATTEMPTED_COMPLETE | 0 | false |
| `20250220_merge_final` | `forwarder_bridge_forensic_20250220_fin_a521dc16d178` | ATTEMPTED_COMPLETE | 0 | false |
| `20250223_quote` | `forwarder_bridge_forensic_20250223_quo_a521dc16d178` | ATTEMPTED_COMPLETE | 0 | false |

## Canonical comparison

مقدار هر cell برابر `Candidate count/hash ↔ Main count/hash` است. همه cellها `DIFFERENT` هستند.

| Candidate | Tables | Columns | PK | FK | Unique | Check | Index | Sequence | Full schema |
|---|---|---|---|---|---|---|---|---|---|
| `20250120_add_customer_gamification_system` | DIFFERENT 26/`5ca18b86…` ↔ 32/`1cbbfe15…` | DIFFERENT 272/`9e7e60fd…` ↔ 321/`f791da33…` | DIFFERENT 26/`b3531730…` ↔ 32/`06ef8079…` | DIFFERENT 56/`a4fd8de5…` ↔ 55/`36693bc3…` | DIFFERENT 6/`f23586da…` ↔ 7/`91eb4406…` | DIFFERENT 23/`0d3988f9…` ↔ 0/`e3b0c442…` | DIFFERENT 163/`fb466400…` ↔ 110/`9e727825…` | DIFFERENT 0/`e3b0c442…` ↔ 31/`ef3070f7…` | DIFFERENT 572/`bd08a576…` ↔ 588/`f04d68ab…` |
| `20250220_add_tracking_code` | DIFFERENT 26/`5ca18b86…` ↔ 32/`1cbbfe15…` | DIFFERENT 273/`1933be31…` ↔ 321/`f791da33…` | DIFFERENT 26/`b3531730…` ↔ 32/`06ef8079…` | DIFFERENT 56/`a4fd8de5…` ↔ 55/`36693bc3…` | DIFFERENT 6/`f23586da…` ↔ 7/`91eb4406…` | DIFFERENT 23/`0d3988f9…` ↔ 0/`e3b0c442…` | DIFFERENT 164/`a7d11f50…` ↔ 110/`9e727825…` | DIFFERENT 0/`e3b0c442…` ↔ 31/`ef3070f7…` | DIFFERENT 574/`be75431a…` ↔ 588/`f04d68ab…` |
| `20250220_merge_heads` | DIFFERENT 26/`5ca18b86…` ↔ 32/`1cbbfe15…` | DIFFERENT 277/`6f817334…` ↔ 321/`f791da33…` | DIFFERENT 26/`b3531730…` ↔ 32/`06ef8079…` | DIFFERENT 58/`6b44a5c4…` ↔ 55/`36693bc3…` | DIFFERENT 6/`f23586da…` ↔ 7/`91eb4406…` | DIFFERENT 23/`0d3988f9…` ↔ 0/`e3b0c442…` | DIFFERENT 166/`e1952f7d…` ↔ 110/`9e727825…` | DIFFERENT 0/`e3b0c442…` ↔ 31/`ef3070f7…` | DIFFERENT 582/`c22a8b1a…` ↔ 588/`f04d68ab…` |
| `20250220_merge_final` | DIFFERENT 26/`5ca18b86…` ↔ 32/`1cbbfe15…` | DIFFERENT 277/`6f817334…` ↔ 321/`f791da33…` | DIFFERENT 26/`b3531730…` ↔ 32/`06ef8079…` | DIFFERENT 58/`6b44a5c4…` ↔ 55/`36693bc3…` | DIFFERENT 6/`f23586da…` ↔ 7/`91eb4406…` | DIFFERENT 23/`0d3988f9…` ↔ 0/`e3b0c442…` | DIFFERENT 166/`29ed4f1c…` ↔ 110/`9e727825…` | DIFFERENT 0/`e3b0c442…` ↔ 31/`ef3070f7…` | DIFFERENT 582/`5f6a786a…` ↔ 588/`f04d68ab…` |
| `20250223_quote` | DIFFERENT 32/`d35b7feb…` ↔ 32/`1cbbfe15…` | DIFFERENT 312/`4095bd25…` ↔ 321/`f791da33…` | DIFFERENT 32/`91ccce4e…` ↔ 32/`06ef8079…` | DIFFERENT 65/`0c4f5c47…` ↔ 55/`36693bc3…` | DIFFERENT 7/`108604a2…` ↔ 7/`91eb4406…` | DIFFERENT 23/`0d3988f9…` ↔ 0/`e3b0c442…` | DIFFERENT 182/`8763ff7c…` ↔ 110/`9e727825…` | DIFFERENT 0/`e3b0c442…` ↔ 31/`ef3070f7…` | DIFFERENT 653/`2f51d350…` ↔ 588/`f04d68ab…` |

Full canonical hashes در فایل machine-readable `analysis-summary.json` در `%TEMP%\forwarder-v23-fingerprint-analysis` ثبت شده‌اند. Main canonical baseline دقیقاً این است: Tables 32/`1cbbfe154f22bedc0d8f205dc06f6bfc9750803713b1ed1f470238009d5bda09`؛ Columns 321/`f791da338d041541ee0b6eddd9d9c48ce12812d539bded198c224cb278df16b9`؛ PK 32/`06ef8079681d5ebf6fc920ad8b97533cc73115e48e82a0bf0cd23294b0bd9a44`؛ FK 55/`36693bc3c450a947a93e11d5f2f7f6bea9b40be91d4f0c9e1219f551d121b2d6`؛ Unique 7/`91eb440606f376e4b0246cca3a57e9d0e818dc07d3eb4e6b61a74ffa5a4e65be`؛ Check 0/`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`؛ Index 110/`9e727825a964022f1721e1150c77295387d33b14bc6658e48720a6c7b8a21ac1`؛ Sequence 31/`ef3070f7e3c65851bca830b2e2b31c9ee1b0f5c57bb2228c4c889e87faf5abad`؛ Full 588/`f04d68ab828396118613abab17e82ca76d93ce020eeece24df8df7e910c2cb99`.

## Structural deltas and semantic classification

هر missing/extra/changed definition به‌صورت machine-readable در پنج فایل `*-delta.json` زیر `%TEMP%\forwarder-v23-fingerprint-analysis` ثبت شده است. شمارش‌ها object-level هستند و stdout length یا timestamp دخالت ندارد.

| Candidate | Changed definitions | Missing | Extra | غالب‌ترین ریسک معنایی |
|---|---:|---:|---:|---|
| `20250120_add_customer_gamification_system` | 53 | 160 | 144 | DESTRUCTIVE، RELATIONSHIP_CHANGE، CONSTRAINT_TIGHTENING |
| `20250220_add_tracking_code` | 53 | 160 | 146 | همان + additive tracking code |
| `20250220_merge_heads` | 53 | 154 | 149 | همان؛ merge خود no-op است |
| `20250220_merge_final` | 53 | 154 | 149 | همان؛ merge خود no-op است |
| `20250223_quote` | 53 | 142 | 202 | DESTRUCTIVE/AMBIGUOUS؛ هم missing و هم extra table families |

- Candidateهای 1 تا 4 شش table اصلی Main را ندارند: `audit_logs`, `customer_tenant_links`, `expert_quote`, `export_jobs`, `memberships`, `tenants`. Candidate 5 پنج مورد از آن‌ها را ندارد (expert_quote حاضر است)، اما پنج table اضافه referral/site دارد.
- 50 تعریف column مشترک در همه Candidateها با Main متفاوت است (`DATA_SEMANTICS_UNKNOWN` تا بررسی داده و default/nullability).
- سه FK هم‌نام تعریف متفاوت دارند (`RELATIONSHIP_CHANGE`) و ده‌ها FK/constraint هم missing/extra هستند.
- همه Candidateها 23 check constraint اضافه نسبت به Main دارند (`CONSTRAINT_TIGHTENING`).
- fingerprint Candidateها هیچ sequence canonical ثبت نکرده، در حالی که Main 31 sequence و ownership/default relationship دارد؛ این اختلاف برای stamp قابل چشم‌پوشی نیست.
- matching object name با definition متفاوت exact محسوب نشده است.

## Structural ranking

| Rank | Candidate | Exact categories | Changed definitions | Missing | Extra | Semantic risk |
|---:|---|---:|---:|---:|---:|---|
| 1 | `20250223_quote` | 0 | 53 | 142 | 202 | HIGH: destructive/ambiguous mixed families |
| 2 | `20250220_merge_final` | 0 | 53 | 154 | 149 | HIGH; closer no-op merge |
| 3 | `20250220_merge_heads` | 0 | 53 | 154 | 149 | HIGH; one additional merge step |
| 4 | `20250120_add_customer_gamification_system` | 0 | 53 | 160 | 144 | HIGH; older branch state |
| 5 | `20250220_add_tracking_code` | 0 | 53 | 160 | 146 | HIGH; extra tracking objects |

این ranking صرفاً structural distance است و Candidate رتبه 1 را به equivalent یا stamp-safe تبدیل نمی‌کند.

## Active graph and distance to head

هر پنج revision در active graph قرار دارند. branch/merge points:

- `20250220_add_tracking_code` فرزند `20250120_add_customer_gamification_system` است.
- `20250220_merge_heads` دو parent دارد: `20250220_add_tracking_code` و `20250115_add_iran_entry_point_fields`.
- `20250220_merge_final` دو parent دارد: `20250220_merge_heads` و `20240924_add_expert_console_fields`.
- سپس مسیر خطی به `20250221_referral → 20250221_auto → 20250221_site → 20250223_quote → 20250223_quote_fix → 20250223_ensure_quote → 20250224_allow_quoted_status → 20260710_crm_link_audit → 20260715_multi_unit_tracking → 20260716_drop_invalid_shipment_update_trigger → 20260717_add_customs_office_domain → 20260718_add_token_revocation → 20260719_add_auth_sessions → 20260720_expand_reference_data_identity → 20260725_add_tracking_location_reference → 20260726_seed_iran_tracking_reference → 20260727_add_iran_destination_point → 20260728_add_quote_customer_response → 20260729_operational_vertical_slice → 20260730_multileg_route → 20260801_route_exception` می‌رسد.

فاصله upgrade-set تا head (با احتساب ancestorهای branch دیگر که هنوز در Candidate اعمال نشده‌اند): Candidateهای 1 تا 5 به‌ترتیب 26، 25، 23، 21 و 17 revision هستند.

طبقه‌بندی ایستا: دو merge و `quote_fix` no-op؛ `ensure_quote` additive/idempotent؛ referral/site/CRM/tracking/auth/customs و operational tables عمدتاً additive؛ `20250221_auto` و `20260726_seed_iran_tracking_reference` data migration؛ چند migration شامل FK/nullability/constraint changes؛ `20250224_allow_quoted_status`, `20260716_drop_invalid_shipment_update_trigger`, بخش‌هایی از `20260719_add_auth_sessions` و `20260730_multileg_route` destructive/constraint-changing هستند. در نتیجه later path فقط additive نیست.

## Archived revision semantics

- Revision: `54ea21ea0d9f`; parent: `20240923_add_cargo_details`.
- نقش تاریخی: autogenerate قدیمی که Main هنوز marker آن را دارد، اما عضو active graph فعلی نیست.
- archive/removal commit: `c3e8f37b9f6df133716f1e82da579bfd7dd2f28a` در 2026-05-18 با عنوان `Archive deprecated root migrations`؛ rename صددرصد به docs archive.
- footprint upgrade: drop کامل `shipper`, `shipment_mode`, `user_otp`, `incoterm`, `package_type`, `app_user`، drop گسترده index/unique/FK، حذف `county.city_id`، تغییر nullability/type/default و افزودن سه ستون transport به `shipment_request`.
- ریسک: destructive و data-loss-capable؛ چند constraint بدون نام ایجاد می‌کند و lineage فعال را نمایندگی نمی‌کند.
- downgrade محدود است: tableها را فقط از تعریف code بازمی‌سازد و داده حذف‌شده را برنمی‌گرداند؛ بازسازی constraint/default/sequence می‌تواند با state واقعی ناسازگار باشد.
- این migration اجرا، restore یا reuse نشده و نباید بشود.

## Selected candidate

- Revision: هیچ Candidate به‌عنوان equivalent انتخاب نشد؛ `20250223_quote` فقط نزدیک‌ترین fingerprint است.
- Reason: 0/9 exact category، 53 changed، 142 missing و 202 extra.
- Exact structural evidence: هیچ category exact نیست.
- Distance to head: 17 revision.
- Later migrations: ترکیب no-op، additive، data، constraint-changing و destructive.
- Ambiguities: 50 column definition، 3 changed FK، sequence/ownership، table families متفاوت و semantics داده.

## Topology decision

- Selected topology: `PHASE_1B_BRIDGE_NOT_FEASIBLE_FRESH_TRANSFER_REQUIRED`
- Why: هیچ active Candidate معادل canonical Main نیست؛ stamp تاریخچه و schema را materially falsify می‌کند. marker/merge بدون DDL نیز mismatch موجود را حل نمی‌کند و truthful applied-DDL history نمی‌سازد.
- Rejected legacy marker: insertion/parent قابل‌دفاعی که state واقعی Main را truthfully represent کند وجود ندارد؛ similarity کافی نیست و archived destructive code نیز قابل اجرا نیست.
- Rejected controlled stamp: شرط حداقل یک exact canonical Candidate برقرار نیست.
- Fresh transfer: پایگاه fresh در active head و انتقال کنترل‌شده با mapping/validation داده، امن‌تر است.
- Implementation permission: `NO`.

## Isolation

- Runner rerun: NO
- PostgreSQL connected: NO
- Main database changed: NO
- Migration/stamp/seed: NO / NO / NO
- Server accessed: NO
- Product/Test/Migration/Config files changed: NO
- Evidence files changed/deleted: NO
- Commit/push: NO / NO
- Secret findings: 0
- `.backend-port`: 57065
- Persistent applied local/server: NO / NO
- HEAD: `377e90abe1446936d8cf0eaeb9aed2998fa65c07`

## Next Gate

Gate بعدی باید یک **Fresh Active-Head Clone + Controlled Data-Transfer Rehearsal** مستقل و صریحاً مجاز باشد: backup/restore clone ایزوله از Main، ایجاد target disposable در `20260801_route_exception`، تعریف mapping table/column و sequence ownership، dry-run انتقال با شمارش و checksum ردیفی/رابطه‌ای، کنترل FK/unique/nullability، reconciliation گزارش‌شده و سپس حذف فقط targetهای allow-listed. این Gate نباید روی Main اجرا شود و در این بررسی اجرا نشده است.

PHASE_1B_BRIDGE_NOT_FEASIBLE_FRESH_TRANSFER_REQUIRED

## Final closure decision — 2026-07-27

Phase 1B product implementation and UAT are complete. Main remains unchanged at legacy revision `54ea21ea0d9f`, and no active candidate is canonically equivalent to Main. Stamp and legacy marker are rejected. The future strategy is a fresh active-head database plus controlled data transfer.

Final operational evidence confirmed source read-only and rollback, disposable migration to `20260801_route_exception`, valid target inventory hash, accepted baseline containing only explained migration/system occupancy, and successful cleanup with `disposable_remaining=false`. Main write, server targeting, and seed execution were all false. Automated mapping stopped because the native analysis child exited `1` (`NATIVE_FAIL:ANALYSIS:1`) and is deferred as a known limitation. No data transfer, persistent migration, stamp, deploy, or server change occurred.

`PHASE_1B_IMPLEMENTATION_COMPLETE / PHASE_1B_DATABASE_CUTOVER_DEFERRED / FRESH_TRANSFER_REQUIRED / AUTOMATED_MAPPING_DEFERRED / MAIN_DATABASE_UNCHANGED / SERVER_UNCHANGED`
