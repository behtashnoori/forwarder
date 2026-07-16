# فرایند Backfill داده‌های مرجع

## 1. هدف
این ابزار فقط هویت و منشأ تأییدشده را به رکوردهای موجود اضافه می‌کند و importer داده Production نیست.

## 2. تفاوت Backfill و Import
Backfill رکورد master جدید نمی‌سازد؛ Import آینده ممکن است dataset مصوب جدید را مدیریت کند.

## 3. Expand–Backfill–Contract
Schema قبلاً Expand شده است. این فاز ابزار Backfill را آماده می‌کند. Contract و NOT NULL فقط پس از تکمیل و reconciliation مجاز است.

## 4. Inventory
خروجی external شامل manifest، approval draft، summary و CSV جداگانه برای ده domain است. تمام proposed fieldها خالی‌اند.

## 5. Temporary row locator
ID عددی فقط locator موقت همان database است و نباید وارد package داده مرجع Production شود.

## 6. Record fingerprint
SHA-256 از domain، locator، نام normalizeشده، کد فعلی، parent IDها و active state ساخته می‌شود. mismatch برابر drift و مانع Apply است.

## 7. Stable code
کد فقط از مالک داده می‌آید؛ تولید از نام، ID، ترتیب یا hash ممنوع است.

## 8. Owner review
مالک داده proposed values، provenance و تصمیم را تکمیل می‌کند. تکمیل CSV به‌تنهایی authorization نیست.

## 9. Manifest
نسخه `1.0`، package type، revision هدف، وضعیت supply هر domain و checksum فایل‌ها را ثبت می‌کند.

## 10. Approval
Approval JSON مدرک مستند و نه امضای رمزنگاری است. domain، operation و target authorization باید صریح باشند.

## 11. Checksum
SHA-256 روی byteهای دقیق UTF-8 محاسبه و پیش از validation/diff/apply کنترل می‌شود.

## 12. Validation
ساختار، path، UTF-8، header، count، checksum، approval، code scope، fingerprint و effective range fail-closed بررسی می‌شوند.

## 13. Drift detection
هر تغییر رکورد پس از export، Apply را متوقف می‌کند. حالت دقیق post-state برای اجرای تکراری unchanged محسوب می‌شود.

## 14. Diff
Diff فقط read-only، deterministic و بدون fuzzy/name matching است.

## 15. Dry run
`apply-reference-backfill` بدون `--apply` هیچ write انجام نمی‌دهد.

## 16. Apply
Apply فقط روی target disposable/مجاز و approval معتبر فعال است. Candidate و `forwarder_db` همیشه رد می‌شوند.

## 17. Transaction
تمام عملیات در یک transaction و به ترتیب dependency اجرا و سپس uniqueness/hierarchy کنترل می‌شود.

## 18. Rollback
هر conflict، drift، constraint یا validation failure کل transaction را rollback می‌کند.

## 19. Idempotency
اجرای دوم فقط unchanged است و PortLocation یا code تکراری ایجاد نمی‌کند.

## 20. PortLocation
فقط از Port locator/fingerprint و کدهای parent صریح ساخته می‌شود؛ هیچ location استنباط نمی‌شود.

## 21. Provenance
source organization/reference/version و dataset ID باید مالک‌محور، بدون credential و قابل ممیزی باشند.

## 22. Candidate authorization
Candidate در این task صرفاً read-only است. Apply نیازمند فاز و approval جداگانه خواهد بود.

## 23. Production authorization
Production approval مستقل است و اکنون وجود ندارد؛ Production همچنان NO-GO است.

## 24. Security
URL اتصال روی CLI پذیرفته نمی‌شود، CSV formula prefixes escape می‌شوند و package path traversal رد می‌شود.

برای محافظت برگشت‌پذیر CSV، exporter فقط به مقادیری که با `=`، `+`، `-`، `@`، tab یا carriage return شروع می‌شوند marker نسخه‌دار `'FORWARDER-CSV-SAFE:'` اضافه می‌کند. validator این marker را فقط از ستون‌های snapshot تولیدشده توسط exporter باز می‌کند؛ مقدارهای پیشنهادی و یادداشت‌های مالک هرگز به‌طور ضمنی decode نمی‌شوند.

## 25. Failure handling
نتایج شامل PASS، PASS_WITH_WARNINGS، REJECTED، BLOCKED و AWAITING_OWNER_INPUT هستند؛ rejection exit موفق ندارد.

## 26. Contract migration prerequisites
کدهای رسمی کامل، parentهای مصوب، provenance، dry-run، reconciliation، Candidate rehearsal و authorization مستقل لازم‌اند.

در این فاز حتی approval با عنوان Production قابل اجرا نیست. ابزار Apply فقط targetهای disposable با prefix مصوب را می‌پذیرد؛ `forwarder_candidate_uat_20260717` و `forwarder_db` همیشه ممنوع‌اند.
