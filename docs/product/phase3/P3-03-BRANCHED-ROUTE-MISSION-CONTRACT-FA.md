# قرارداد مأموریت P3-03 — مسیر مشترک، شاخه‌های مقصد و مسیر واقعی

وضعیت: `IMPLEMENTATION_IN_PROGRESS`
مبنای حاکمیتی: `LPAF v2.7`
سطح سخت‌گیری: `Level B`
مسیر قابلیت: `Astra`
مبنای کد: `integration/golden-controlled@629e6f5a544b7b2824670960d90eb5209d3c594b`
شاخهٔ نامزد: `codex/phase3-p3-03-route-planning`

## نتیجه، دامنه و توقف

نتیجهٔ مجاز آن است که Expert مسئول بتواند برنامهٔ مسیر را ابتدا ناقص و بدون stage/date/time/stop جعلی ذخیره کند، بخش مشترک و شاخه‌های مقصد را روی همان `RoutePlan/RouteLeg` بسازد، هر Cargo را بدون تکثیر Cargo یا Shipment به شاخهٔ مقصد خود متصل کند، و پیمایش واقعی را جدا از برنامه ثبت و مقایسه کند. replan باید علت و نسخه‌ها را حفظ کند و واقعیت بعدی هرگز برنامهٔ قبلی را پاک نکند.

دامنه فقط `P3-03` است. وسیله، تجهیز، Carrier assignment، تخصیص اجرایی، ETA، taxonomy مکان رخداد P3-07، Customer projection، delivery/closure و انتقال مالک خارج از دامنه‌اند. اختلاف مسیر به‌تنهایی `OperationalException` نمی‌سازد. Production، deployment و release ممنوع‌اند. پس از qualification و integration این بخش، کار باید پیش از `P3-04` متوقف شود.

شرایط توقف:

- نیاز به lifecycle/status/transition تازهٔ Product؛
- نیاز به Route SOR یا workflow engine دوم؛
- نیاز به ساخت location/event semantics متعلق به P3-07؛
- نیاز به Carrier/vehicle/equipment behavior متعلق به P3-04؛
- grant تازهٔ Customer Portal یا تغییر مالک ثابت Shipment.

## Product Authority Record

| فیلد | مقدار |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | پیش‌نویس مسیر ناقص؛ parent branch روی RouteLeg؛ بخش مشترک و مقصدهای واگرا؛ اتصال Cargo به terminal branch؛ plan revision/replan history؛ actual traversal fact جدا؛ نمایش plan در برابر actual و deviation بدون Exception خودکار. |
| `DELEGATED_TECHNICAL_CHOICES` | schema افزایشی، composite FK، index، DTO/command، optimistic version، audit/outbox، graph validation، migration/rollback، ساختار UI و آزمون تا وقتی معنای Product تغییر نکند. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | RoutePlan SOR موجود؛ checkpoint/dependency/milestone و occurrence authority؛ Cargo SOR و lineage P3-02؛ مسئول ثابت Shipment؛ allocation/execution؛ Carrier/vehicle/equipment؛ event location؛ ETA؛ Customer projection؛ lifecycleهای موجود. |
| `DECISIONS_NEEDED` | `DN01=OPEN` و status تازه ساخته نمی‌شود؛ `DN10=OPEN` و Customer projection ساخته نمی‌شود. تصمیم تازه‌ای برای طراحی فنی bounded لازم نیست. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner با دستور صریح اجرای ترتیبی P3-02 سپس P3-03؛ LPAF v2.7 برای حاکمیت. |
| `APPROVAL_REFERENCE` | درخواست جاری؛ Product Contract v1 §10–§11؛ Journey Pack v1.1؛ UX V2.1؛ رکورد P3-03 در Implementation Plan v1. |

## FACT / ASSUMPTION / UNKNOWN / DECISION NEEDED

### FACT

