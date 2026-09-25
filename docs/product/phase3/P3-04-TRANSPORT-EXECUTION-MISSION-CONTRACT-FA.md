# قرارداد مأموریت P3-04 — اجرای حمل مرحله‌ای

وضعیت: `AUTHORIZED_FOR_BOUNDED_IMPLEMENTATION`
مبنای حاکمیتی: `LPAF v2.7`
سطح سخت‌گیری: `Level B`
مسیر قابلیت: `Astra`
مبنای کد: `integration/golden-controlled@c69c0d3096c29d902a7fad2009d0b8ec2d4bdf68`
شاخهٔ نامزد: `codex/phase3-p3-04-transport-execution`

## نتیجه، دامنه و توقف

نتیجهٔ مجاز آن است که Expert مسئول روی هر مرحلهٔ فعال مسیر، صفر تا چند اجرای حمل واقعی بسازد و برای هر اجرا شرکت حمل، نوع وسیله، صفر تا چند واحد/ظرف حمل، شناسه‌ها و جزئیات عملیاتی سبک را به‌تدریج ثبت کند. تغییر معنادار شرکت، وسیله، تجهیز یا شناسه باید revision تازه بسازد و رخدادهای قبلی را در context revision قبلی نگه دارد.

دامنه فقط `P3-04` است. تخصیص، split، transfer، مانده و lifecycle مقدار Cargo متعلق به `P3-05` است و تغییر نمی‌کند. fleet registry، Driver/Carrier Portal، lifecycle/status تازه، ETA، GPS، finance/customs، Customer projection، Production، deployment و release ممنوع‌اند. پس از qualification و integration، کار پیش از `P3-05` متوقف می‌شود.

شرایط توقف:

- نیاز به ownership جدید برای Shipment یا تبدیل Carrier به مالک؛
- نیاز به یک Route یا Execution SOR دوم؛
- نیاز به containment معنایی تازه برای equipment فراتر از زنجیرهٔ مرتب مصوب؛
- نیاز به lifecycle/status/Exception/SLA تازه؛
- نیاز به اجرای allocation یا انتقال Cargo.

## Product Authority Record

| فیلد | مقدار |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | چند execution برای یک Route Leg؛ Carrier مستقل هر execution؛ Means و Equipment مجزا با نوع مرجع مصوب سازمان؛ جزئیات ناقص و تکمیل تدریجی؛ history معنادار تغییر؛ اتصال رخداد تازه به revision مؤثر؛ نمایش فارسی زنجیرهٔ شرکت حمل ← وسیله حمل ← واحد/ظرف حمل. |
| `DELEGATED_TECHNICAL_CHOICES` | association افزایشی stage/execution، revision snapshot و equipment snapshot مرتب، کلید/index/FK، optimistic version/idempotency، DTO/API/UI، migration/rollback و آزمون تا وقتی معنای Product تغییر نکند. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | ADR-046 tenant-owned ExecutionUnit و shared execution؛ legacy project/shipment compatibility؛ P3-01 reference authority؛ P3-02 Cargo/quantity؛ P3-03 Route SOR/history؛ allocationهای موجود بدون گسترش؛ fixed Shipment owner؛ tracking/event history؛ Customer/Public/Admin authority و همه lifecycleها. |
| `DECISIONS_NEEDED` | `DN08=OPEN` و تعریف/promotion مرجع تازه ساخته نمی‌شود. containment مالکیتی equipment تعریف نمی‌شود؛ ترتیب equipment فقط زنجیرهٔ ارائه و snapshot همان execution است. تصمیم Product تازه‌ای برای اجرای bounded حاضر لازم نیست. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner با دستور صریح `START PHASE 3 IMPLEMENTATION — P3-04 ONLY`؛ LPAF v2.7 برای حاکمیت. |
| `APPROVAL_REFERENCE` | درخواست جاری؛ Product Contract v1 §12–§13؛ Journey Pack v1.1؛ UX V2.1؛ رکورد P3-04 در Implementation Plan v1. |

## FACT / ASSUMPTION / UNKNOWN / DECISION NEEDED

### FACT

- canonical و remote روی SHA مبنا برابر و worktree تمیز بودند؛ P3-01، P3-02 و P3-03 ancestor هستند.
- Alembic دقیقاً یک head با شناسهٔ `20261002_phase3_branched_route` دارد.
- `ExecutionUnit` tenant-owned و SOR اجراست؛ `project_id` و `operational_shipment_id` compatibility-only هستند.
- `carrier_customer_id` و نقش فعال `CARRIER` موجودند؛ `vehicle_reference` معنای legacy یکنواخت و قابل backfill به Means یا Equipment ندارد.
- P3-01 نوع‌های `TransportMeansType` و `TransportEquipmentType` و activation سازمانی آن‌ها را ایجاد کرده است.
- P3-03 `RoutePlan/RouteLeg` را با revision و branch حفظ می‌کند.
- `OperationalEvent` append-only است، ولی اکنون revision وسیله/تجهیز را ثبت نمی‌کند.

### ASSUMPTION قابل آزمون

