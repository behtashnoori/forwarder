# ADR-048: رهگیری سازگاری و Timeline محدود FWD-06

- Status: ACCEPTED — ACCEPTED_FOR_BOUNDED_FWD06; explicit Owner acceptance; local development and qualification only
- Date: 2026-09-16 (Asia/Tehran)
- Owners: نقش‌های Architecture / Operations / Product / Security / Data؛ شخصی تعیین نشده است.
- Affected domain: legacy tracking، Presentation، customer visibility و command receipts

## Context

فرم فعلی «افزودن بخش قابل رهگیری» در RequestDetail به مسیر
`ShipmentRequest -> ShipmentTracking -> ShipmentTransportUnit -> ShipmentTransportUnitUpdate`
متصل است. این مسیر سازگاری است؛ مالک canonical اجرا نیست. فعال‌سازی نیازمند
request با وضعیت تجاری `won`، tracking code و مالکیت tenant معتبر است.
`won` صرفاً eligibility است و وجود OperationalShipment را اثبات نمی‌کند.

در این فرم `unit_code` را کارشناس ثبت می‌کند و در همان tracking یکتا است؛
شناسهٔ DB را سیستم می‌سازد. `vehicle_reference` اختیاری است و بسته به نوع،
شناسهٔ کامیون، واگن یا کانتینر را نگه می‌دارد؛ مدل فعلی برای vehicle و container
دو فیلد مستقل ندارد. `ExecutionUnit` مسیر دیگری با کد خودکار `U-…` دارد و
نباید معنای آن به این فرم نسبت داده شود.

آزمون واقعی API در SQLite جدا: افزودن اولیهٔ هر چهار نوع با شناسهٔ فیزیکی
نامعلوم `201`؛ تکرار کد `409` با پیام عمومی، بدون رکورد دوم؛ tracking غیرفعال
و کد خالی `400`. خطای افزودن اولیهٔ گزارش‌شده در Production روی این baseline
بازتولید نشده است. وضعیت Production UNKNOWN باقی می‌ماند.

internal query فعلی فقط خلاصهٔ customer-visible را برمی‌گرداند و Timeline
ندارد. public query Timeline با allowlist دارد، اما زمان ثبت رخداد را منتشر
نمی‌کند. رخدادهای legacy زمان وقوع اجباری و زمان ثبت `created_at` دارند؛
command تصحیح/supersession یا هویت retry برای update موجود نیست.

## Problem and governing gate

Baseline §4: «New features MUST NOT target a legacy model unless an Accepted ADR
explicitly authorizes that choice.» Legacy/Canonical Map نیز تغییر واحد legacy
را نیازمند Accepted ADR می‌داند. ADR-035 فقط همگرایی مکان و snapshot را پذیرفته
است؛ توسعهٔ Timeline، receipt و customer visibility در آن تصمیم نشده است.
ADR-040 مهاجرت public canonical را به lineage/cohort gate وابسته کرده و
slice نخست آن public و legacy writes را تغییر نمی‌دهد.

این ADR برای تغییرهای اثرگذار فوق است؛ اصلاح معمول label، validation و
نمایش خطای موجود به‌تنهایی تصمیم معماری تازه نمی‌خواهد. مأموریت FWD-06 این
ADR را از پیش نپذیرفته است. هیچ تغییر runtime در این checkpoint اجرا نشده است.

## Decision — متن کامل تصمیم پیشنهادی

1. صرفاً برای FWD-06، توسعهٔ محدود مسیر سازگاری موجود برای intake روشن،
   Timeline داخلی و نمایش مجاز همان subject به مشتری مجاز شود. مالک موقت
   داده همان legacy tracking service و همان جداول فعلی بماند؛ این مسیر
   OperationalShipment یا ExecutionUnit canonical معرفی نشود. بازبینی این
   اختیار در پایان FWD-06 یا پیش از انتشار واقعی، هرکدام زودتر است.
2. `unit_code` کد داخلی ثبت‌شده توسط کارشناس، یکتا در tracking موجود و مستقل
   از شناسهٔ فیزیکی باقی بماند. DB ID سیستم‌ساخته است؛ شمارهٔ وسیله/محفظه
   اختیاری است. label و مثال طبق نوع `truck/container/wagon/other` باشند؛
   فیلد تازه یا شناسهٔ placeholder ذخیره‌شدنی ساخته نشود. رکورد و کد تاریخی
   حذف، renumber یا تبدیل نشوند.
3. eligibility فعلی `won + tracking_code + TENANT`، assignment، active actor،
   active membership و tenant در هر read/write/replay دوباره بررسی شوند.
   هیچ status، conversion یا customer authority جدید از قبول پیشنهاد FWD-05
   حاصل نشود. fixture اصلی از seed/command مجاز و transition واقعی موجود
   ساخته شود؛ ورود مصنوعی مستقیم به `won` شاهد journey عملیاتی محسوب نشود.
