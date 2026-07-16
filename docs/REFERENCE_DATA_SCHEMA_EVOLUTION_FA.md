# تکامل Schema داده‌های مرجع

## 1. مسئله
Schema میراثی برای همه دامنه‌ها هویت پایدار، چرخه عمر و منشأ داده ندارد. این سند تصمیم فاز سازگار با گذشته را ثبت می‌کند؛ هیچ داده مرجع یا کد رسمی ایجاد نمی‌شود.

## 2. Expand–Backfill–Contract
مسیر مصوب سه مرحله دارد: **Expand** ستون‌ها و جداول nullable را اضافه می‌کند؛ **Backfill** در آینده فقط نگاشت صریح مالک داده را اعمال می‌کند؛ **Contract** پس از تکمیل و ممیزی Backfill محدودیت‌های نهایی را برقرار می‌کند. این تغییر فقط Expand است.

## 3. وضعیت فعلی
Country و CustomsOffice هویت پایدار دارند. Province فقط code اختیاری دارد. County، City و IranPort کد پایدار ندارند. PortLocation و CustomsProvinceMapping نیز وجود نداشتند.

## 4. Stable codes
Country.code و CustomsOffice.code globally unique باقی می‌مانند. Province در محدوده Country، County در محدوده Province، City در محدوده County و IranPort در محدوده Country یکتا است. همه کدهای جدید nullable و بدون default هستند.

## 5. Parent relationships
Province.country_id و IranPort.country_id در Expand nullable هستند. parentهای موجود County/City حفظ می‌شوند. هیچ parentی از نام استنباط یا ایجاد نمی‌شود.

## 6. Lifecycle
`is_active` حذف فیزیکی نیست. `effective_from` و `effective_to` اختیاری‌اند و پایان بازه نمی‌تواند قبل از آغاز باشد. انقضا به‌تنهایی رکورد را حذف یا غیرفعال نمی‌کند.

## 7. Provenance
فیلدهای nullable شامل `source_organization`، `source_reference`، `source_version` و `dataset_id` هستند. این فیلدها نباید credential یا اطلاعات تماس شخصی نگه دارند.

## 8. Port identity
IranPort.code و country_id اضافه می‌شوند؛ province_id، IDها، نام‌ها و رفتار API فعلی حفظ می‌شوند. هیچ code یا Country ساخته نمی‌شود.

## 9. Port physical location
PortLocation منبع نرمال آینده است و حداکثر یک location فعال برای هر Port دارد. migration هیچ ردیفی ایجاد نمی‌کند؛ هر ۱۲ Port فعلی نیازمند Backfill مالک داده است.

## 10. Port service coverage
PortProvinceMapping پوشش خدمت است، نه مکان فیزیکی. uniqueness روی `(port_id, province_id)` فقط پس از preflight duplicate اعمال می‌شود. `is_recommended` حفظ و `is_preferred` جداگانه افزوده می‌شود.

## 11. Customs identity
یکتایی فعلی CustomsOffice.code و controlled type حفظ می‌شود. هیچ Customs record seed نمی‌شود.

## 12. Port-Customs relationship
رابطه و uniqueness فعلی حفظ و فقط lifecycle/provenance افزوده می‌شود.

## 13. Customs coverage
CustomsProvinceMapping با FKهای صریح و uniqueness روی `(customs_office_id, province_id)` ایجاد می‌شود و migration آن را خالی می‌گذارد.

## 14. Nullable transition
کدها، Country FKهای جدید و provenance تا پایان Backfill nullable می‌مانند. چند NULL مجاز است؛ کد non-null تکراری در parent یکسان مجاز نیست.

## 15. Backfill requirements
کد و parent فقط از mapping صریح و تأییدشده مالک داده می‌آید. وضعیت فعلی پس از Expand برابر `BACKFILL_REQUIRED` است.

## 16. Contract migration
NOT NULL، اتکای انحصاری به PortLocation و provenance اجباری فقط در migration جداگانه پس از Backfill کامل و reconciliation مجاز است.

## 17. Compatibility
APIهای عمومی همچنان ID و نام موجود را مصرف می‌کنند؛ فیلد nullable جدید وابستگی جدیدی برای clientها ایجاد نمی‌کند. Seedها مجاز به تولید کد نیستند.

در تست Country، محدودیت قدیمی سه‌کاراکتری با prefix عمومی `TEST-` سازگار نیست؛ بنابراین فقط برای Country از کد رزروشده و آشکارا مصنوعی `ZZ` استفاده می‌شود. این استثنا مجوز استفاده از `ZZ` در package یا داده واقعی نیست؛ سایر کدهای synthetic باید prefix مصوب داشته باشند.

## 18. Rollback
Downgrade فقط objectهای همین migration را حذف می‌کند. مقادیر احتمالی واردشده در ستون‌های Expand با downgrade از دست می‌روند؛ رکوردها و ستون‌های میراثی حذف نمی‌شوند.

## 19. UAT
اعتبارسنجی ابتدا روی PostgreSQL disposable و clone انجام می‌شود. Candidate فقط پس از موفقیت clone قابل upgrade است. `forwarder_db` همیشه read-only است.

## 20. Production restrictions
این Schema مجوز import، Backfill، deploy یا cutover نیست. Production همچنان **NO-GO** و Customs data همچنان `CUSTOMS_REFERENCE_DATA_PENDING` است.
