# I18N-2A: ممیزی و برنامه تکمیل چندزبانه‌سازی فرانت‌اند

تاریخ: 2026-07-10

## 1. وضعیت این سند

این سند فقط برای ممیزی و برنامه‌ریزی است.

در این فاز هیچ ترجمه UI، تغییر backend، تغییر database، تغییر model، migration، تغییر API payload، تغییر schema مربوط به `SiteSettings`، نصب package، deploy، commit یا push انجام نمی‌شود.

## 2. وضعیت Git در زمان ممیزی

وضعیت تاییدشده قبل از تهیه سند:

| مورد | نتیجه |
| --- | --- |
| Branch | `forwarder-14050324-ver-13` |
| Upstream | `origin/forwarder-14050324-ver-13` |
| وضعیت sync | branch با origin هم‌تراز است |
| ahead set | خالی |
| working tree | clean؛ فقط warning شناخته‌شده `.pytest_cache` ممکن است دیده شود |

## 3. هدف I18N-2A

هدف I18N-2A تهیه نقشه تکمیل چندزبانه‌سازی frontend است تا فازهای بعدی بتوانند بدون دست‌زدن به backend یا دیتابیس، متن‌های باقی‌مانده UI را به foundation موجود منتقل کنند.

زبان‌های هدف فعلی:

- فارسی: زبان پیش‌فرض
- انگلیسی: زبان دوم

اصل معماری:

- چندزبانه‌سازی فعلی باید frontend-only باقی بماند.
- هیچ payload یا contract از backend برای ترجمه تغییر نمی‌کند.
- هیچ schema جدیدی برای `SiteSettings` ساخته نمی‌شود.
- داده‌های دامنه‌ای که از API می‌آیند، مثل نام شهر، استان، کشور، نام کاربر، توضیح کاربر، tracking code، status خام ناشناخته یا نام روش حمل، نباید به صورت جعلی ترجمه شوند.

## 4. foundation موجود

بر اساس کد فعلی:

- `src/i18n.tsx` وجود دارد.
- `Language = "fa" | "en"` تعریف شده است.
- `I18nProvider` در `src/App.tsx` دور routeها قرار گرفته است.
- زبان اولیه از `localStorage` با key فعلی `forwarder.language` خوانده می‌شود.
- زبان پیش‌فرض وقتی مقدار معتبر وجود ندارد فارسی است.
- با تغییر زبان، `document.documentElement.lang` تنظیم می‌شود.
- با تغییر زبان، `document.documentElement.dir` بین `rtl` و `ltr` تنظیم می‌شود.
- helperهای `t`, `tf`, `statusLabel`, `shippingTypeLabel`, `stepLabel`, `actionLabel`, و `transportLabel` وجود دارند.
- `Header` دکمه تغییر زبان دارد و از `toggleLanguage` استفاده می‌کند.
- چند بخش public/customer/expert/admin از `useI18n` استفاده می‌کنند.

## 5. محدوده‌هایی که اکنون بخشی از i18n را استفاده می‌کنند

فایل‌هایی که در ممیزی فعلی `useI18n` دارند:

- `src/components/Header.tsx`
- `src/components/Footer.tsx`
- `src/components/Hero.tsx`
- `src/components/LocationForm.tsx`
- `src/components/RequestConfirmation.tsx`
- `src/pages/Index.tsx`
- `src/pages/PublicTracking.tsx`
- `src/pages/CustomerDashboard.tsx`
- `src/pages/CustomerRequestDetail.tsx`
- `src/pages/ExpertConsole.tsx`
- `src/pages/RequestDetail.tsx`
- `src/pages/AdminPanel.tsx`
- `src/pages/CRMDashboard.tsx`

نتیجه:

foundation فعال است، اما coverage کامل نیست. بعضی فایل‌ها `useI18n` دارند ولی هنوز متن hardcoded هم دارند.

## 6. سطح‌های باقی‌مانده با متن hardcoded

ممیزی با جستجوی متن فارسی در `src/pages`, `src/components`, و `src/contexts` نشان داد این فایل‌ها هنوز متن فارسی hardcoded دارند:

- `src/contexts/SiteSettingsContext.tsx`
- `src/components/AdminReportsTab.tsx`
- `src/components/ErrorBoundary.tsx`
- `src/components/AdvancedSearch.tsx`
- `src/components/ExpertLogin.tsx`
- `src/components/PageNav.tsx`
- `src/components/NotificationCenter.tsx`
- `src/components/QuoteModal.tsx`
- `src/components/ReferralRulesTab.tsx`
- `src/components/RequestConfirmation.tsx`
- `src/components/LocationForm.tsx`
- `src/components/SiteSettingsTab.tsx`
- `src/pages/VerifyEmail.tsx`
- `src/pages/UserManagement.tsx`
- `src/pages/ExpertConsole.tsx`
- `src/pages/RequestDetail.tsx`
- `src/pages/CustomerDashboard.tsx`
- `src/pages/CustomerRequestDetail.tsx`
- `src/pages/PublicTracking.tsx`

این فهرست به معنی خطا نیست؛ نشان می‌دهد فازهای بعدی باید کدام سطح‌ها را به تدریج به translation key منتقل کنند.

