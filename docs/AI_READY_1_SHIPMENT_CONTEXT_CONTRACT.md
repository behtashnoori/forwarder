# AI-READY-1 — ShipmentRequest Context Contract

## 1. وضعیت سند

- نام قرارداد: `shipment_request_context`
- نسخه قرارداد: `1.0`
- پروفایل: `operational_minimum_v1`
- سطح طبقه‌بندی کل خروجی: `confidential`
- حالت اجرا: `read_only`
- پیاده‌سازی مرجع: `backend/services/shipment_context_service.py`
- تست قرارداد: `backend/tests/test_shipment_context_service.py`
- وضعیت انتشار API: هیچ route یا endpointای در این فاز اضافه نشده است.

این سند رفتار commit مربوط به AI-READY-1 را تعریف می‌کند. هر تغییر ناسازگار در نام‌ها، ترتیب، معنا، سیاست محرمانگی یا قواعد طبقه‌بندی باید با نسخه جدید قرارداد منتشر شود.

## 2. هدف

این قرارداد یک projection ساخت‌یافته، نسخه‌دار و قطعی از داده‌های موجود `ShipmentRequest` می‌سازد تا در فازهای بعد بتوان از آن به‌عنوان ورودی امن برای موارد زیر استفاده کرد:

- قواعد deterministic؛
- نمونه‌های synthetic یا de-identified؛
- mock providerها؛
- پیشنهادهای آینده که پیش از هر اثر عملیاتی توسط انسان بازبینی می‌شوند.

این قرارداد system of record جدیدی ایجاد نمی‌کند. `ShipmentRequest` همچنان منبع اصلی داده است و `ShipmentRequest.status` تنها وضعیت canonical چرخه عملیاتی در خروجی محسوب می‌شود.

## 3. موارد خارج از محدوده

AI-READY-1 موارد زیر را پیاده‌سازی نمی‌کند:

- runtime AI agent؛
- اتصال به AI provider یا مدل زبانی؛
- AI SDK، embedding یا vector database؛
- دریافت یا پردازش ایمیل واقعی؛
- mailbox، IMAP، SMTP یا webhook؛
- attachment ingestion یا parsing؛
- workflow خودکار؛
- route یا API جدید؛
- database query، write، flush یا commit؛
- migration، model/schema change یا dependency جدید؛
- frontend یا deployment change.

خروجی این قرارداد برای write-back معتبر نیست و هیچ consumerی نباید آن را مجوز تغییر وضعیت، ارسال پیام، ساخت CRM record یا اجرای عملیات دامنه تلقی کند.

## 4. نحوه استفاده

Builder یک instance موجود از `ShipmentRequest` دریافت می‌کند:

```python
from backend.services.shipment_context_service import build_shipment_request_context

context = build_shipment_request_context(shipment_request)
```

Builder:

- query اجرا نمی‌کند؛
- relationshipها را traverse نمی‌کند؛
- object ورودی را تغییر نمی‌دهد؛
- session state ایجاد نمی‌کند؛
- authorization انجام نمی‌دهد.

بنابراین caller آینده موظف است قبل از فراخوانی builder، دسترسی کاربر یا service principal به همان shipment را enforce کند. قرار دادن مستقیم این تابع پشت endpoint عمومی یا اشتراک خروجی با provider خارجی بدون policy و authorization مستقل مجاز نیست.

## 5. envelope نسخه ۱

ترتیب top-level بخشی از قرارداد نسخه ۱ است:

```json
{
  "contract": {},
  "aggregate": {},
  "confirmed": [],
  "missing": [],
  "ambiguous": [],
  "excluded": [],
  "unavailable": [],
  "limitations": []
}
```

### 5.1 `contract`

مقدار ثابت:

```json
{
  "name": "shipment_request_context",
  "version": "1.0",
  "profile": "operational_minimum_v1",
  "mode": "read_only",
  "deterministic": true,
  "classification": "confidential"
}
```

فیلد زمان تولید عمداً وجود ندارد، زیرا افزودن زمان جاری باعث غیرقطعی شدن خروجی یک state ثابت می‌شود.

