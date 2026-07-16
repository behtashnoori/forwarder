# ستون‌های CSV بسته Backfill

`record_id` فقط locator موقت است. `record_fingerprint_sha256` drift را تشخیص می‌دهد. ستون‌های `current_*` snapshot زمان export هستند و ستون‌های `proposed_*` فقط توسط مالک داده تکمیل می‌شوند. `owner_decision` و `owner_notes` مستندات تصمیم‌اند. هیچ proposed value از نام یا ID تولید نمی‌شود.

`port_locations.csv` از locator و fingerprint بندر به‌همراه کدهای صریح Country/Province و County/City اختیاری استفاده می‌کند. مقدار `location_status` یکی از `confirmed`، `provisional`، `historical` یا `unknown` است.

## ستون‌های عمومی

ترتیب header ثابت است: `record_id`، `record_fingerprint_sha256`، `current_name_fa`، `current_name_en`، `current_code`، `current_parent_path`، `current_parent_ids`، `current_is_active`، `current_effective_from`، `current_effective_to`، چهار ستون provenance فعلی، سپس `proposed_code`، `proposed_country_code`، `proposed_parent_code`، `proposed_is_active`، `proposed_effective_from`، `proposed_effective_to`، چهار ستون provenance پیشنهادی و در پایان `owner_decision` و `owner_notes`.

تاریخ‌ها ISO-8601 (`YYYY-MM-DD`) و booleanها فقط `true` یا `false` هستند. کد پیشنهادی با حرف/عدد بزرگ آغاز می‌شود و فقط حروف بزرگ، عدد، نقطه، underscore و hyphen دارد. کد، parent، lifecycle و provenance همگی باید صریحاً توسط مالک داده تأمین شوند؛ ابزار هیچ مقدار پیشنهادی نمی‌سازد یا استنباط نمی‌کند.

## قرارداد دامنه‌ها

- `countries.csv`: فقط lifecycle و provenance رکورد موجود؛ ایجاد Country ممنوع است.
- `provinces.csv`: `proposed_code` و `proposed_country_code`؛ parent از نام استنباط نمی‌شود.
- `counties.csv`: کد در scope همان Province موجود؛ جابه‌جایی Province ممنوع است.
- `cities.csv`: کد در scope همان County موجود؛ جابه‌جایی County ممنوع است.
- `ports.csv`: کد و Country صریح برای Port موجود؛ ایجاد Port ممنوع است.
- فایل‌های coverage و Customs فقط metadata رکورد موجود را تغییر می‌دهند؛ ایجاد Customs یا mapping جدید ممنوع است.
- `port_locations.csv`: ستون‌های `port_record_id`، `port_fingerprint_sha256`، کدهای hierarchy، lifecycle، provenance و تصمیم مالک را دارد و تنها create مجاز در این package type است.

## ایمنی spreadsheet

exporter برای مقدار snapshot خطرناک marker نسخه‌دار `'FORWARDER-CSV-SAFE:'` می‌گذارد. marker بخشی از مقدار دیتابیس نیست. validator آن را فقط در ستون‌های exporter-owned باز می‌کند. مقدار اصلی که خودش با apostrophe آغاز شده باشد بدون تغییر حفظ می‌شود. هر formula prefix خام در فیلدهای owner/proposed با `CSV_INJECTION_RISK` رد می‌شود.
