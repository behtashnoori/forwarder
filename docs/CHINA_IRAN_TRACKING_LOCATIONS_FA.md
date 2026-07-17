# نقاط ردیابی سبک چین–ایران

## هدف
این قابلیت به کارشناس اجازه می‌دهد در همان گزارش دستی واحد حمل، یک نقطه پرتکرار را انتخاب کند یا محل را آزادانه بنویسد.

## دامنه سبک و نقش کارشناس
کارشناس مسئول انتخاب یا ورود محل است. هیچ تشخیص، تطبیق فازی، مسیریابی یا استنباط خودکاری انجام نمی‌شود.

## TrackingLocationReference
این جدول lookup داخلی شامل نام فارسی/انگلیسی، کشور، نوع، alias، ترتیب و وضعیت فعال است. `internal_key` فقط شناسه فنی داخلی است و کد رسمی Customs، Port یا UN/LOCODE نیست. ردیف‌های اولیه `internal_reference` هستند.

## انتخاب از فهرست و ورود محل آزاد
API و فرم expert هر دو مسیر را پشتیبانی می‌کنند. clients قدیمی همچنان می‌توانند فیلد legacy `location` را بفرستند یا محل را خالی بگذارند.

## Snapshot تاریخی
هنگام انتخاب reference، نام و کشور در `ShipmentTransportUnitUpdate` کپی می‌شوند. ویرایش یا غیرفعال‌سازی reference تاریخچه قبلی را تغییر نمی‌دهد.

## نقاط چین، ترانزیت و ایران
Bootstrap فقط نقاط عملیاتی رایج چین تا ایران را ایجاد می‌کند: بنادر/ترمینال‌های چین، نقاط منتخب آسیای مرکزی، پاکستان و افغانستان، و gatewayها/شهرهای ایران.

## Yiwu، Xi'an و Ash / اش
Yiwu و Xi'an دو reference مستقل با aliasهای صریح هستند. برای `Ash` یا `اش` reference ساخته نمی‌شود؛ ورود آن فقط free text است و به Yiwu، Xi'an یا محل دیگری نگاشت نمی‌شود.

## اوش

- Osh در جنوب قرقیزستان قرار دارد.
- `country_code` آن `KG` است.
- Osh شهر یا مرز قزاقستان نیست و نقطه مرزی مستقیم نیز محسوب نمی‌شود.
- Osh یک هاب ترانزیتی جاده‌ای–ریلی است که در این سامانه با نوع کنترل‌شده `commercial_hub` نگهداری می‌شود.
- انتخاب Osh توسط کارشناس کاملاً دستی است.
- سیستم عبور محموله از Osh را استنباط نمی‌کند و وجود آن در فهرست به معنی عبور همه محموله‌ها از Osh نیست.
- aliasهای صریح آن فقط `Osh`، `Ош` و `اوش` هستند.
- `Ash / اش` به‌صورت خودکار alias اوش نیست، به اوش نگاشت نمی‌شود و فقط به‌عنوان متن آزاد ثبت می‌شود.

## Admin management
Admin می‌تواند فهرست را ببیند، جست‌وجو کند، ردیف بسازد، نام و metadata نمایشی را تغییر دهد، مرتب کند یا غیرفعال سازد. حذف فیزیکی ارائه نشده است.

## موارد خارج از دامنه
این feature برنامه‌ریزی یا اعتبارسنجی مسیر، Corridor/CorridorLeg، ETA، نقشه/GIS، geolocation، BorderCrossing master، Customs master data یا Port master رسمی ارائه نمی‌کند.

## Migration
Revision `20260725_add_tracking_location_reference` پس از `20260720_expand_reference_data_identity` جدول reference و snapshot fieldهای nullable را اضافه می‌کند و داده جاری را تغییر نمی‌دهد.

## Bootstrap
`python manage.py bootstrap-china-iran-tracking-locations --database <name>` پیش‌فرض dry run است. فقط با `--apply` می‌نویسد؛ idempotent است، حذف ندارد و تنها display fieldهای صریح را refresh می‌کند.

## Rollback
Downgrade ستون‌های افزوده و جدول جدید را حذف می‌کند. پیش از rollback باید وابستگی گزارش‌های جدید ارزیابی شود؛ داده bootstrap در migration قرار ندارد.

## Candidate UAT و محدودیت Production
ابتدا migration و bootstrap روی دیتابیس disposable و clone کاندیدا آزموده می‌شوند. ارتقای Candidate فقط پس از عبور clone مجاز است. این feature مجوز Production یا deployment ایجاد نمی‌کند.