### 5.2 `aggregate`

```json
{
  "type": "ShipmentRequest",
  "id": 42
}
```

`id` شناسه داخلی aggregate است و بخشی از context محرمانه محسوب می‌شود. `tracking_code` در نسخه ۱ خروجی داده نمی‌شود.

## 6. معنا و ساختار دسته‌ها

### 6.1 `confirmed`

فیلدی که در allow-list نسخه ۱ قرار دارد، برای نوع shipment قابل اعمال است و مقدار معتبر غیرخالی دارد:

```json
{
  "field": "route.origin.country",
  "source": "ShipmentRequest.origin_country",
  "classification": "operational_confidential",
  "content_trust": "trusted_structured",
  "value": "Iran"
}
```

### 6.2 `missing`

فیلدی که قابل اعمال است اما مقدار آن `null` یا رشته خالی است:

```json
{
  "field": "dates.delivery",
  "source": "ShipmentRequest.delivery_date",
  "classification": "operational_confidential",
  "content_trust": "trusted_structured",
  "reason": "not_provided"
}
```

فیلدهای مربوط به نوع دیگر حمل، missing محسوب نمی‌شوند؛ آن‌ها با دلیل `not_applicable_for_*_shipment` در `excluded` قرار می‌گیرند.

### 6.3 `ambiguous`

وجود داده‌های cross-mode که با `shipping_type` تعارض دارند، بدون انتخاب یا inference ثبت می‌شود:

```json
{
  "field": "route.international",
  "reason": "values_conflict_with_domestic_shipping_type",
  "candidates": [
    {
      "value": "Iran",
      "source": "ShipmentRequest.origin_country"
    }
  ]
}
```

اگر `shipping_type` یکی از `domestic` یا `international` نباشد، مقدار موجود با دلیل `unsupported_shipping_type` در `ambiguous` ثبت می‌شود. Builder نوع حمل را حدس نمی‌زند.

### 6.4 `excluded`

فیلدهایی که عمداً به دلیل privacy، sensitivity، legacy status، relationship boundary یا عدم applicability وارد context نمی‌شوند:

```json
{
  "field": "contact_phone",
  "reason": "direct_contact_data"
}
```

مقدار واقعی فیلد excluded هرگز در خروجی قرار نمی‌گیرد.

### 6.5 `unavailable`

قابلیتی که repository فعلی داده لازم آن را نگهداری نمی‌کند:

```json
{
  "field": "attachments",
  "availability": "not_supported",
  "reason": "not_supported_on_shipment_request"
}
```

این دسته با «بررسی شد و موردی وجود نداشت» تفاوت دارد. برای مثال `attachments` در نسخه ۱ لیست خالی نیست؛ صریحاً `not_supported` است.

## 7. منبع حقیقت و allow-list

### 7.1 وضعیت canonical

| Context field | Source | Policy |
|---|---|---|
| `shipment.status` | `ShipmentRequest.status` | تنها lifecycle status canonical |
| `status_request_status` | legacy column | همیشه excluded |

هیچ reconciliation یا fallback بین این دو ستون انجام نمی‌شود.

### 7.2 فیلدهای مشترک

| Context field | Source | Classification | Trust |
|---|---|---|---|
| `shipment.shipping_type` | `shipping_type` | `operational` | `trusted_structured` |
| `transport.preference` | `transport_method_preference` | `operational_confidential` | `trusted_structured` |
| `cargo.description` | `cargo_description` | `operational_confidential` | `untrusted_user_text` |
| `cargo.weight` | `cargo_weight` | `operational_confidential` | `trusted_structured` |
| `cargo.volume` | `cargo_volume` | `operational_confidential` | `trusted_structured` |
| `dates.created_at` | `created_at` | `operational_confidential` | `trusted_structured` |
| `dates.ready_at` | `ready_at` | `operational_confidential` | `trusted_structured` |
| `dates.pickup` | `pickup_date` | `operational_confidential` | `trusted_structured` |
| `dates.delivery` | `delivery_date` | `operational_confidential` | `trusted_structured` |
| `operations.priority` | `priority` | `operational_confidential` | `trusted_structured` |
| `operations.sla_due_at` | `sla_due_at` | `operational_confidential` | `trusted_structured` |
| `operations.last_customer_touch_at` | `last_customer_touch_at` | `operational_confidential` | `trusted_structured` |
| `operations.has_unread_for_assignee` | `has_unread_for_assignee` | `operational_confidential` | `trusted_structured` |

