# بسته طراحی UX فاز ۳ Forwarder

وضعیت تمام surfaceها: `TARGET_PHASE3_UX`

## محتوا

- [Blueprint اصلی](../PHASE3-OPERATIONAL-SHIPMENT-UX-BLUEPRINT-V1-FA.md)
- [موجودی سطح‌ها](./SCREEN-INVENTORY.md)
- [ماتریس حالت‌ها](./STATE-MATRIX.md)
- [اسکریپت بازبینی Product Owner](./PRODUCT-OWNER-REVIEW.md)
- [Prototype قابل کلیک](./prototype/index.html)
- [شواهد مرورگر](./evidence/README.md)

## اجرای محلی

از ریشه repository:

```powershell
python -m http.server 4179 --directory docs/product/ux/phase3/prototype
```

سپس `http://127.0.0.1:4179/` را باز کنید.

Prototype هیچ وابستگی build ندارد، به API یا production وصل نمی‌شود و state آن فقط محلی و ناپایدار است.

## مسیر پیشنهادی مرور

1. Expert: نمای کلی → مشتری/Request → Cargo → مسیر → اجرای حمل → تخصیص → اسناد → Timeline → مشکلات → تحویل → Closure
2. Customer A: خلاصه → Timeline → Cargo → اسناد → Delivery، یک‌بار روی desktop و یک‌بار عرض ۳۹۰px
3. Organization Admin: تعاریف مرجع → زمان مرجع مسیر → الزام‌های closure → استثنای closure
4. حالت‌های رابط: loading، empty، error، denied و stale

## مرز

این پوشه طراحی و شواهد است. هیچ فایل آن نباید از runtime application import شود. تبدیل این UI به Product code فقط در مأموریت مستقل implementation planning و پس از Product Owner review مجاز است.
