# تحلیل شکاف عملیاتی سامانه Forwarder

> اصطلاح رسمی مدل هدف: `OperationalShipment`. اصطلاح `ShipmentJob` فقط alias منسوخ است.
> مبنا و محدودیت ممیزی در [موجودی معماری فعلی](forwarder_current_architecture_inventory.md) آمده است.

## 1. خلاصه مدیریتی

سامانه از نظر intake، ارجاع و quote بالغ‌تر از execution است. بزرگ‌ترین ریسک توسعه، افزودن leg، سند، هزینه و عملیات به `ShipmentRequest` است. این مدل در `backend/models.py:319-431` هم‌اکنون چند مسئولیت دارد و status آن چرخه تجاری را نمایش می‌دهد. تحول باید aggregate مستقل `OperationalShipment` و چرخه وضعیت عملیاتی جدا ایجاد کند.

## 2. طبقه‌بندی شکاف‌ها

- **Domain:** مفاهیم و invariantهای غایب یا مبهم؛
- **Process:** workflow، transition، handoff و ownership؛
- **Data:** lineage، quality، provenance و persistence؛
- **API/UI:** command/query و workspace؛
- **Reporting:** KPI، projection و analytics؛
- **Security/Internal Control:** permission، audit و کنترل تفکیک وظایف.

## 3. بیست شکاف اصلی

مقیاس شدت/احتمال/اثر: کم، متوسط، بالا، بحرانی.

| ID | دسته | شکاف | شاهد موجود | شدت | احتمال | اثر | اولویت |
|---|---|---|---|---|---|---|---|
| G01 | Process | تبدیل idempotent quote پذیرفته‌شده به عملیات | `ExpertQuote` در `models.py:734`؛ job مستقل نیست | بحرانی | بالا | lineage/duplicate | P0 |
| G02 | Domain | پرونده مستقل `OperationalShipment` | فقط `ShipmentRequest` در خط 319 | بحرانی | بالا | God aggregate | P0 |
| G03 | Domain | `TransportProject` و portfolio/work package | مدل مشاهده نشد | بالا | متوسط | پروژه‌های پیچیده | P1 |
| G04 | Domain | route plan و leg چندمرحله‌ای | route کلی روی request | بحرانی | بالا | اجرای multimodal | P0 |
| G05 | Process/Data | milestone planned/actual | timeline مشتق از status در `timeline_service.py:19` | بحرانی | بالا | کنترل تأخیر | P0 |
| G06 | Domain/Security | Party/Organization/Role | CRM Customer و ExpertUser | بالا | بالا | طرف‌ها و scope | P0 |
| G07 | Process | booking/service order | مدل مشاهده نشد | بالا | بالا | تعهد provider | P1 |
| G08 | Domain/Data | cargo/equipment/load allocation جامع | unit ساده در `models.py:471` | بالا | بالا | چند سفارش/واحد | P1 |
| G09 | Data/Security | document/version/requirement/storage | مدل مشاهده نشد | بحرانی | بالا | اجرا و compliance | P1 |
| G10 | Process | customs/compliance workflow | reference گمرک در `models.py:1171` | بالا | بالا | توقف/ریسک قانونی | P1 |
| G11 | Process | exception case و resolution | delayed status؛ case مستقل نیست | بحرانی | بالا | کنترل رخداد | P0 |
| G12 | Internal Control | SLA/alert/escalation عملیاتی | SLA درخواست محدود | بالا | بالا | breach و accountability | P0 |
| G13 | Reporting/Data | ETA و confidence | مشاهده نشد | متوسط | متوسط | پیش‌بینی | P2 |
| G14 | Process | communication چندکاناله با receipt | message/notification داخلی | متوسط | بالا | handoff ناقص | P1 |
| G15 | Domain/Data | cost/revenue/accrual/invoice | quote/estimated value | بحرانی | بالا | سودآوری واقعی | P1 |
| G16 | Reporting | margin shipment/project و at-risk | گزارش request-centric | بالا | بالا | تصمیم مالی | P1 |
| G17 | UI/Reporting | control tower work queue | admin/expert dashboard | بحرانی | بالا | اقدام‌پذیری | P1 |
| G18 | API/Data | adapter/webhook/outbox/inbox | abstraction محدود AI | بالا | بالا | integration reliability | P1 |
| G19 | Data/Internal Control | governance/lineage/retention/quality | reference backfill نقطه قوت محدود | بالا | بالا | اعتماد به داده | P1 |
| G20 | UI/Process | field/mobile/offline/POD | مشاهده نشد | متوسط | متوسط | عملیات میدانی | P3 |

