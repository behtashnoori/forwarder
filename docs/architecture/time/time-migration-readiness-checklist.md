# Time Migration Readiness Checklist

این سند gate اجباری پیش از طراحی، اجرا یا rollout هر Migration زمانی است. تکمیل
Checklist به‌تنهایی مجوز اجرا نیست؛ مجوز تغییر، review و فرایند عملیاتی پروژه نیز
لازم است.

## 1. Scope and authorization

- [ ] یک ستون یا گروه هم‌قرارداد با نام table/column و owner مشخص شده است.
- [ ] معنای هدف مطابق [ADR-016](../../operational/adr/ADR-016-time-and-timezone-architecture.md)
  یکی از Instant، Local Date، Business Local DateTime یا Duration است.
- [ ] تصمیم‌های کسب‌وکاری وابسته در
  [Decision Register](time-business-decision-register.md) وضعیت `Approved` دارند.
- [ ] تغییر schema/data و پنجره اجرا جداگانه مجاز و review شده‌اند.
- [ ] خارج از محدوده و موارد عمداً deferred ثبت شده‌اند.

## 2. Historical evidence

- [ ] همه مسیرهای write تاریخی و فعلی inventory شده‌اند.
- [ ] نوع ORM/driver، DB type و تنظیم Timezone سرور/دیتابیس در هر دوره شناخته شده است.
- [ ] producerها، importها، APIها، jobها و منابع خارجی بررسی شده‌اند.
- [ ] نمونه‌های نماینده از دوره‌ها، کاربران، Locationها و مرز روز استخراج شده‌اند.
- [ ] فرض UTC/local بودن هر مقدار با evidence پشتیبانی می‌شود؛ naive ناشناخته حدس
  زده نشده است.
- [ ] null، default، sentinel، outlier، duplicate و مقدار خارج از دامنه شمارش شده‌اند.

## 3. Conversion contract

- [ ] Rule تبدیل دقیق، versioned و برای هر cohort نوشته شده است.
- [ ] IANA timezone و مالک/Location منبع آن مشخص است.
- [ ] رفتار ambiguous/nonexistent local time صریح است.
- [ ] Date-only هرگز با midnight ضمنی به Instant تبدیل نمی‌شود.
- [ ] precision، rounding و ترتیب رخدادها حفظ می‌شود.
- [ ] رکورد غیرقابل‌تبدیل quarantine می‌شود و fallback حدسی ندارد.
- [ ] expected counts، invariants، tolerance و acceptance threshold تعریف شده‌اند.

## 4. Safe rehearsal

- [ ] backup یا snapshot قابل restore و Clone ایزوله تهیه شده است.
- [ ] داده حساس Clone طبق سیاست امنیتی محافظت شده است.
- [ ] dry-run روی Clone با نسخه واقعی موتور و schema اجرا شده است.
- [ ] زمان اجرا، lock، index impact، batch size و ظرفیت log اندازه‌گیری شده‌اند.
- [ ] snapshot قبل/بعد و reconciliation رکوردبه‌رکورد یا aggregate انجام شده است.
- [ ] anomalyها review و Rule پس از هر تغییر دوباره rehearsal شده است.

## 5. Compatibility and rollout

- [ ] برنامه expand → migrate → verify → switch → contract رعایت می‌شود.
- [ ] سازگاری N/N-1، read/write path و serialization دوره گذار تعیین شده‌اند.
- [ ] rollout مرحله‌ای، cohort/canary، checkpoint و idempotency تعریف شده‌اند.
- [ ] API/UI/reporting تا زمان switch معنای قدیم و جدید را مخلوط نمی‌کنند.
- [ ] observability شامل progress، error count، quarantine و mismatch آماده است.
- [ ] deployment و Migration از startup برنامه جدا هستند.

## 6. Rollback and recovery

- [ ] نقطه بدون بازگشت و معیار stop/go تعریف شده است.
- [ ] rollback فنی و routing به قرارداد قبلی نوشته و روی Clone آزموده شده است.
- [ ] restore واقعی backup آزموده و RTO/RPO ثبت شده است.
- [ ] داده‌های نوشته‌شده در دوره rollout برای بازگشت reconcile می‌شوند.
- [ ] مسئول اجرا، approver، on-call و مسیر escalation مشخص‌اند.

## 7. Verification and evidence

- [ ] count، null rate، min/max، distribution و boundary samples قبل/بعد مقایسه شده‌اند.
- [ ] Instantها با RFC 3339 round-trip و UTC canonicalization بررسی شده‌اند.
- [ ] Date-onlyها در API/UI بدون جابه‌جایی روز round-trip می‌شوند.
- [ ] گزارش‌ها IANA timezone و مرز `[start, end)` مصوب را نشان می‌دهند.
- [ ] رخدادهای out-of-order با `occurred_at`/`recorded_at` درست باقی می‌مانند.
- [ ] Contract Testهای DB/Backend/API/UI و سناریوهای مرزی پیش از rollout تعریف شده‌اند.
- [ ] evidence، queryها، checksumها، approvalها و نتیجه rollback rehearsal بایگانی شده‌اند.

## Mandatory migration record

هر Migration باید پیش از اجرا یک record شامل این فیلدها داشته باشد:

| Field | Required content |
| --- | --- |
| Scope | table/column/cohort و خارج از محدوده |
| Source semantics | evidence و دوره‌های تاریخی |
| Target contract | نوع معنایی و قرارداد DB/API/UI |
| Conversion rule | نسخه Rule، zone source و ambiguity handling |
| Business approval | Decision ID، approver و تاریخ |
| Rehearsal | Clone، dataset، نتیجه و performance |
| Reconciliation | معیارها، baseline و نتیجه مورد انتظار |
| Rollback | روش آزموده‌شده، stop criteria و owner |
| Execution | window، operator، checkpoints و monitoring |
| Evidence | محل snapshot، log و گزارش نهایی |

اگر هر مورد P0 ناقص یا هر معنای تاریخی `UNKNOWN` باشد، وضعیت Migration
`NOT READY` است.
