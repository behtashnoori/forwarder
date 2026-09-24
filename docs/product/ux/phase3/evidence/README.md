# شواهد جاری V2.1

[مرور رفتاری تازه](browser-v2-1/result.json) · [مرور بصری تازه](browser-v2-1/visual-review.json) · [مقایسه کنار هم](VISUAL-COMPARISON.html) · [گزارش](../VISUAL-V2-1-REPORT.md)

شواهد browser/ و browser-v2/ و گزارش‌های V1/V2 تاریخی‌اند؛ دست‌نخورده حفظ شده‌اند. نتیجه انسانی V2 اکنون COMPLETED_CONDITIONAL_PASS_VISUAL_ALIGNMENT_REQUIRED است. V2.1 آماده مرور است و نتیجه انسانی NOT_RUN می‌ماند.

---

# شواهد تاریخی مرورگر Prototype نسخه اول

**این بخش و فایل‌های browser/ شواهد تاریخی V1 هستند. نتیجه انسانی V1 اکنون COMPLETED_NEEDS_CHANGE است. نتیجه تازه V2 در [browser-v2/result.json](browser-v2/result.json) و [گزارش Revision v2](../REVISION-V2-REPORT.md) ثبت می‌شود.**

نوع شاهد: `UX PROTOTYPE EVIDENCE — NOT PRODUCT RUNTIME QUALIFICATION`
Prototype: `TARGET_PHASE3_UX`
نتیجه: `BROWSER_PROTOTYPE_REVIEW=PASS`
داده: `SYNTHETIC_DATA_ONLY=YES`

## محیط و روش

- اجرا روی static server محلی: `http://127.0.0.1:4179/`
- مرور خودکار: Chromium از طریق Playwright
- desktop viewport: `1440x900`
- Customer mobile viewport: `390x844`
- درخواست بیرونی: صفر
- console error: صفر
- page error: صفر
- زمان ثبت machine-readable: `browser/result.json`

## نتایج کنترل خودکار

| کنترل | نتیجه |
|---|---|
| Prototype محلی load می‌شود | `PASS` |
| همه سطح‌های اصلی Expert قابل دستیابی‌اند | `PASS` |
| over-allocation مسدود و allocation معتبر پذیرفته می‌شود | `PASS` |
| projection مشتری A نام/هویت مشتری B/C را نشان نمی‌دهد | `PASS` |
| صفحه Customer در ۳۹۰px horizontal overflow ندارد | `PASS` |
| مفهوم فعال‌سازی تعریف سازمانی قابل کلیک است | `PASS` |
| stale/degraded صریح است و سلامت کاذب القا نمی‌کند | `PASS` |
| dependency شبکه production/خارجی وجود ندارد | `PASS` |
| خطای console یا page وجود ندارد | `PASS` |

## تصاویر اجباری

| شناسه | شاهد | موضوع |
|---|---|---|
| A | [A-expert-shipment-overview-desktop.png](./browser/A-expert-shipment-overview-desktop.png) | Expert Shipment Overview |
| B | [B-cargo-allocation-multi-customer.png](./browser/B-cargo-allocation-multi-customer.png) | تخصیص چندمشتری |
| C1 | [C1-planned-and-branched-route.png](./browser/C1-planned-and-branched-route.png) | planned/actual و مسیر منشعب |
| C2 | [C2-route-stage-transport-execution.png](./browser/C2-route-stage-transport-execution.png) | چند execution، means/unit/Carrier |
| D | [D-timeline-reported-location-correction.png](./browser/D-timeline-reported-location-correction.png) | Timeline، reported location و correction |
| E | [E-exception-customer-safe-explanation.png](./browser/E-exception-customer-safe-explanation.png) | internal در برابر customer-safe explanation |
| F | [F-partial-delivery.png](./browser/F-partial-delivery.png) | partial delivery و evidence |
| G | [G-closure-blocker.png](./browser/G-closure-blocker.png) | closure checklist و blocker |
| H1 | [H1-customer-shared-shipment-desktop.png](./browser/H1-customer-shared-shipment-desktop.png) | Customer shared-Shipment desktop |
| H2 | [H2-customer-shared-shipment-mobile-390.png](./browser/H2-customer-shared-shipment-mobile-390.png) | Customer mobile 390px |
| I | [I-admin-reference-configuration.png](./browser/I-admin-reference-configuration.png) | Admin reference configuration |
| J | [J-stale-degraded-state.png](./browser/J-stale-degraded-state.png) | stale/degraded state |

نتیجه کامل machine-readable در [result.json](./browser/result.json) ثبت شده است.

## حدود شاهد

این شواهد فقط نشان می‌دهند Prototype ایزوله، clickable و از نظر presentation قابل مرور است. موارد زیر از آن استنتاج نمی‌شوند:

- پذیرش Product Owner؛
- Human Product Walkthrough؛
- صحت runtime، API، authorization، persistence یا database؛
- PASS سفرهای یکپارچه Product؛
- production readiness یا release readiness.

بنابراین:

`UX_PRODUCT_OWNER_REVIEW=NOT_RUN`
`HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN`
`GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`
`RELEASE_READY=NO`
