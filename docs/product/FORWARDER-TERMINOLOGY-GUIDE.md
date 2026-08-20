# Forwarder Product Terminology Guide

Status: governed product language

Scope: expert-facing Persian UI
Architecture authority: none; this guide does not rename models, tables, APIs, fields, or events.

## Principles

- Product wording explains what an operational user sees or does. Internal names remain canonical in code and architecture documentation.
- `Project`, `ShipmentRequest`, `OperationalShipment`, and `ExecutionUnit` are distinct concepts and must not be collapsed.
- A generic unit term must remain mode-neutral across road, sea, air, rail, and multimodal work.
- Codes, references, identifiers, and English terms use LTR presentation inside Persian screens.
- Help appears once near first use. It must not promise workflow, aggregation, ownership, or allocation that the product does not support.

## Preferred terms

| Internal concept | Preferred Persian UI term | Preferred English UI term | Short definition / use when | Do not confuse with | Contextual help |
| --- | --- | --- | --- | --- | --- |
| Project | پروژه | Project | Coordination boundary grouping related requests and operational shipments. | A request or one shipment. | پروژه می‌تواند چند درخواست و چند محموله عملیاتی مرتبط را هماهنگ کند. |
| ShipmentRequest | درخواست حمل | Shipment request | Commercial intake, quotation, and decision record. | Operational execution. | رکورد ثبت و بررسی تجاری پیش از اجرای حمل. |
| OperationalShipment | محموله عملیاتی | Operational shipment | End-to-end execution aggregate. Use «محموله» only where the operational context is already explicit. | Request or project. | اجرای حمل از برنامه‌ریزی تا تکمیل عملیات. |
| legacy ShipmentTransportUnit | بخش قابل رهگیری حمل | Trackable transport segment | A truck, container, wagon, or other part whose status/location is updated separately in request tracking. | Canonical ExecutionUnit; a vehicle only. | هر وسیله، کانتینر، واگن یا بخش دیگری از حمل که وضعیت و موقعیت آن جداگانه ثبت می‌شود. |
| ExecutionUnit | بخش اجرایی حمل | Execution unit | Independently managed physical or logical part of an OperationalShipment. | Organizational unit or tracking-only projection. | بخش مستقل حمل، مانند وسیله، کانتینر، واگن یا عملیات هوایی، با وضعیت جداگانه. |
| OperationalEvent | رویداد عملیاتی | Operational event | A recorded fact in execution history. | Current status or editable note. | رویداد ثبت‌شده در تاریخچه عملیات؛ وضعیت فعلی از رویدادها نمایش داده می‌شود. |
| CargoCatalogItem | کالای استاندارد | Catalog cargo item | Reusable organization master data. | Cargo actually recorded in a shipment. | اطلاعات این کالا یک‌بار تعریف و در محموله‌های مختلف استفاده می‌شود. |
| ShipmentCargoItem | قلم محموله | Shipment cargo item | Cargo snapshot and quantity recorded on one shipment. | Reusable catalog item. | اطلاعات این قلم متعلق به همین محموله است و تغییر بعدی کاتالوگ تاریخچه آن را بازنویسی نمی‌کند. |
| CargoType | نوع کالا | Cargo type | Governed classification of cargo. | Catalog item or shipment line. | — |
| UOM | واحد اندازه‌گیری | Unit of measure | Unit attached to a cargo quantity. | Quantity aggregation. | مقادیر با واحدهای ناسازگار نباید با هم جمع شوند. |
| LogisticsPoint | مکان لجستیکی سازمان | Organization logistics location | Reusable organization location master data. | A current tracking location or legacy selector. | مکان استانداردی که در پروژه‌ها و ثبت موقعیت محموله دوباره قابل انتخاب است. |
| ProjectLogisticsPoint | مکان پیکربندی‌شده پروژه | Project logistics location | A LogisticsPoint selected and ordered for a project. | Automatically generated route/checkpoint. | افزودن مکان به پروژه، مسیر یا نقطه کنترل را خودکار ایجاد نمی‌کند. |
| current tracking location | آخرین موقعیت ثبت‌شده | Latest recorded location | Latest location reported for a shipment/unit. | Logistics Network master data. | — |
| TrackingLocationReference | مکان رهگیری قدیمی | Legacy tracking location | Compatibility selector only; avoid exposing this name in new UI. | LogisticsPoint. | Internal term should be hidden. |
| DocumentDefinition | نوع سند | Document type | Governed definition and file policy. | Requirement or uploaded file. | وجود نوع سند در کاتالوگ، آن را الزامی نمی‌کند. |
| document requirement | الزام سند | Document requirement | Policy that a document is required at a specific scope. | Uploaded file or approval. | الزام مشخص می‌کند چه مدرکی لازم است؛ خودش فایل نیست. |
| CaseDocumentFile | فایل بارگذاری‌شده پرونده | Uploaded case file | Exact uploaded file version owned by the source request. | Document type, requirement, or approval. | بارگذاری فایل به معنی تأیید آن نیست. |
| OperationalDocumentRequirement | الزام سند محموله | Shipment document requirement | Requirement materialized independently for a shipment. | Project policy or file ownership. | — |
| Assignment | تخصیص مسئولیت | Assignment | Giving current responsibility for a request to an expert. | Referral policy/rule. | — |
| Referral | ارجاع درخواست | Referral | Sending a request through the assignment workflow. | The resulting assignment. | ارجاع می‌تواند به تخصیص خودکار یا دستی منجر شود. |
| current workload | بار کاری فعلی | Current workload | Count of assigned/in-progress request cases for the expert. | Capacity or referral engine count. | تعداد پرونده‌های دارای مسئولیت عملیاتی فعلی کارشناس در وضعیت تخصیص‌یافته یا در حال انجام. تخصیص پیش‌فرض نوبت‌گردشی است. |
| capacity count | ظرفیت مجاز | Capacity limit | Optional engine limit using its separately governed count. | Displayed current workload. | شمارش موتور ارجاع ممکن است با بار کاری نمایشی متفاوت باشد. |
| Round Robin | نوبت‌گردشی | Round robin | Default time-based assignment ordering. | Least-workload rule. | — |