4. Timeline یک query قابل بازسازی از updateهای موجود باشد، نه SOR تازه.
   query داخلی فقط دادهٔ subject مجاز را نشان دهد؛ query عمومی فقط رخدادهای
   customer-visible و allowlist صریح را بازگرداند. presentation مشترک مجاز
   است؛ internal_note، actor identity، tenant IDs، numeric location IDs، private
   catalog و metadata داخلی در public payload غایب باشند. public tracking-code
   یک capability خواندنی است و احراز هویت شخص مشتری معرفی نشود.
5. `occurred_at` زمان وقوع و `ShipmentTransportUnitUpdate.created_at` زمان ثبت
   واقعی همان update است. برای این فیلد، writer فعلی `datetime.utcnow()` و
   service normalization منشأ UTC-naive هستند؛ فقط همین فیلد از serializer
   proven-legacy-UTC استفاده کند. به allowlist عمومی، `recorded_at` به‌عنوان
   alias این فیلد و `last_recorded_at` به‌عنوان بیشینهٔ زمان ثبت رخدادهای
   visible همان scope افزوده شود. recorded_at جای occurred_at نباشد و
   timezone انتخابی فقط نمایش را تغییر دهد. offset-less Instant جدید رد شود.
   فرم وقوع با now پر نشود؛ زمان نامعلوم با now یا زمان ثبت جعل نشود.
6. ترتیب legacy موجود نزولی `(occurred_at, id)` حفظ شود؛ id فقط tie-breaker
   پایدار داخلی است و برای این تصمیم عمومی نمی‌شود. زمان غیرقابل‌خواندن در
   نمایش صریحاً نامعلوم باشد و مرتب‌سازی presentation آن را بعد از زمان‌های
   معتبر قرار دهد؛ command زمان نامعلوم را طبق الزام فعلی نپذیرد. latest report
   از زمان ثبت و current compatibility status از query مالک بیاید. رخداد
   دیررس با occurred_at قدیمی وضعیت جدیدتر را عقب نبرد. خلاصهٔ داخلی فعلی
   customer-visible بماند و این scope در UI روشن باشد؛ نمایش history داخلی
   scope این خلاصه را عوض نکند. نبود رخداد به‌عنوان نبود گزارش نمایش داده شود،
   حتی اگر مقدار legacy خلاصه `not_started` باشد. lifecycle حمل canonical
   و projection/cache آن تغییر نکند.
7. برای UI جدید، create subject و append update از کلید پایدار `Idempotency-Key`
   متصل به payload ثابت استفاده کنند. owner receipt از مدل موجود
   OperationalIdempotency و یک public command-receipt contract محدود استفاده
   کند؛ هماهنگی و lock در command مالک tracking انجام شود، نه در UI یا با
   دسترسی مستقیم presentation به ORM مالک دیگر. scope یکتا شامل organization،
   operation، request/tracking یا unit و key باشد. همان key/payload پس از
   reauthorization همان identity نتیجه را بازیابی کند؛ key با payload متفاوت
   `409` بدهد. receipt، update و اثر local مجاز اتمیک باشند. receiptهای این
   slice expire/delete نشوند؛ retention بعدی تصمیم جدا می‌خواهد. client قدیمی
   بدون key فقط قرارداد سازگاری فعلی را حفظ کند و تضمین replay نگیرد؛ duplicate
   unit code همچنان conflict است، نه شاهد idempotent replay. concurrency و
   revocation این seam روی PostgreSQL disposable احراز شوند.
8. مکان فقط از قرارداد مجاز FWD-02/ADR-035 resolve شود؛ eligibility، FK و
   snapshotها حفظ شوند. مشتری فقط snapshotهای allowlisted را ببیند؛ catalog
   خصوصی و مختصات حدسی منتشر نشوند. event تصحیح legacy، status جدید، schema
   تاریخی، backfill، تغییر مالکیت، public canonical cutover، dual write، GPS،
   نقشه، routing، notification policy تازه، provider واقعی، Agent SDK و LLM API
   از این تصمیم خارج باشند. command تصحیح موجود نیست؛ محصول این قابلیت را
   ادعا نکند و تاریخچه برای زیبایی Timeline تغییر نکند. نیاز اثبات‌شده به
   تصحیح، schema تازه یا تغییر lifecycle با تصمیم نام‌دار جدا متوقف شود.

## Difference from current contract

اختیار تازه: bounded legacy feature extension، internal history query، public
recorded-time allowlist و receipt coordination. بدون تغییر: canonical owners،
شناسه‌ها، eligibility، واژگان status، تاریخچه، قرارداد مکان و public read-only
authority. اصلاح label و actionable error، به‌خودی‌خود exception معماری نیستند.

## Alternatives and exact Owner decision

- **A — پیشنهاد:** پذیرش صریح ADR-048 با همین متن/Hash، فقط FWD-06. این انتخاب
  اصلاح مسیر واقعاً موجود را مجاز می‌کند؛ canonical end-to-end tracking نیست.
