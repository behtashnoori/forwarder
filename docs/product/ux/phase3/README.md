# نمونه تعاملی فاز ۳ — V2.1

`VISUAL_FIDELITY_CANDIDATE=READY_FOR_FINAL_PRODUCT_OWNER_REVIEW`

- [باز کردن نمونه](http://127.0.0.1:4183/)
- [بسته مرور نهایی مالک محصول](PRODUCT-OWNER-REVIEW.md)
- [مقایسه تصویری کنار هم](evidence/VISUAL-COMPARISON.html)
- [Visual DNA فعلی](FORWARDER-VISUAL-DNA-INVENTORY.md)
- [ممیزی ظاهر](VISUAL-FIDELITY-AUDIT-V2-1.md)
- [گزارش و وضعیت‌های نهایی](VISUAL-V2-1-REPORT.md)
- [رکورد اختیار](VISUAL-V2-1-AUTHORITY.md)
- [Blueprint](../PHASE3-OPERATIONAL-SHIPMENT-UX-BLUEPRINT-V1-FA.md)
- [داستان صفحه‌ها، بدون تغییر](STORYTELLING-AUDIT-V2.md) و [موجودی صفحه‌ها](SCREEN-INVENTORY.md)
- [آزمون رفتار](evidence/browser-v2-1/result.json) و [مرور بصری Chrome](evidence/browser-v2-1/visual-review.json)

## اجرای مستقل محلی

```powershell
python -m http.server 4183 --bind 127.0.0.1 --directory "D:\1-webapp\forwarder-dev\phase3-ux-visual-fidelity-v2-1\docs\product\ux\phase3\prototype"
```

فقط CSS مستقل و فونت محلی به V2 اضافه شده‌اند؛ app.js و متن/ترتیب صفحه‌ها همان V2 هستند. برچسب نسخه و وضعیت مرور در index.html به‌روز شده است. داده‌ها ساختگی و تغییرهای تعاملی در حافظه‌اند. اتصال API، auth، پایگاه داده و درخواست خارجی مرورگر وجود ندارد.

[مرجع محلی کد فعلی](http://127.0.0.1:4183/reference-current.html) فقط componentهای نمایشی canonical را با props ساختگی رندر می‌کند؛ صفحه واقعی محصول یا محیط عملیاتی نیست. نمونه اصلی هیچ وابستگی به آن ندارد.

V1: COMPLETED_NEEDS_CHANGE. V2: COMPLETED_CONDITIONAL_PASS_VISUAL_ALIGNMENT_REQUIRED. V2.1 و تأیید نهایی انسانی: NOT_RUN؛ بسته آماده مرور است. کد محصول و canonical دست‌نخورده‌اند؛ ادغام، push، انتشار و برنامه‌ریزی پیاده‌سازی انجام نشده است.