## 4. تحلیل Overloading مدل ShipmentRequest

`ShipmentRequest` اکنون intake، contact، cargo/route، commercial status، assignment، tracking code و روابط quote/log/tracking را در خود جمع کرده است (`backend/models.py:319-431`). ادامه توسعه روی آن مشکلات زیر را می‌سازد:

1. lifecycle تجاری با execution مخلوط می‌شود؛
2. یک request نمی‌تواند به‌روشنی چند shipment یا project را تغذیه کند؛
3. status واحد برای milestone/leg/exception کافی نیست؛
4. permission فروش و عملیات روی یک resource قفل می‌شود؛
5. migration و rollback پرریسک می‌شود؛
6. گزارش conversion و execution معنای متناقض پیدا می‌کند؛
7. public tracking ممکن است داده داخلی را ناخواسته آشکار کند.

**تصمیم:** `ShipmentRequest.status` صرفاً وضعیت چرخه تجاری است. هیچ status عملیاتی به آن افزوده یا از روی آن به‌عنوان حقیقت اجرا استنتاج نمی‌شود.

## 5. شکاف‌های Domain و Process

هسته غایب، زنجیره `OperationalShipment → RouteLeg → Milestone` است. TransportProject ظرف چند shipment، CustomerOrder تقاضای تجاری قابل fulfillment، TransportUnit منبع/واحد فیزیکی و LoadAllocation رابطه تخصیص order/cargo به unit/leg است. نبود این تفکیک سناریوی چند سفارش و چند واحد را مبهم می‌کند.

workflow فعلی از request به quote و پاسخ مشتری می‌رسد، اما accepted quote فقط status تجاری را تغییر می‌دهد. conversion، booking، plan baseline، handoff، actual event، exception ownership و completion gate تعریف نشده‌اند.

## 6. شکاف‌های Data و API

- statusها string و مجموعه‌های مصرفی پراکنده‌اند (`admin_report_overview_service.py:47-49`)؛
- event source، external id، dedupe key، received time و confidence نیست؛
- outbox/inbox و worker وجود ندارد؛
- commandهای معنایی، idempotency key و optimistic locking عمومی نیست؛
- OpenAPI موجود است اما coverage/compatibility gate کامل **نیازمند تأیید**؛
- document blob store، retention و checksum غایب است؛
- money/currency/FX snapshot تعریف نشده است.

## 7. شکاف‌های UI و Reporting

افزودن tab به Expert/Admin جای cockpit عملیاتی را نمی‌گیرد. UI هدف به work queue، timeline leg/milestone، exception ownership، freshness، document blocker و drill-down project→shipment→leg نیاز دارد. KPIهای فعلی count/status درخواست‌اند؛ on-time milestone، dwell، MTTA/MTTR، ETA accuracy، exception aging، cost variance و margin at risk غایب‌اند.

## 8. شکاف‌های Security و Internal Control

- نقش‌های عملیاتی و scope سازمانی صریح نیست؛
- تفکیک وظایف pricing/operation/finance/compliance تعریف نشده؛
- audit logها correlation/causation/idempotency مشترک ندارند؛
- export/document/cost permission جدا نشده؛
- service account و credential partner از user identity تفکیک نشده؛
- transition guard و approval threshold وجود ندارد؛
- tracking عمومی نیازمند threat model IDOR/enumeration و allowlist مداوم است.