- **B — canonical slice:** Owner bounded legacy extension را نپذیرد و خروجی را
  canonical بخواهد. در آن صورت همین ADR اجرا نمی‌شود؛ باید proposal دیگری با
  ordinary-expert authority، Shipment/ExecutionUnit lineage، governed location
  identity و public cohort/visibility coverage طبق ADR-040 تهیه و پذیرفته شود.
- **C — فقط اصلاح عادی:** Owner Timeline/receipt/public recorded fields را از
  scope خارج کند؛ فقط validation/error/identifier presentation موجود اصلاح
  شوند. این خروجی PASS مأموریت کامل FWD-06 نیست.

تصمیم لازم: «ADR-048 با Hash ارائه‌شده را فقط برای FWD-06 می‌پذیرم»؛ یا انتخاب
صریح B/C و تغییر scope. سکوت، زمان سپری‌شده یا PASS آزمون پذیرش نیست.

## Consequences, compatibility and migration

مسیر فعلی واضح و قابل trace می‌شود، اما بدهی legacy و نبود canonical mapping
باقی می‌ماند. public payload افزایشی است؛ aliasهای فعلی باقی می‌مانند. client
بدون key رفتار قبلی دارد؛ client جدید replay می‌گیرد. schema change در طراحی
فعلی پیش‌بینی نمی‌شود؛ sole head واقعی `20260916_fwd05_quote_response` است.
اگر مدل receipt موجود برای invariant کافی نبود، پیش از schema change توقف
و proposal اثر/upgrade/data-preservation آماده شود. migration تاریخی، backfill
و downgrade حذف‌کنندهٔ داده مجاز نیستند.

## Operational impact and rollback

backend compatible سپس UI جدید؛ bounded timeline query، loading/error/empty
جدا و input preservation لازم‌اند. rollback برنامه presentation قبلی را بازمی‌گرداند
و داده، receipt، snapshot و history را نگه می‌دارد. هیچ real provider، Production،
deploy، release tag یا main merge مجاز نیست. failure receipt/state جعلی نسازد.

## Validation required after acceptance

API واقعی intake/retry/invalid/precondition، native PostgreSQL receipt races و
revocation، same/cross tenant، private point permission/snapshot/leakage،
internal/public allowlist، occurrence/recording/timezone/late/ties/unknown،
history preservation و failure/empty/loading. browser UAT مستقل با ordinary
expert، customer capability واقعی، login/logout/reopen، RTL موبایل/دسکتاپ و
UTC/America_New_York با harness FWD-04؛ regression متأثر FWD-01 تا FWD-05،
static/architecture/secret gates و commit/push/fetched-ref verification لازم‌اند.
این فهرست طرح qualification است، نه PASS از پیش تعیین‌شده. بازبین جدا فقط
برای security gate واقعاً لازم و با نتیجهٔ مستقل به کار رود.

## Supersedes / status history

- Supersedes: none؛ فقط exception محدود و مکمل ADR-002/010/016/018/019/035/040.
- Superseded by: none.
- 2026-09-16: PROPOSED — legacy feature authorization، receipt و public visibility
  پیش از Build نیازمند تصمیم صریح هستند. Owner acceptance: NOT_RECEIVED.

## Bounded acceptance — 2026-09-16 (Asia/Tehran)

Explicit Owner continuation accepted the unchanged eight-point decision for FWD-06 only. No human name or title was supplied. Acceptance is not implementation verification, canonical designation, ownership transfer, cutover, dual write, historical migration, Production, GPS, map, provider or real Agent authority.

- Accepted proposal SHA256: `A3FFFEAA2C364B5073410B67ACD1943DC22139CB1895809F9E2F4A5956875FD3`.
- Exact proposed bytes preserved in [proposal history](../evidence/fwd-06-tracking-timeline/ADR-048-PROPOSED.md).
- Review due at FWD-06 end or before real release, whichever earlier. Further mission authority is not automatically extended. End of authority does not delete data or automatically disable the delivered capability.
- Implementation and qualification: pending; prior BLOCKED checkpoint remains historical evidence.

- 2026-09-16: ACCEPTED_FOR_BOUNDED_FWD06 — explicit Owner acceptance bound to the exact preserved proposal hash above; no additional decision accepted.

## Amendment M1 — 2026-09-16

The Owner accepted the [unchanged M1 proposal](../evidence/fwd-06-tracking-timeline/ADR-048-AMENDMENT-M1-MANUAL-TIME-PROPOSED.md), SHA256 `6792ADD2CC064A73977386D62263EDA13A0C534CE5A7E118679A1422CD55673A`, for local FWD-06 development and qualification. [Acceptance record](../evidence/fwd-06-tracking-timeline/ADR-048-AMENDMENT-M1-ACCEPTANCE-2026-09-16.md). M1 makes a bounded manual Asia/Tehran exception to TIME-BIZ-007/011 and authorizes one five-column additive migration. The historical proposed text and prior acceptance are preserved above; all other ADR-048 decisions remain in force. This is a decision record, not a runtime PASS.