## 7. طبقه‌بندی اولویت تکمیل

### 7.1 اولویت 1: سطح عمومی و مشتری

این سطح‌ها مستقیم روی تجربه مشتری اثر دارند و برای فعال‌سازی English secondary باید زودتر کامل شوند:

- `Index`
- `Header`
- `Footer`
- `Hero`
- `LocationForm`
- `RequestConfirmation`
- `PublicTracking`
- `CustomerDashboard`
- `CustomerRequestDetail`
- `VerifyEmail`
- `ErrorBoundary`

هدف:

- متن‌های فرم ثبت درخواست، validation، toast، success state و tracking در هر دو زبان قابل خواندن باشند.
- تغییر `dir` باعث شکستن layout نشود.
- داده‌های مکانی فارسی از backend بدون ترجمه جعلی نمایش داده شوند.

### 7.2 اولویت 2: سطح کارشناس و عملیات

این سطح‌ها برای تیم داخلی مهم‌اند، اما بعد از public/customer می‌توانند تکمیل شوند:

- `ExpertConsole`
- `RequestDetail`
- `QuoteModal`
- `PageNav`
- `NotificationCenter`

هدف:

- status/action labels از helperهای فعلی استفاده کنند.
- toastها و modalها hardcoded باقی نمانند.
- تاریخ و عدد با `locale` فعلی format شوند.
- متن‌های CRM جدید در `RequestDetail` برای English آماده شوند، بدون تغییر backend.

### 7.3 اولویت 3: سطح مدیریت

این سطح‌ها پیچیده‌ترند و متن‌های تنظیماتی زیادی دارند:

- `AdminPanel`
- `AdminReportsTab`
- `UserManagement`
- `SiteSettingsTab`
- `ReferralRulesTab`
- `AdvancedSearch`

هدف:

- labelها، toastها، empty stateها، filterها و buttonها به translation key منتقل شوند.
- `SiteSettingsTab` فقط UI labelهای خودش را ترجمه کند؛ schema و keyهای ذخیره‌شده تغییر نکنند.
- داده‌های قابل ویرایش توسط مدیر مثل نام سایت، متن footer، محتوای درباره ما و تماس با ما، همچنان content مدیریتی باقی بمانند و در این فاز به مدل چندزبانه تبدیل نشوند.

## 8. مرزبندی SiteSettings

`SiteSettingsContext` اکنون defaultهای فارسی برای محتوای قابل تنظیم سایت دارد.

تصمیم پیشنهادی برای I18N-2:

- فعلا schema مربوط به `SiteSettings` تغییر نکند.
- فعلا backend برای ذخیره متن دو زبانه تغییر نکند.
- اگر admin در `SiteSettings` متن فارسی وارد کرده باشد، همان متن در UI نمایش داده شود.
- fallback فقط وقتی از `t(...)` استفاده شود که مقدار `SiteSettings` خالی باشد.
- برنامه چندزبانه کردن محتوای CMS-like سایت، اگر لازم شد، باید فاز جداگانه باشد.

دلیل:

تبدیل `SiteSettings` به محتوای چندزبانه نیازمند تصمیم محصولی، schema، migration، API contract و UI مدیریت محتواست؛ خارج از محدوده frontend-only است.

## 9. مرزبندی API و داده‌های دامنه‌ای

در فازهای بعدی نباید این موارد به صورت مصنوعی ترجمه شوند:

- نام استان، شهرستان، شهر، کشور، بندر و port که از API می‌آیند.
- نام مشتری، کارشناس، شرکت، شماره تماس و email.
- متن‌های یادداشت، message، quote note و توضیحات واردشده توسط کاربر.
- tracking code، request id و کدهای سیستمی.
- خطاهای خام backend مگر آنکه frontend برای کد خطای مشخص mapping امن داشته باشد.

مواردی که قابل ترجمه frontend-only هستند:

- labelها
- placeholderها
- toastهای frontend
- empty stateها
- tab titleها
- button textها
- helper textها
- headingها
- validation messageهای frontend
- status/action/step labels وقتی مقدار شناخته‌شده است.

## 10. قرارداد keyها

برای جلوگیری از آشفتگی keyها، الگوی زیر پیشنهاد می‌شود:

- `common.*` برای actionها و labelهای مشترک.
- `auth.*` برای login و session.
- `public.*` برای landing و tracking عمومی.
- `requestForm.*` برای فرم ثبت درخواست.
- `requestConfirmation.*` برای صفحه تایید درخواست.
- `customer.*` برای پنل مشتری.
- `expert.*` برای کنسول کارشناس.
- `requestDetail.*` برای جزئیات درخواست کارشناس.
- `crm.*` برای سطح CRM داخل UI.
- `admin.*` برای داشبورد و مدیریت.
- `reports.*` برای گزارش‌ها.
- `userManagement.*` برای مدیریت کاربران.
- `siteSettings.*` برای labelهای فرم تنظیمات سایت، نه محتوای ذخیره‌شده.
- `validation.*` برای خطاهای client-side.

قاعده:

هر key جدید باید هم در `fa` و هم در `en` اضافه شود. اضافه کردن key فقط در یک زبان ممنوع باشد.

## 11. برنامه اجرایی پیشنهادی

### فاز I18N-2B: تکمیل سطح عمومی و مشتری

دامنه:

- `LocationForm`
- `RequestConfirmation`
- `PublicTracking`
- `CustomerDashboard`
- `CustomerRequestDetail`
- `VerifyEmail`
- `ErrorBoundary`

خروجی مورد انتظار:

- همه متن‌های static و toastهای این سطح‌ها به `t/tf` منتقل شوند.
- `locale` برای تاریخ‌ها و اعداد استفاده شود.
- layout در `fa/rtl` و `en/ltr` smoke شود.

### فاز I18N-2C: تکمیل سطح کارشناس و CRM

دامنه:

- `ExpertConsole`
- `RequestDetail`
- `QuoteModal`
- `PageNav`
- `NotificationCenter`

خروجی مورد انتظار:

- متن‌های عملیات داخلی، note/quote modal، CRM link/create UI و toastها ترجمه شوند.
- status/action labels از helperهای موجود استفاده کنند.
- هیچ API payload تغییر نکند.

### فاز I18N-2D: تکمیل سطح مدیریت

دامنه:

- `AdminPanel`
- `AdminReportsTab`
- `UserManagement`
- `SiteSettingsTab`
- `ReferralRulesTab`
- `AdvancedSearch`

خروجی مورد انتظار:

- labelها، toastها، filterها و empty stateها ترجمه شوند.
- `SiteSettings` فقط در سطح UI label ترجمه شود؛ schema و مقدارهای ذخیره‌شده ثابت بمانند.

### فاز I18N-2E: hardening و QA

دامنه:

- مرور کل `src/pages`, `src/components`, `src/contexts`
- حذف متن static باقی‌مانده به جز موارد مجاز
- smoke دو زبانه
- regression build/lint

خروجی مورد انتظار:

- فهرست hardcodedهای باقی‌مانده فقط شامل داده دامنه‌ای، test text، comment یا fallback آگاهانه باشد.
- build و lint هدفمند pass شوند.

## 12. QA gate پیشنهادی برای هر فاز

برای هر فاز implementation آینده:

1. `rg` برای hardcoded Persian/English UI literals در فایل‌های تغییرکرده اجرا شود.
2. بررسی شود هر key جدید در هر دو زبان وجود دارد.
3. صفحه‌های تغییرکرده در `fa` و `en` smoke شوند.
4. `document.documentElement.lang` و `dir` بعد از toggle بررسی شود.
5. در mobile و desktop، متن دکمه‌ها و cardها overflow نداشته باشد.
6. `npm.cmd run build` اجرا شود.
7. lint هدفمند روی فایل‌های تغییرکرده اجرا شود.

اگر repo-wide lint به warning یا issue موجود برخورد کند، باید جداگانه گزارش شود و با فاز i18n مخلوط نشود.

## 13. تست‌های پیشنهادی آینده

بدون الزام به اجرای فعلی، تست‌های مفید برای فازهای بعدی:

- تست `I18nProvider` برای default فارسی.
- تست persistence در `localStorage`.
- تست toggle زبان و تنظیم `document.documentElement.lang/dir`.
- تست اینکه keyهای `fa` و `en` هم‌پوشانی کامل دارند.
- smoke component برای Header language toggle.
- تست helperهای `statusLabel`, `shippingTypeLabel`, `stepLabel`, `actionLabel`, `transportLabel`.

## 14. ریسک‌ها

| ریسک | توضیح | کنترل پیشنهادی |
| --- | --- | --- |
| مخلوط شدن content مدیریتی با translation key | متن‌های `SiteSettings` از backend/content می‌آیند | schema را تغییر ندهید؛ فقط labelهای UI ترجمه شوند |
| ترجمه جعلی داده دامنه‌ای | نام شهر/کشور/کاربر از API می‌آید | فقط labelهای UI ترجمه شوند |
| شکستن LTR layout | بعضی componentها `dir="rtl"` hardcoded دارند | در فاز اجرا، componentها با `direction` سازگار شوند |
| ناقص بودن keyها | key در فارسی اضافه شود ولی در انگلیسی نه | check هم‌پوشانی keyها اضافه شود |
| بزرگ شدن `src/i18n.tsx` | keyها زیاد می‌شوند | فعلا قابل قبول است؛ split فایل‌ها فقط اگر پیچیدگی واقعی ایجاد شد |
| تغییر ناخواسته API | وسوسه ترجمه status در backend | ممنوع؛ ترجمه status در frontend helper انجام شود |

## 15. تصمیم آمادگی

وضعیت I18N-2A: `PLAN_READY`

این سند مجوز implementation نیست. معنی آن این است که frontend i18n foundation موجود تایید شد و مسیر تکمیل چندزبانه‌سازی به فازهای کوچک، frontend-only و قابل QA تقسیم شده است.

فاز بعدی پیشنهادی:

`I18N-2B`: تکمیل سطح عمومی و مشتری، بدون backend/database/API/schema change.