`cargo.description` داده کاربر است. وجود آن در context به معنای trusted instruction بودن آن نیست.

### 7.3 فیلدهای domestic

این فیلدها فقط هنگامی applicable هستند که `shipping_type == "domestic"` باشد:

| Context field | Source |
|---|---|
| `route.origin.province_id` | `origin_province_id` |
| `route.origin.county_id` | `origin_county_id` |
| `route.origin.city_id` | `origin_city_id` |
| `route.destination.province_id` | `dest_province_id` |
| `route.destination.county_id` | `dest_county_id` |
| `route.destination.city_id` | `dest_city_id` |
| `transport.domestic_method` | `domestic_transport_method` |

نسخه ۱ relationship lookup انجام نمی‌دهد؛ بنابراین نام province/county/city را از database استخراج نمی‌کند و فقط ID ساخت‌یافته موجود روی aggregate را برمی‌گرداند.

### 7.4 فیلدهای international

این فیلدها فقط هنگامی applicable هستند که `shipping_type == "international"` باشد:

| Context field | Source |
|---|---|
| `route.origin.country` | `origin_country` |
| `route.origin.city` | `origin_city_international` |
| `route.destination.country` | `dest_country` |
| `route.destination.city` | `dest_city_international` |
| `route.iran_entry_port` | `iran_entry_port` |
| `route.iran_entry_port_id` | `iran_entry_port_id` |
| `route.iran_entry_province` | `iran_entry_province` |
| `route.iran_entry_province_id` | `iran_entry_province_id` |
| `transport.international_method` | `international_transport_method` |

متن و ID نقطه ورود ایران هر دو source fact مستقل هستند؛ builder آن‌ها را resolve یا reconcile نمی‌کند.

## 8. فیلدهای excluded ثابت

| Source field/category | Reason |
|---|---|
| `status_request_status` | legacy status؛ `ShipmentRequest.status` canonical است |
| `tracking_code` | public identifier برای context لازم نیست |
| `transport_method` | legacy label در نسخه ۱ reconcile نمی‌شود |
| `contact_phone` | direct contact data |
| `customer_first_name`, `customer_last_name` | personal data |
| آدرس دقیق بین‌المللی | precise address |
| `cargo_value`, `estimated_value` | commercially sensitive |
| `special_instructions` | unbounded sensitive free text |
| `request_user_id`, `assigned_to` | internal identity |
| `customer_id`, `gamification_customer_id` | internal relationship |
| logs و expert logs | free text، actor و network metadata |
| messages و notifications | raw content خارج از محدوده |
| assigned expert و customer relationships | identity، personal یا commercial data |

فیلد جدید ORM به‌صورت خودکار وارد قرارداد نمی‌شود. اضافه‌کردن source field جدید نیازمند تصمیم صریح allow-list، privacy review و تست قرارداد است.

## 9. داده‌های unavailable

نسخه ۱ موارد زیر را infer نمی‌کند:

| Context capability | Reason |
|---|---|
| `attachments` | attachment metadata روی `ShipmentRequest` وجود ندارد |
| `correspondence_provenance` | email/source provenance پیاده‌سازی نشده است |
| `cargo.weight_unit` | واحد ذخیره نشده است |
| `cargo.volume_unit` | واحد ذخیره نشده است |
| `shipment.source_revision` | aggregate revision ذخیره نشده است |
| `shipment.incoterm` | ذخیره نشده است |
| `shipment.partner_forwarder` | مدل نشده است |

مصرف‌کننده نباید برای وزن یا حجم واحدی مانند kg یا m³ فرض کند.

## 10. قواعد determinism و serialization

