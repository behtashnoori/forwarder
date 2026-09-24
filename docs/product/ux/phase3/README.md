# نمونه تعاملی فاز ۳ — Revision v2

`UX_STATUS=TARGET_CANDIDATE_AWAITING_PRODUCT_OWNER_APPROVAL`

- [Blueprint به‌روز](../PHASE3-OPERATIONAL-SHIPMENT-UX-BLUEPRINT-V1-FA.md)
- [موجودی صفحه‌ها](SCREEN-INVENTORY.md)
- [ممیزی داستان صفحه‌ها](STORYTELLING-AUDIT-V2.md)
- [ماتریس حالت‌ها](STATE-MATRIX.md)
- [سه سفر مرور مالک محصول](PRODUCT-OWNER-REVIEW.md)
- [رکورد اختیار](REVISION-V2-AUTHORITY.md)
- [شواهد مرور تازه Chrome](evidence/browser-v2/result.json)

## اجرای محلی مستقل

```powershell
python -m http.server 4182 --bind 127.0.0.1 --directory "D:\1-webapp\forwarder-dev\phase3-ux-prototype-revision-v2\docs\product\ux\phase3\prototype"
```

نشانی: [باز کردن Revision v2](http://127.0.0.1:4182/)

نمونه فعلی در همان پوشه نسخه اول بازبینی شده است؛ نمونه جداگانه‌ای ایجاد نشده است. داده‌ها ساختگی‌اند. تغییرات فقط در حافظه مرورگرند و با بازخوانی صفحه پاک می‌شوند. سیاست امنیت محتوای صفحه، اتصال شبکه و ارسال فرم را مسدود می‌کند. سرور فقط روی رایانه محلی گوش می‌دهد؛ به محصول یا پایگاه داده دسترسی ندارد.

## سه سفر

کارشناس: نمای کلی ← مشتری‌ها/کالا ← مسیر ← اجرا ← تخصیص ← اسناد ← روند حمل ← مشکلات/پیگیری ← تحویل ← بستن.

مشتری: خلاصه ← مسیر/موقعیت/روند ← کالا ← اسناد ← تحویل، روی دسکتاپ و عرض ۳۹۰.

مدیر: تعاریف پایه ← زمان‌های معمول ← شرایط بستن ← تصمیم استثنایی.

V1: `COMPLETED_NEEDS_CHANGE`. تأیید انسانی V2 انجام نشده است. کد محصول، canonical و Production تغییر نمی‌کنند. پیاده‌سازی و برنامه‌ریزی آن تا مرور V2 شروع نمی‌شوند.

[گزارش نهایی و همه وضعیت‌ها](REVISION-V2-REPORT.md) · [ممیزی زبان](MICROCOPY-AUDIT-V2.md)
