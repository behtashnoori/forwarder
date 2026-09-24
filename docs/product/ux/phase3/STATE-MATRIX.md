# ماتریس حالت‌های تجربه فاز ۳

وضعیت: `TARGET_PHASE3_UX`  
اصل: هیچ اطلاعات حیاتی فقط با رنگ منتقل نمی‌شود؛ label، icon/marker و توضیح متنی همراه رنگ هستند.

## ۱. واژگان حالت

| حالت | معنای UX | ارائه الزامی | نباید با آن اشتباه شود |
|---|---|---|---|
| `normal/current` | داده معتبر و context جاری | label «جاری/در حال حمل»، marker و زمان | completed یا live GPS |
| `incomplete` | داده هنوز کامل نشده ولی incident رخ نداده است | label «اطلاعات ناقص»، field مفقود و اثر آن | operational problem |
| `empty` | هنوز آیتمی وجود ندارد | empty state، دلیل و اقدام ممکن | load failure |
| `loading` | داده در حال دریافت/آماده‌سازی است | skeleton/progress و حفظ context | empty |
| `denied` | actor اجازه دیدن/اقدام ندارد | پیام permission-safe و مسیر بازگشت | not found یا error فنی |
| `error` | عملیات/دریافت ناموفق است | پیام امن، retry در صورت مجاز، reference | business blocker |
| `stale/degraded` | تازگی/پایش قابل اتکا نیست | timestamp، label «قدیمی»، توضیح اینکه نبود هشدار سلامت را ثابت نمی‌کند | normal/current |
| `needs attention` | اکنون باید بررسی شود | دلیل attention و CTA contextual | incident یا blocker قطعی |
| `operational problem` | اتفاق عملیاتی واقعی با اثر | عنوان، impact، state، explanation و follow-up | اطلاعات ناقص |
| `blocked/required` | پیش‌شرط/الزام مانع اقدام مشخص است | دلیل، requirement، راه رفع و scope انسداد | مسدود بودن کل Shipment |
| `completed` | نتیجه تعریف‌شده به پایان رسیده است | label/marker کامل و evidence مرتبط | closed Shipment مگر contract بگوید |
| `historical/corrected` | داده قبلی معتبر تاریخی یا بعداً اصلاح‌شده است | مقدار قبلی، زمان، علت/اشاره اصلاح و مقدار معتبر جاری | حذف یا overwrite |

## ۲. نگاشت سطح‌ها به حالت‌ها

| سطح/Component | Current | Incomplete | Empty | Loading | Denied | Error | Stale | Blocked | Completed | Historical/Corrected |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Shipment header | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Overview progress | ✓ | ✓ | — | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| Customers / Requests | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Cargo details | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Requested / planned / actual | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Route planner | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Transport execution | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cargo allocation | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Documents | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Timeline / location | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Exception / follow-up | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Delivery | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Closure | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Customer projection | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ | ✓ |
| Admin references | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

علامت ✓ یعنی طراحی باید آن حالت را بدون تغییر semantics پشتیبانی کند؛ همه ترکیب‌ها لزوماً در نسخه اول runtime لازم نیستند.

## ۳. سناریوهای component-level

| context | محرک نمونه | state قابل مشاهده | پیام/اقدام مورد انتظار |
|---|---|---|---|
| Cargo HS Code | مقدار هنوز ثبت نشده | `incomplete` | «HS Code هنوز تکمیل نشده»؛ ادامه کار مجاز، الزام آینده `DECISION_NEEDED` |
| Transport detail | پلاک TR-24 نرسیده | `incomplete` | detail مفقود و اثر محدود؛ incident نیست |
| Base definition | واگن یخچالی سازمانی فعال نیست | `blocked/required` | فقط اقدام وابسته متوقف؛ مسیر روشن به Organization Admin؛ بدون free-text |
| Allocation B1 | ۸۰ از ۹۰ کارتن | `incomplete + attention` | ۱۰ باقیمانده، ادامه مجاز و CTA تخصیص |
| Allocation B1 | درخواست ۱۱ با باقیمانده ۱۰ | `error/block` | خطای inline؛ submit رد می‌شود؛ current allocation عوض نمی‌شود |
| Route | stage بعدی هنوز تعریف نشده | `incomplete` | افزودن مرحله؛ سایر contextها قابل استفاده‌اند |
| Reported location | آخرین گزارش از threshold قدیمی‌تر است | `stale/degraded` | timestamp و اخطار صریح؛ نبود مشکل به معنی سلامت نیست |
| Location correction | گزارش قبلی اصلاح شده | `historical/corrected` | گزارش قبلی باقی می‌ماند؛ معتبر جدید برجسته می‌شود |
| Documents | scope سند موجود ولی visibility کافی نیست | `denied` | نام/metadata حساس افشا نمی‌شود؛ پیام عمومی مجوز |
| Customer issue | متن customer-facing خالی است | `needs attention` برای Expert؛ safe notice برای Customer | پیام امن پیش‌فرض deterministic؛ توضیح داخلی پنهان |
| Delivery A1 | ۶۰ + ۴۰، یکی evidence ناقص | `completed delivery + incomplete evidence` | مقدار کامل تحویل، evidence ناقص جدا؛ Shipment خودکار بسته نمی‌شود |
| Closure | رسید DL-305 و follow-up AC-88 باز است | `blocked` | requirementها، دلیل و مسیر رفع؛ Expert bypass ندارد |
| Closure exception | Admin دلیل و approval می‌دهد | `exceptional/historical` | explicit exception، approver/time؛ requirement PASS کاذب نمی‌شود |

## ۴. state gallery قابل کلیک

دکمه «حالت‌های رابط» در Prototype حالت‌های زیر را روی همان context نمایش می‌دهد:

- Normal: نمای role جاری و سناریوی اصلی؛
- Loading: skeleton با label خوانا؛
- Empty: نبود داده با اقدام ممکن؛
- Error: failure امن با retry نمایشی؛
- Denied: پیام بدون نشت داده؛
- Stale/degraded: banner زمان‌دار و هشدار نبود قطعیت.

این gallery برای نقد presentation است و contract خطا یا threshold runtime را تعیین نمی‌کند.

## ۵. قواعد نوشتاری و بصری

- `incomplete`: کهربایی ملایم + عبارت «اطلاعات ناقص/تکمیل نشده»؛
- `attention`: کهربایی + دلیل «چرا اکنون؟»؛
- `problem`: قرمز محدود + عنوان مشکل و impact؛
- `stale`: بنفش/کهربایی + timestamp و واژه «قدیمی/کاهش اطمینان»؛
- `completed`: سبز محدود + نتیجه مشخص؛
- `blocked`: قرمز با واژه «مسدود/الزام» و راه رفع؛
- `current`: آبی + واژه «جاری/در حال اجرا»؛
- `corrected`: بنفش + ارتباط بصری گزارش قدیم و جدید.

در هیچ مورد، نقطه یا رنگ به‌تنهایی معنای state نیست.

