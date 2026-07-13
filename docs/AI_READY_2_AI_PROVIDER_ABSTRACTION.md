# AI-READY-2 — AI Provider Abstraction Contract

## 1. وضعیت و محدوده

- نسخه interface: `1.0`
- mode پیش‌فرض: `disabled`
- تنها mode اجرایی: `deterministic_mock`
- پیاده‌سازی: `backend/services/ai_provider_service.py`
- تست: `backend/tests/test_ai_provider_service.py`

این abstraction به هیچ AI provider یا مدل واقعی متصل نیست. نام AI در این قرارداد فقط یک boundary نرم‌افزاری vendor-neutral برای prototypeهای امن آینده است.

موارد زیر در AI-READY-2 وجود ندارند:

- OpenAI، Anthropic، Gemini یا Azure OpenAI؛
- local model runtime؛
- SDK، API key، endpoint یا external HTTP call؛
- environment/config-based provider selection؛
- email، attachment، vector، embedding یا queue؛
- route، frontend، database model، migration یا persistence؛
- autonomous agent یا business workflow.

## 2. اصول قرارداد

1. نبود mode به‌معنای `disabled` است.
2. mock فقط با literal دقیق `deterministic_mock` فعال می‌شود.
3. mode ناشناخته هرگز fallback ندارد.
4. disabled mode هیچ contextای را inspect، copy، fingerprint یا process نمی‌کند.
5. mock فقط خروجی synthetic و advisory تولید می‌کند.
6. هیچ outputی مجوز write، send یا اثر دامنه ندارد.
7. request و response نسبت به mutation caller پایدار هستند.
8. ورودی باید strict JSON، محدود و قطعی باشد.
9. interface به vendor، model یا business domain خاص وابسته نیست.

## 3. ساخت provider

```python
from backend.services.ai_provider_service import build_ai_provider

provider = build_ai_provider()  # disabled
mock_provider = build_ai_provider("deterministic_mock")
```

فقط مقادیر زیر پذیرفته می‌شوند:

| Mode | رفتار |
|---|---|
| `disabled` | هر generation را با خطای typed رد می‌کند |
| `deterministic_mock` | پاسخ synthetic، ثابت و بدون I/O می‌سازد |

مواردی مانند `None`، رشته خالی، whitespace، تفاوت حروف، `auto`، نام vendor یا URL با `AIProviderUnsupportedModeError` رد می‌شوند. متن mode ورودی در error echo نمی‌شود.

## 4. interface

Providerها protocol زیر را پیاده می‌کنند:

```python
class AIProvider(Protocol):
    mode: str

    def generate(self, request: AIProviderRequest) -> AIProviderResponse:
        ...
```

Business service آینده باید فقط به این protocol وابسته باشد، نه به نام vendor، SDK یا model.

## 5. request contract

```python
request = AIProviderRequest(
    operation="shipment_summary",
    context=shipment_context,
    output_schema_version="1.0",
)
```

فیلدهای immutable request:

| Field | معنا |
|---|---|
| `operation` | identifier کنترل‌شده برای capability |
| `output_schema_version` | نسخه output مورد انتظار caller |
| `interface_version` | نسخه boundary؛ در این فاز `1.0` |
| `_canonical_context` | snapshot خصوصی canonical JSON |

### 5.1 snapshot و immutability

در زمان ساخت request:

- context به strict JSON canonical تبدیل می‌شود؛
- snapshot مستقل از dict اولیه ذخیره می‌شود؛
- mutation بعدی dict caller fingerprint یا رفتار request را تغییر نمی‌دهد؛
- property عمومی `request.context` در هر بار فراخوانی یک copy تازه برمی‌گرداند؛
- consumer به object داخلی mutable دسترسی ندارد.

### 5.2 identifierها

`operation` باید با الگوی کنترل‌شده lowercase identifier سازگار باشد و حداکثر ۶۴ کاراکتر داشته باشد. `output_schema_version` نیز identifier نسخه محدود است. متن آزاد، prompt یا secret نباید در این فیلدها قرار گیرد.

## 6. strict JSON و limits

context باید یک JSON object واقعی (`dict`) باشد. مقادیر مجاز:

- `null`؛
- string؛
- boolean؛
- integer؛
- finite float؛
- list؛
- dict با key رشته‌ای.

موارد زیر با `AIProviderInvalidRequestError` رد می‌شوند:

- `NaN`، `Infinity` یا `-Infinity`؛
- tuple، set، bytes، datetime یا custom object؛
- key غیررشته‌ای؛
- cyclic data؛
- nesting بیش از `32`؛
- بیش از `10,000` item؛
- canonical request بزرگ‌تر از `1,000,000` بایت UTF-8.

خطاها raw input، context، secret یا mode نامعتبر را echo نمی‌کنند.

## 7. canonical serialization و fingerprint

Canonical request شامل این موارد است:

```json
{
  "context": {},
  "interface_version": "1.0",
  "operation": "shipment_summary",
  "output_schema_version": "1.0"
}
```

قواعد serialization:

- UTF-8؛
- object keyهای مرتب؛
- separator ثابت و compact؛
- `ensure_ascii=False`؛
- `allow_nan=False`.