- P3-02 در canonical با SHA `629e6f5a544b7b2824670960d90eb5209d3c594b` ادغام و push شده و P3-03 از همان SHA آغاز شده است.
- Alembic پیش از P3-03 یک head داشت: `20261001_phase3_cargo_lineage`.
- `RoutePlan` revision، active uniqueness، replan reason و history دارد؛ `RouteLeg`، `OperationalCheckpoint`، `RouteDependency` و milestone/occurrence موجود و reusable هستند.
- validation موجود فقط مسیر خطی با زمان‌های اجباری را می‌پذیرفت و Cargo-destination و actual traversal fact مستقل نداشت.

### ASSUMPTION قابل آزمون

- parent self-reference هم‌برنامه‌ای روی `RouteLeg` کمینهٔ ایمن برای topology شاخه‌ای است و `sequence_number` فقط ترتیب نمایش/ویرایش باقی می‌ماند.
- plan ناقص با nullable mode/time در status موجود `draft` ذخیره می‌شود؛ activation همچنان completeness و graph validity را می‌طلبد، پس status تازه لازم نیست.
- `RouteCargoDestination` فقط association نسخهٔ plan است و Cargo/Shipment تازه نمی‌سازد.
- `RouteTraversalFact` evidence append-only زیر RoutePlan است؛ SOR برنامه همچنان RoutePlan/RouteLeg می‌ماند و fact واقعی به revision بعدی تکثیر نمی‌شود.

### UNKNOWN

- Product rule دقیق برای promotion یک deviation به OperationalException مشخص نشده است؛ این slice هیچ promotion خودکاری انجام نمی‌دهد.
- Human Product Walkthrough و integrated journey evidence هنوز اجرا نشده‌اند.

### DECISION NEEDED

- تصمیم تازه‌ای برای اجرای bounded P3-03 لازم نیست. هر lifecycle/status تازه فقط با توقف و ارائهٔ `DN01` ممکن است.

## مالکیت، SOR و زنجیره

`RoutePlan/RouteLeg` تنها SOR برنامهٔ مسیر هستند. `RouteCargoDestination` رابطهٔ Cargo موجود با terminal leg همان revision است. `RouteTraversalFact` سند رخداد واقعی است و plan را overwrite نمی‌کند. `OperationalShipment` tenant و fixed owning Expert را تعیین می‌کند؛ Organization Admin حق ویرایش P3-03 ندارد. readهای مجاز موجود حفظ می‌شوند و Customer endpoint تازه‌ای ایجاد نمی‌شود.

زنجیرهٔ command:

`owning Expert → authorized Shipment → same-plan RoutePlan/RouteLeg graph → optional same-Shipment Cargo destination / append-only traversal fact → audit + outbox`

## Journey Impact و شواهد لازم

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J03,FWD-J04,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-04
REQUIRED_SLICE_RERUN=P3-03-INCOMPLETE,P3-03-BRANCHES,P3-03-CARGO-DESTINATIONS,P3-03-PLAN-ACTUAL,P3-03-REPLAN-HISTORY,P3-03-DEVIATION-NO-EXCEPTION,P3-03-TENANT
REQUIRED_INTEGRATED_RERUN=FWD-IPJ-01,FWD-IPJ-04-BOUNDARY
HUMAN_WALKTHROUGH_RERUN=YES_BEFORE_RELEASE_READY
```

Qualification باید backend/frontend متمرکز، PostgreSQL 18، upgrade و downgrade/re-upgrade، active-plan uniqueness، graph/cycle و tenant/authorization منفی، browser Product journey/reopen، TypeScript، lint، build، architecture/structure/governance، diff check و regression کامل را به SHA دقیق Product bind کند. این مأموریت integrated journeyها را PASS اعلام نمی‌کند.

## وضعیت completion

`Engineering Complete`، `Product Complete` و `Release Ready` جدا گزارش می‌شوند. `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`، `HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN` و `RELEASE_READY=NO` باقی می‌مانند.