## 9. بدهی فنی

| بدهی | شاهد/پیامد | اقدام پیشنهادی |
|---|---|---|
| فایل مدل مشترک بزرگ | `backend/models.py` چند دامنه | module ownership و architecture test |
| status semantics پراکنده | report/timeline/serviceها | glossary + state machine |
| legacy status دوگانه | `status_request_status` در ShipmentRequest | deprecation و عدم استفاده جدید |
| synchronous architecture | نبود worker/outbox | فاز platform foundation |
| مستندات mojibake/stale | برخی README/docs | UTF-8 و canonical marker |
| API client/page coupling | SPA مشترک چند نقش | feature module/workspace |
| topology تک‌نمونه | Compose فعلی | SLO/DR/HA پس از نیازسنجی |
| artifactهای legacy repository | DB/zip/outputها | policy و cleanup جدا؛ **نیازمند تأیید** |

## 10. Risk Register

| R | ریسک | احتمال | اثر | کنترل | فاز مالک |
|---|---|---|---|---|---|
| R01 | God aggregate | بالا | بحرانی | OperationalShipment مستقل | Phase 0-1 |
| R02 | اختلاط statusها | بالا | بحرانی | state machine جدا | Phase 0 |
| R03 | backfill اشتباه | بالا | بالا | dry-run/quarantine/reconciliation | Phase 1 |
| R04 | duplicate/out-of-order event | بالا | بالا | inbox/dedupe/event time | Phase 1-2 |
| R05 | dashboard غیرقابل اقدام | متوسط | بالا | owner/due/command/work queue | Phase 2 |
| R06 | افشای document/cost | متوسط | بحرانی | scoped permission/encryption/audit | Phase 3-4 |
| R07 | lock/downtime migration | متوسط | بالا | expand-migrate-contract | همه فازها |
| R08 | AI mutation خودکار | متوسط | بالا | proposal-only/human approval | Phase 6 |
| R09 | microservice زودهنگام | متوسط | متوسط | modular monolith و extraction criteria | Phase 0-6 |
| R10 | KPI نادرست | بالا | بالا | metric contract/lineage | Phase 2 |
| R11 | startup side effect | متوسط | بالا | migration/seed خارج از app startup | Phase 0-1 |
| R12 | FK تکراری/مبهم | متوسط | بالا | naming convention/schema inspection | Phase 1 |
| R13 | regression request/quote | متوسط | بحرانی | compatibility/regression suite | Phase 1-2 |
| R14 | partner outage | بالا | بالا | retry/circuit breaker/DLQ/manual fallback | Phase 4 |

## 11. موارد نیازمند تأیید

1. تعریف سازمانی shipment/job/project/booking؛
2. mode و lane اولویت‌دار و ضرورت multimodal؛
3. cardinality واقعی request→quote→shipment؛
4. carrier/agent/broker و روش integration؛
5. milestone catalog و SLA هر service level؛
6. اسناد و الزامات قانونی هر lane/commodity؛
7. tenancy و organization scope؛
8. volume، retention، RPO/RTO و ساعات control tower؛
9. currency/FX/accounting boundary؛
10. permission production و سازوکار backup/restore؛
11. coverage واقعی OpenAPI و audit logs؛
12. نیاز mobile/offline و POD.

## 12. اولویت نتیجه

P0 بر semantic foundation و اجرای ممیزی‌پذیر متمرکز است؛ P1 control tower/document/finance/integration را می‌سازد؛ P2/P3 تنها پس از داده سالم به ETA، optimization و mobile می‌رسد. این ترتیب با [مدل هدف](forwarder_target_domain_model.md)، [MVP](forwarder_mvp_scope.md)، [راهبرد مهاجرت](forwarder_migration_strategy.md) و [برنامه فازها](forwarder_phase_plan.md) یکسان است.
