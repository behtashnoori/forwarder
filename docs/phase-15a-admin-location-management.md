# Phase 15A — مدیریت مبدا و مقصد توسط ادمین

## هدف
تمام داده‌های مبدا/مقصد حمل داخلی و بین‌المللی باید توسط ادمین قابل تعریف،
ویرایش، تغییر و غیرفعال‌سازی باشند؛ پیش از این این داده‌ها فقط از طریق
اسکریپت‌های seed دستی قابل تغییر بودند و هیچ CRUD ادمینی نداشتند.

## دامنه
موجودیت‌هایی که فرم انتخاب مبدا/مقصد را تغذیه می‌کنند:

| حوزه | موجودیت | جدول |
| --- | --- | --- |
| داخلی | استان → شهرستان → شهر | `province`, `county`, `city` |
| بین‌المللی | کشور → شهر/بندر | `country`, `international_city` |
| مبادی ورود ایران | بندر ورودی | `iran_port` |

## بک‌اند
- سرویس اعتبارسنجی و CRUD: `backend/services/location_admin_service.py`
  - والدها هرگز به‌صورت ضمنی ساخته نمی‌شوند؛ `county_id`/`province_id`/`country_id`
    باید از قبل موجود باشند.
  - `city.province_id` همیشه از شهرستان انتخابی مشتق می‌شود تا سلسله‌مراتب سازگار بماند.
  - کد کشور یکتا و به حروف بزرگ نرمال می‌شود.
  - «حذف» = غیرفعال‌سازی نرم (`is_active = False`)؛ رکورد فیزیکی حذف نمی‌شود
    (هم‌راستا با `PRODUCTION_REFERENCE_DATA_REQUIREMENTS_FA.md`).
- روت‌های ادمین (فقط نقش `admin`): `backend/routes/location_admin.py`
  با پیشوند `/api/admin/locations/<resource>` و متدهای
  `GET` (لیست، شامل غیرفعال‌ها با `include_inactive=true`)،
  `POST`، `PUT`/`PATCH`، `DELETE` (غیرفعال‌سازی).
- ثبت blueprint در `backend/routes/__init__.py`.
- تست: `backend/tests/test_location_admin.py` (سرویس + لایهٔ HTTP/احراز هویت).

## فرانت‌اند
- توابع کلاینت در `src/lib/api.ts` (`fetchAdmin*`, `createAdminLocation`,
  `updateAdminLocation`, `deactivateAdminLocation`).
- تب جدید «مبدا و مقصد» در پنل ادمین: `src/components/LocationsAdminTab.tsx`
  با سه زیربخش (داخلی/بین‌المللی/بنادر) و انتخاب آبشاری استان→شهرستان→شهر و
  کشور→شهر. اتصال در `src/pages/AdminPanel.tsx`.

## نکته
فرم مشتری از همان endpointهای عمومی `locations.py` می‌خواند که فقط رکوردهای
`is_active` را برمی‌گردانند؛ بنابراین تغییرات ادمین بلافاصله در دراپ‌داون‌های
مبدا/مقصد منعکس می‌شود بدون تغییر در جریان ثبت سفارش.
