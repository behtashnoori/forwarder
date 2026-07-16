# الزامات داده‌های مرجع Production سامانه فورواردری

## 1. هدف
تعریف قرارداد fail-closed برای دریافت، تأیید و ورود آینده داده مرجع؛ این سند مجوز import نیست.

## 2. وضعیت فعلی Candidate
سلسله‌مراتب 31/425/425 و 372 نگاشت پوشش بندر snapshot میراثی و فقط UAT هستند. داده معتبر Customs وجود ندارد.

## 3. تفاوت UAT و Production
داده UAT برای آزمون رفتار است؛ Production فقط dataset نسخه‌دار، تأییدشده و checksum-verified می‌پذیرد.

## 4. Country
کلید طبیعی code پایدار؛ نام فارسی و انگلیسی، active، effective date، source، version و checksum الزامی است.

## 5. Province
code پایدار و country_code والد؛ همان metadata و سیاست تغییر کنترل‌شده الزامی است.

## 6. County
code پایدار و province_code والد؛ ایجاد ضمنی یا fuzzy match ممنوع است.

## 7. City
code پایدار و county_code والد؛ رابطه والد و نام فارسی الزامی است.

## 8. Port
code پایدار، نام فارسی/انگلیسی، نوع و active الزامی است.

## 9. Port physical location
port_code و سلسله‌مراتب مکانی معتبر با تاریخ اثر الزامی است.

## 10. Port service coverage
port_code و کد ناحیه خدمت باید unique و قابل ممیزی باشد؛ 372 نگاشت فعلی UAT-only است.

## 11. Customs Office
code پایدار، نام‌ها، نوع و مکان لازم است؛ اکنون dataset authoritative موجود نیست.

## 12. Port-Customs relationship
هر دو طرف باید از قبل وجود داشته باشند؛ نوع رابطه، active و تاریخ اثر لازم است.

## 13. Customs service coverage
customs_code و ناحیه خدمت باید معتبر و unique باشند.

## 14. Stable codes
تغییر معنای code ممنوع؛ rename فقط نام را تغییر می‌دهد و code جدید رکورد جدید است.

## 15. UTF-8 and Unicode normalization
UTF-8 بدون BOM و Unicode NFC؛ حذف فاصله ابتدا/انتها و منع control character الزامی است.

## 16. Dataset version
نسخه immutable و یکتا برای هر تحویل لازم است.

## 17. Effective date
تاریخ ISO-8601 و timezone/تقویم مشخص لازم است.

## 18. Source organization
نام سازمان، مرجع انتشار و شناسه سند منبع ثبت شود.

## 19. Ownership and approval
مالک داده و Product Owner باید approval قابل ممیزی بدهند؛ بدون آن import ممنوع است.

## 20. Checksum
SHA-256 هر فایل و manifest کل dataset پیش از dry-run و apply تطبیق داده شود.

## 21. Update policy
هر update نسخه جدید، diff، دلیل و approval می‌خواهد؛ overwrite خام ممنوع است.

## 22. Deactivation and history
حذف فیزیکی پیش‌فرض ممنوع؛ deactivation با effective date و history انجام شود.

## 23. Validation rules
code یکتا، والد موجود، رابطه بدون orphan، coverage یکتا، تاریخ معتبر و schema کامل لازم است.

## 24. Import contract
import آینده ابتدا checksum/version، سپس dry-run قطعی و گزارش کامل را اجرا می‌کند؛ fuzzy/numeric-ID matching، ایجاد ضمنی، partial import و orphan ممنوع است.

## 25. Rollback
هر batch شناسه و manifest دارد؛ rollback تمرین‌شده باید کل batch را transactionally برگرداند.

## 26. Production acceptance gates
تأیید مالک، همه datasetهای authoritative، checksum/version، dry-run بدون خطا، backup و rollback rehearsal الزامی است. تا آن زمان Production cutover و import ممنوع و وضعیت NO-GO است.

## قرارداد ستون‌ها
همه objectها `code,name_fa,name_en,parent_code,is_active,effective_date,source_organization,source_version,checksum,change_policy` را حسب موضوع دارند. `code` کلید طبیعی، `parent_code` رابطه والد، `is_active` بولی، تاریخ ISO، source/version منشأ، checksum صحت و change_policy قاعده تغییر است. فایل‌های template seed نیستند و داده حدسی ندارند.