Fingerprint:

```text
SHA-256(
  "forwarder:ai-provider-request:v1\0" + canonical_request_utf8
)
```

Fingerprint:

- نسبت به ترتیب insertion در objectها مستقل است؛
- نسبت به ترتیب list حساس است، زیرا ترتیب array semantic محسوب می‌شود؛
- با تغییر context، operation، output version یا interface version تغییر می‌کند؛
- integrity signature یا authorization proof نیست؛
- preimage یا context را در response بازنشر نمی‌کند.

## 8. disabled mode

```python
provider = build_ai_provider()
provider.generate(request)
```

نتیجه همیشه `AIProviderDisabledError` است.

Disabled mode قبل از رد درخواست:

- validation انجام نمی‌دهد؛
- context را inspect نمی‌کند؛
- fingerprint نمی‌سازد؛
- environment یا config نمی‌خواند؛
- I/O یا callback اجرا نمی‌کند؛
- response موفق خالی تولید نمی‌کند.

این رفتار مانع می‌شود disabled به‌اشتباه به‌عنوان analysis موفق تفسیر شود.

## 9. deterministic mock mode

```python
provider = build_ai_provider("deterministic_mock")
response = provider.generate(request)
```

Mock:

- inference انجام نمی‌دهد؛
- context را echo نمی‌کند؛
- findings یا proposals واقعی تولید نمی‌کند؛
- time، randomness، database، network، file یا environment state مصرف نمی‌کند؛
- برای request یکسان response برابر تولید می‌کند.

## 10. response contract

`AIProviderResponse` یک dataclass frozen است:

| Field | مقدار mock |
|---|---|
| `provider` | `deterministic_mock` |
| `mode` | `deterministic_mock` |
| `interface_version` | `1.0` |
| `request_fingerprint` | domain-separated SHA-256 |
| `output_schema_version` | نسخه درخواست‌شده |
| `output` | `AIProviderOutput` immutable |

Mock output:

```json
{
  "kind": "synthetic_mock_proposal",
  "operation": "shipment_summary",
  "findings": [],
  "proposals": [],
  "authority": "advisory_only",
  "write_allowed": false,
  "send_allowed": false,
  "requires_human_review": true,
  "business_effects_applied": false,
  "deterministic": true
}
```

در Python، `findings` و `proposals` tuple هستند و output frozen است. برای JSON serialization می‌توان از `dataclasses.asdict(response)` استفاده کرد.

## 11. error contract

| Error | کاربرد |
|---|---|
| `AIProviderError` | base error |
| `AIProviderDisabledError` | تلاش برای generation در disabled mode |
| `AIProviderUnsupportedModeError` | mode خارج از allow-list |
| `AIProviderInvalidRequestError` | request یا context غیرمعتبر |

هیچ errorی نباید context body، canary secret، URL، API key احتمالی یا mode خام نامعتبر را نمایش دهد.

## 12. مرز اختیار

Response mock فقط برای تست wiring و prototype synthetic است:

- canonical shipment fact نیست؛
- تصمیم تاییدشده نیست؛
- risk assessment واقعی نیست؛
- اجازه database mutation ندارد؛
- اجازه status change ندارد؛
- اجازه send ندارد؛
- هیچ domain serviceای را فراخوانی نمی‌کند.

هر consumer آینده باید `authority == "advisory_only"`، `write_allowed == false`، `send_allowed == false` و `requires_human_review == true` را حفظ کند.

## 13. تضمین‌های عدم I/O

پیاده‌سازی AI-READY-2:

- provider SDK import نمی‌کند؛
- `requests`، `httpx`، socket یا subprocess استفاده نمی‌کند؛
- environment variable یا API key نمی‌خواند؛
- Flask route یا Blueprint ندارد؛
- database/session/model را import یا استفاده نمی‌کند؛
- file system، email، queue یا deployment hook ندارد.

## 14. پوشش تست

تست‌های synthetic موارد زیر را پوشش می‌دهند:

- protocol و dataclass contract؛
- disabled پیش‌فرض و عدم inspection؛
- exact mode allow-list؛
- عدم echo mode نامعتبر؛
- strict nested JSON؛
- cycle/depth/item/byte limits؛
- validation operation/version؛
- domain-separated deterministic fingerprint؛
- object-order stability و list-order sensitivity؛
- immutable request snapshot و copyهای بدون alias؛
- immutable typed output؛
- عدم echo context canary؛
- advisory/no-write/no-send semantics؛
- strict JSON response؛
- عدم DB/network/environment/config access.

## 15. سیاست توسعه آینده

اضافه‌کردن هر mode یا adapter جدید خارج از AI-READY-2 است و نیازمند phase و review مستقل خواهد بود. چنین phaseای حداقل باید شامل موارد زیر باشد:

- threat model و privacy approval؛
- explicit configuration contract؛
- secret management؛
- outbound network/egress policy؛
- provider data retention review؛
- timeout/retry/circuit-breaker semantics؛
- observability و redaction؛
- evaluation corpus و release thresholds؛
- human-review boundary؛
- kill switch و incident response؛
- commit و release gate مستقل.

وجود protocol در این فاز به‌معنای تایید هیچ provider واقعی نیست.