- ترتیب top-level و ترتیب field specها ثابت است.
- یک state یکسان از object، خروجی برابر تولید می‌کند.
- date و datetime با `isoformat()` serialize می‌شوند.
- مقدار غیرمتناهی float مانند `NaN` یا `Infinity` به خروجی JSON غیرمجاز راه پیدا نمی‌کند و به‌عنوان مقدار قابل استفاده موجود نیست.
- serialization با `json.dumps(..., allow_nan=False)` پشتیبانی می‌شود.
- current time، random value، network state یا database lookup وارد خروجی نمی‌شود.
- builder inference یا normalization دامنه‌ای خارج از lowercase/trim موردنیاز برای تشخیص `shipping_type` انجام نمی‌دهد.

## 11. محدودیت‌های امنیت و حریم خصوصی

- خروجی کامل همچنان `confidential` است.
- builder جایگزین authorization نیست.
- `aggregate.id` یک شناسه داخلی است و نباید عمومی شود.
- `cargo.description` باید همیشه به‌عنوان `untrusted_user_text` پردازش شود.
- context شامل PII مشتری، tracking code، raw message، internal note، IP address، actor identity یا attachment content نیست.
- این نسخه برای ارسال به provider خارجی مجوز ایجاد نمی‌کند.
- logging خروجی کامل یا ذخیره آن خارج از policy مصوب مجاز نیست.

## 12. تضمین‌های read-only

پیاده‌سازی نسخه ۱:

- `db.session` را import یا استفاده نمی‌کند؛
- query اجرا نمی‌کند؛
- relationship را access نمی‌کند؛
- `add`، `delete`، `flush` یا `commit` ندارد؛
- object ورودی را mutate یا attach نمی‌کند؛
- file یا network I/O ندارد.

## 13. پوشش تست

تست synthetic نسخه ۱ موارد زیر را کنترل می‌کند:

- envelope و version دقیق؛
- برابری deterministic خروجی؛
- strict JSON serialization؛
- canonical بودن `ShipmentRequest.status`؛
- حذف legacy status؛
- applicability داخلی و بین‌المللی؛
- inclusion صریح Iran entry text/ID؛
- تشخیص cross-mode ambiguity؛
- تفکیک confirmed، missing، excluded و unavailable؛
- label شدن free text به‌عنوان untrusted؛
- عدم نشت privacy canaryها؛
- عدم وجود attachment/correspondence content؛
- رفتار امن برای float غیرمتناهی؛
- عدم mutation و عدم attach شدن transient aggregate.

## 14. سیاست نسخه‌بندی

تغییرات زیر breaking محسوب می‌شوند و نیازمند نسخه جدید هستند:

- حذف یا تغییر نام field؛
- تغییر معنای confirmed/missing/ambiguous/excluded/unavailable؛
- تغییر source-of-truth؛
- تغییر ترتیب تضمین‌شده؛
- تغییر privacy classification یا redaction profile؛
- اضافه‌کردن relationship traversal، query یا inference؛
- وارد کردن PII، commercial value، correspondence یا attachment data؛
- تغییر canonical status policy.

افزودن field جدید نیز باید با review صریح انجام شود. حتی اگر از نظر JSON additive باشد، consumerهای deterministic ممکن است exact-key contract داشته باشند؛ بنابراین تغییر allow-list باید با تصمیم نسخه‌بندی و تست regression همراه باشد.

## 15. دروازه فاز بعد

پیش از اتصال این context به هر consumer جدید باید موارد زیر تعیین شوند:

1. caller و authorization boundary؛
2. purpose و audience؛
3. retention و logging policy؛
4. profile مورد استفاده؛
5. رفتار consumer در برابر missing و ambiguous؛
6. ممنوعیت write مستقیم و الزام human review برای هر پیشنهاد آینده؛
7. version pinning و regression test.

AI-READY-1 فقط قرارداد read-only را فراهم می‌کند و هیچ مجوزی برای پردازش ایمیل واقعی، اتصال provider یا ایجاد workflow خودکار نمی‌دهد.