## Census and consistency record

The expert workflow census reviewed 52 visible terms across dashboard/navigation, request detail, legacy tracking, operational shipments, execution units, cargo, documents, logistics configuration, user workload, and referral/assignment screens.

| Classification | Count | Representative findings |
| --- | ---: | --- |
| CLEAR | 26 | پروژه، درخواست حمل، محموله عملیاتی, نوع کالا، الزام سند، تخصیص دستی |
| NEEDS_REWORDING | 12 | واحد حمل, مشخصات واحد حمل, raw Execution Unit labels, raw status/action labels |
| NEEDS_HELP_TEXT | 9 | cargo catalog, logistics network, current workload, execution/trackable segment, document distinctions |
| INTERNAL_TERM_SHOULD_BE_HIDDEN | 4 | ExecutionUnit, ShipmentTransportUnit, OperationalEvent, TrackingLocationReference when shown as architecture names |
| SEMANTIC_AMBIGUITY — DO NOT FIX AS COPY | 1 | legacy trackable unit versus canonical ExecutionUnit convergence |

Resolved naming inconsistencies:

- Legacy request tracking consistently uses «بخش قابل رهگیری حمل» instead of mixing «واحد حمل»، «خودرو / واحد حمل»، and «نقطه ردیابی».
- Canonical execution management uses «بخش اجرایی حمل» and localized statuses/actions while retaining internal enum values.
- Cargo master data is «فهرست استاندارد کالاها» / «کالای استاندارد»; transactional cargo remains «قلم محموله».
- Organization master locations are «مکان‌های لجستیکی سازمان»; the reported location is «آخرین موقعیت ثبت‌شده».
- Documents retain the three-way distinction «نوع سند» / «الزام سند» / «فایل بارگذاری‌شده».
- «بار کاری فعلی» remains distinct from referral capacity and the least-workload compatibility count.

## Compatibility guardrails

The following internal names remain unchanged: `Project`, `ShipmentRequest`, `OperationalShipment`, `ExecutionUnit`, `ShipmentTransportUnit`, `OperationalEvent`, `CargoCatalogItem`, `ShipmentCargoItem`, `LogisticsPoint`, `TrackingLocationReference`, `DocumentDefinition`, `CaseDocumentFile`, assignment API fields, statuses, and event types. The semantic ambiguity between legacy `ShipmentTransportUnit` and canonical `ExecutionUnit` requires architecture-led convergence and is not resolved by copy.
