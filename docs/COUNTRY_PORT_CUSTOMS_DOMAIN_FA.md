# مدل Country، Port و Customs

## تصمیم دامنه

کشور با کلید پایدار `Country.code` شناخته می‌شود و ایران دقیقاً یک رکورد با کد `IR` دارد. Province، County و City جغرافیای داخلی‌اند. `IranPort.province_id` موقعیت فیزیکی استان بندر است، ولی `PortProvinceMapping` پوشش عملیاتی/تجاری است.

`CustomsOffice` موجودیتی مستقل با کد یکتا، نوع کنترل‌شده، Country الزامی و Province/County/City اختیاری است. `PortCustomsOffice` رابطه صریح بندر و گمرک را نگه می‌دارد. پوشش گمرک فعلاً مدل نشده چون نیاز تأییدشده‌ای وجود ندارد.

## مالکیت و Seed

- Country Seed فقط Country می‌سازد.
- bootstrap جغرافیا فقط Province، County و City می‌سازد.
- Port Seed هیچ Country یا geography نمی‌سازد و پیش از write همه مراجع را اعتبارسنجی می‌کند.
- قابلیت Customs هیچ geography نمی‌سازد.
- هیچ رکورد گمرکی حدس زده یا از نام Port/City استنتاج نمی‌شود.

## Migration و API

revision `20260717_add_customs_office_domain` فقط جدول‌های `customs_office` و `port_customs_office` و constraint/indexهای آن‌ها را ایجاد می‌کند. API داخلی `/api/customs` با مجوز admin، empty-state، CRUD محدود master data و مدیریت رابطه را ارائه می‌دهد. UI مدیریت به فاز جداگانه موکول است.

## وضعیت داده

`CUSTOMS_REFERENCE_DATA_PENDING`: Candidate دارای صفر Customs و صفر Port-Customs است. این وضعیت مانع UAT غیرگمرکی نیست، اما UAT داده واقعی Customs را مجاز نمی‌کند. داده 31/425/425 و پوشش 372 فقط UAT است و مجوز Production نیست.
