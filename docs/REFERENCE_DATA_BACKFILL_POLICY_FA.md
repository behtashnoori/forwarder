# سیاست Backfill هویت داده‌های مرجع

1. کدها فقط توسط مالک داده تأییدشده تأمین می‌شوند.
2. کد از نام فارسی یا انگلیسی تولید نمی‌شود.
3. کد از ID عددی تولید نمی‌شود.
4. هر نگاشت باید صریح باشد.
5. mapping باید رکورد موجود را دقیقاً مشخص کند؛ ID فقط locator موقت reconciliation است.
6. سلسله‌مراتب parent باید دقیقاً منطبق باشد.
7. کد پیشنهادی تکراری کل Backfill را رد می‌کند.
8. apply جزئی ممنوع است.
9. dry run اجباری است.
10. apply باید در یک transaction PostgreSQL انجام شود.
11. audit report اجباری است.
12. rehearsal روی Candidate clone اجباری است.
13. Contract migration فقط پس از Backfill کامل مجاز است.
14. Production approval مستقل و همچنان الزامی است.

این فاز command اعمال Backfill ندارد. inventory خروجی نیز هیچ کدی پیشنهاد یا تولید نمی‌کند و نباید commit شود.
