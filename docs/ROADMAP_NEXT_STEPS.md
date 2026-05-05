# نقشه‌راه پیشنهادی برای بلوغ ساختار و توسعه سیستم Forwarder

این سند بر اساس وضعیت فعلی ریپو تنظیم شده و رویکرد را به دو فاز اصلی تقسیم می‌کند: 
1) **بالابردن کیفیت ساختار**، 2) **توسعه قابلیت‌های جدید**.

---

## فاز ۰ — تثبیت ساختار پایه (پیش‌نیاز توسعه)

### 0.1 یکپارچه‌سازی ساختار Migration
- تعیین یک مسیر واحد برای migrationها (در حال حاضر هم `migrations/` در روت و هم `backend/migrations/` وجود دارد).
- حذف/آرشیو مسیر غیرمرجع و مستندسازی مسیر رسمی در README.
- اضافه کردن چک CI که فقط یک شاخه migration معتبر را بپذیرد.

### 0.2 استانداردسازی ساختار تست
- تفکیک تست‌ها به ۳ لایه مشخص:
  - `backend/tests/unit`
  - `backend/tests/integration`
  - `src/tests` برای frontend
- انتقال اسکریپت‌های تست ad-hoc از `scripts/` به تست‌های قابل اجرا با یک runner استاندارد.
- تعریف حداقل پوشش تست برای مسیرهای حیاتی (auth، shipment flow، expert flow، tracking).

### 0.3 کاهش پراکندگی Scriptها
- دسته‌بندی `scripts/` به زیرپوشه‌های هدفمند (`seed`, `diagnostics`, `manual`, `legacy`).
- حذف scriptهای تکراری/منسوخ و نگه‌داشتن یک نسخه canonical برای هر عملیات.
- ایجاد `scripts/README.md` با جدول «کاربرد، پیش‌نیاز، دستور اجرا».

### 0.4 قرارداد پیکربندی محیط (Environment Contract)
- تعریف فایل مرجع واحد برای env (ترجیحاً `.env.example` + `backend/env.production.example`).
- اعتبارسنجی اجباری env در startup و fail-fast با پیام دقیق.
- مستندسازی تفاوت env توسعه/تست/پروداکشن.

### 0.5 سخت‌سازی Logging و Monitoring
- یکپارچه‌سازی فرمت لاگ (json یا key-value استاندارد).
- افزودن correlation/request id در کل چرخه درخواست.
- تعریف شاخص‌های پایه: latency endpointها، خطاهای 4xx/5xx، وضعیت DB.

---

## فاز ۱ — آماده‌سازی معماری برای توسعه پایدار

### 1.1 تعریف مرزبندی Domainها در Backend
- شکستن مسیرهای backend از مدل route-centric به domain-centric (مثل `shipment`, `crm`, `expert`, `admin`).
- استخراج service layer برای منطق تجاری (جدا از route handlerها).
- استانداردسازی DTO/Schema ورودی-خروجی برای APIها.

### 1.2 قرارداد API و نسخه‌بندی
- تولید OpenAPI spec و قرار دادن در `docs/API.md` یا فایل جداگانه.
- تعریف versioning (`/api/v1/...`) برای جلوگیری از شکستن سازگاری.
- اضافه کردن تست قرارداد (contract tests) برای endpointهای حیاتی.

### 1.3 سیاست امنیتی عملیاتی
- مرور کامل JWT lifecycle (expiry، refresh strategy، revoke).
- rate limiting برای endpointهای حساس (login، public tracking، admin).
- بازبینی CORS و security headers مبتنی بر محیط deployment واقعی.

### 1.4 بهداشت فرانت‌اند
- تعریف ساختار feature-based برای `src/` (به‌جای رشد صفحه‌محور صرف).
- محدود کردن importهای cross-feature.
- یکپارچه‌سازی مدیریت state سروری با React Query (کلیدگذاری، invalidation policy، error policy).

---

## فاز ۲ — توسعه قابلیت‌ها (بعد از بلوغ ساختار)

### 2.1 توسعه جریان کامل عملیات Forwarding
- تکمیل چرخه end-to-end از ثبت درخواست تا quote، assign، status transition و closure.
- تعریف state machine واضح برای وضعیت درخواست‌ها و enforce در backend.

### 2.2 CRM و Expert Console پیشرفته
- SLA dashboard برای تیم عملیات.
- rule-based assignment با قابلیت وزن‌دهی (منطقه، نوع بار، ظرفیت کارشناس).
- timeline کامل فعالیت‌ها و audit trail.

### 2.3 قابلیت رهگیری عمومی و اطلاع‌رسانی
- hardening صفحه public tracking.
- اعلان رویدادهای کلیدی (پیامک/ایمیل/نوتیفیکیشن داخلی).
- تعریف سیاست privacy برای داده‌های قابل نمایش عمومی.

---

## برنامه اجرایی ۶ هفته‌ای پیشنهادی

### هفته 1
- تثبیت migration path + پاکسازی scriptهای بحرانی + سند `scripts/README.md`.

### هفته 2
- ساختار تست استاندارد + baseline تست برای auth/health/shipment.

### هفته 3
- service layer اولیه برای shipment و expert + refactor تدریجی routeها.

### هفته 4
- OpenAPI v1 + contract test + نسخه‌بندی endpointها.

### هفته 5
- logging/monitoring استاندارد + request id + شاخص‌های SLA.

### هفته 6
- شروع توسعه قابلیت‌های بیزینسی جدید (assignment rule و tracking enhancements).

---

## Definition of Done برای «رسیدن به سطح قابل قبول ساختاری»

- یک مسیر migration رسمی و بدون ابهام.
- اجرای تست‌ها با یک دستور مشخص و پایدار در CI.
- اسکریپت‌های operational مستند، غیرتکراری و قابل ردیابی.
- API نسخه‌بندی‌شده با قرارداد مشخص.
- لاگ و مانیتورینگ قابل اتکا برای عیب‌یابی production.

> پیشنهاد: تا قبل از تکمیل فاز ۰ و بخش‌های کلیدی فاز ۱، توسعه featureهای بزرگ جدید متوقف یا محدود به رفع نیازهای فوری شود.