- association صریح RouteLeg↔ExecutionUnit کمینهٔ سازگار با ADR-046 است و ownership tenant را به Shipment برنمی‌گرداند.
- snapshot immutable از کل وضعیت transport در هر تغییر، همراه equipmentهای مرتب، history کافی بدون event sourcing کامل می‌دهد.
- `OperationalEvent.transport_revision_id` برای رخدادهای تازه مانع جابه‌جایی معنایی رخدادهای Truck A به Truck B می‌شود؛ NULL تاریخی صریحاً context نامعلوم legacy است.
- Means type برای ایجاد execution لازم است؛ Carrier، شناسه وسیله، equipment و driver context می‌توانند nullable باشند و نبودشان Exception نمی‌سازد.

### UNKNOWN

- معنای legacy `vehicle_reference` برای همه ردیف‌های قدیمی قابل اثبات نیست و backfill نمی‌شود.
- integrated journey و Human Product Walkthrough این slice هنوز اجرا نشده‌اند.

### DECISION NEEDED

تصمیم تازه‌ای برای طراحی bounded حاضر لازم نیست. hierarchy/ownership پیچیدهٔ equipment، تعریف مرجع سازمانی تازه، Portal یا lifecycle جدید باید متوقف و جداگانه به Product Owner ارجاع شود.

## طبقه‌بندی foundationهای موجود

| foundation | نتیجه | کاربرد P3-04 |
| --- | --- | --- |
| `ExecutionUnit` | `EXTEND` | همان SOR اجرا؛ association مرحله و revision transport افزوده می‌شود. |
| `carrier_customer_id` | `REUSE / ADAPT` | current compatibility projection؛ Carrier تاریخی در revision snapshot می‌ماند. |
| `vehicle_reference` | `ADAPT` | برای executionهای تازه projection شناسه means است؛ legacy reinterpret/backfill نمی‌شود. |
| `CustomerRoleAssignment/CARRIER` | `REUSE` | فقط Customer فعال همان tenant با نقش فعال selectable است. |
| `shared_transport_service` | `REUSE / ADAPT` | قواعد tenant/Carrier reuse می‌شود؛ allocation API و semantics دست‌نخورده است. |
| `execution_unit_service` و `routes/execution_units.py` | `ADAPT` | projection/history context تکمیل می‌شود؛ project routes سازگاری باقی می‌مانند. |
| operational execution routes و `OperationalExecutionSection` | `NOT_APPLICABLE / REGRESSION` | آن‌ها milestone execution هستند؛ P3-04 در همان Shipment workspace و روی ExecutionUnit نمایش مجاور می‌گیرد. |
| P3-01 Means/Equipment reference | `REUSE` | فقط central-valid ∩ organization-active برای write؛ inactive historical readable. |
| P3-03 `RoutePlan/RouteLeg` | `REUSE` | assignment به revision/leg دقیق؛ route تغییر نمی‌کند. |
| `OperationalEvent` | `EXTEND` | رخداد تازه revision مؤثر را pin می‌کند؛ رخداد قدیمی جابه‌جا نمی‌شود. |
| ADR-046 و tenant inventory | `EXTEND` | ownership tenant حفظ و associationهای indirect ثبت می‌شوند. |
| legacy project/shipment/tracking adapters | `ADAPT` | readهای قدیمی و ردیف‌های بدون revision حفظ؛ SOR جدیدی ساخته نمی‌شود. |

## مالکیت، SOR و زنجیره

`ExecutionUnit` تنها SOR اجرای فیزیکی باقی می‌ماند. `RouteStageExecution` participation آن execution در `OperationalShipment + RoutePlan revision + RouteLeg` است؛ ownership ایجاد نمی‌کند. `ExecutionTransportRevision` و equipmentهای child snapshot، تاریخچهٔ immutable همان execution هستند. P3-01 definitions مرجع نوع‌اند و snapshot مصرف‌کننده معنای تاریخی را ثابت نگه می‌دارد.

زنجیرهٔ command:

`owning Expert → authorized Shipment → active RoutePlan/RouteLeg → tenant-owned ExecutionUnit → immutable transport revision/equipment snapshots → audit/outbox-compatible history`

Carrier assignment هیچ entitlement یا Shipment ownership ایجاد نمی‌کند. Organization Admin و Platform Admin فرمان عادی mutation ندارند.

## Journey Impact و شواهد لازم

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J04,FWD-J07,FWD-J08,FWD-J09,FWD-IPJ-02,FWD-IPJ-04
REQUIRED_SLICE_RERUN=P3-04-STAGE-EXECUTION,P3-04-MULTIPLE,P3-04-PROGRESSIVE,P3-04-HISTORY,P3-04-REFERENCE-INACTIVE,P3-04-TENANT,P3-04-SHARED-FOUNDATION,P3-04-RAIL
REQUIRED_INTEGRATED_RERUN=FWD-IPJ-02,FWD-IPJ-04-BOUNDARY
HUMAN_WALKTHROUGH_RERUN=YES_BEFORE_RELEASE_READY
```

Qualification شامل backend/frontend متمرکز، PostgreSQL 18، migration upgrade و downgrade/re-upgrade، concurrency، مجوزهای منفی، browser normal-navigation/reopen، TypeScript، ESLint، production build، compile/import، architecture/structure/governance، `git diff --check` و regression کامل است. evidence به Product SHA دقیق bind می‌شود. integrated journeys globally PASS و Human Walkthrough ادعا نمی‌شوند.

## وضعیت completion

`Engineering Complete`، `Product Complete`، `Release Ready` و `Release Complete` جدا هستند. در این مأموریت `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`، `HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN` و `RELEASE_READY=NO` باقی می‌مانند.
