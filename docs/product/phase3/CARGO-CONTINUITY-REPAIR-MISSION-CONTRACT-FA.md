# قرارداد مأموریت ترمیم تداوم Cargo تاریخی

## هویت و حاکمیت

- `LPAF_BASELINE=2.7`
- `RIGOR=LEVEL_C_INTEGRATED`
- `CAPABILITY_TIER=SOL`
- `OWNER=Product Owner`
- `APPROVAL_REFERENCE=GOVERNED_HISTORICAL_CREATION_CONTINUITY_REPAIR_2026-09-29`
- `JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`
- `AFFECTED_JOURNEYS=FWD-J01,FWD-J02,FWD-J03,FWD-J04,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-04`

## Mission Contract

`OUTCOME`: برای یک Shipment تاریخی در هر بار اجرا، فقط facts گمشدهٔ ناشی از نقص شناخته‌شدهٔ Request→Shipment creation با یک فرمان maintenance دو مرحله‌ای، fail-closed، قابل ممیزی و idempotent ترمیم شود.

`PROBLEM`: ایجاد قدیمی Shipment می‌توانست Shipment Cargo و RoutePlan و Execution را بسازد اما Request Cargo lineage، requested quantity و `RouteCargoDestination` را جا بیندازد. مسیر ایجاد آینده قبلاً اصلاح و qualification شده است.

`IN_SCOPE`: plan خواندنی، apply صریح، binding دقیق به database و Cargo و source Request Cargo و RoutePlan و terminal leg بازبینی‌شده، اثبات lineage از accepted Quote و Request و creation audit/idempotency، snapshot مقدار درخواستی و UOM موجود، افزودن participation به همان RoutePlan revision و terminal leg اثبات‌شده، audit واحد به‌همراه outbox و ledger داخلی همان transaction، کنترل authority/tenant/conflict/concurrency/idempotency، qualification و ترمیم رکورد synthetic walkthrough فقط پس از PASS و integration.

`OUT_OF_SCOPE`: backfill گروهی، heuristic update، raw SQL، migration-time/startup repair، UI button، replan، تغییر topology/RouteLeg/Execution/owner/assignee/customer/entitlement/Quote/Request history، allocation توسط عامل، ساخت ETA input، production، deployment و release.

`ACTORS`: System Admin یا operator خودمیزبان که با هویت فعال، tenant فعال، نام operator دقیقاً برابر username و approval صریح از command maintenance استفاده می‌کند؛ همین فرمان offline محدود capability اختصاصی این تصمیم است و هیچ tenant permission عادی ایجاد نمی‌کند؛ ordinary Expert هیچ اختیار repair ندارد؛ Product Owner فقط allocation بعدی را دستی آزمایش می‌کند.

`SYSTEMS_OF_RECORD`: accepted `ExpertQuote` و `ShipmentRequest` و `RequestCargoItem` برای حقیقت تجاری؛ `OperationalShipment` و `ShipmentCargoItem` برای Cargo عملیاتی؛ `RoutePlan`/`RouteLeg`/`RouteCargoDestination` برای participation مسیر؛ `OperationalAudit` برای تاریخچهٔ repair.

`STOP_CONDITIONS`: هر ambiguity یا conflict، بیش از یک Cargo یا Request Cargo قابل انتخاب، route revision/path نامعین، tenant mismatch، downstream contradiction، authority ناکافی، نیاز به schema، تغییر غیرمنتظرهٔ source/runtime/migration، یا failure در qualification باعث توقف بخش affected می‌شود.

`DEFINITION_OF_DONE`: plan/apply تک-Shipment، eligibility کامل، replay بدون تغییر و بدون audit تکراری، conflict fail-closed، audit کامل، PostgreSQL 18 و concurrency، regressions و journeys روی exact candidate، canonical fast-forward و 0/0، سپس plan و در صورت PASS apply روی walkthrough و read verification. Human Walkthrough همچنان `IN_PROGRESS` و Release Ready برابر `NO` می‌ماند.

## Product Authority Record

`AUTHORIZED_PRODUCT_CHANGES`:

1. افزودن یک maintenance command غیر UI برای plan/apply ترمیم دقیق facts گمشدهٔ defect شناخته‌شده.
2. افزودن source Request و source Request Cargo linkage و requested quantity فقط وقتی source یکتا و authoritative است.
3. افزودن `RouteCargoDestination` روی همان active RoutePlan revision فقط وقتی terminal path یکتا است و topology تغییر نمی‌کند.
4. ثبت audit repair با دلیل `KNOWN_REQUEST_TO_SHIPMENT_CREATION_CONTINUITY_DEFECT`.

`DELEGATED_TECHNICAL_CHOICES`: ساختار service/CLI، شکل JSON plan، locking، fingerprint، query composition، test fixtures و evidence packaging، مشروط به حفظ product semantics و نبود migration.

`PROTECTED_OUT_OF_SCOPE_BEHAVIOR`: destination درخواستی Customer، destination برنامه‌ریزی‌شدهٔ عملیات، owner/assignee/customer/entitlement، Quote و Request history، planned/actual quantity، Route topology، Execution و allocation/delivery facts، Direct Shipment بدون lineage جعلی، Customer UI و همهٔ UX findingهای باز.

`DECISIONS_NEEDED=NONE_FOR_IMPLEMENTATION`; Human Product Walkthrough PASS فقط در اختیار Product Owner یا نمایندهٔ انسانی مجاز است.

`APPROVING_OWNER_OR_AUTHORITY=Product Owner`

`APPROVAL_REFERENCE=User mission: Forwarder — GOVERNED HISTORICAL CREATION-CONTINUITY REPAIR`

## Facts, assumptions, unknowns

`FACT`: canonical preflight روی `70ace52cf94de0ff0f9dea150cb0cd60cf4f0155` clean و GitHub `0/0` بود؛ Product HEAD برابر `2ddb61aa06721b884f7b142997cd15659865d4fc` و Alembic head یکتا `20261012_phase3_cargo_eta` است.

`FACT`: evidence قبلی defect و رکورد walkthrough را ثبت کرده و mutation را به نبود command برای active-plan participation متوقف کرده است.

`FACT`: schema فعلی تمام facts و `OperationalAudit` لازم را دارد؛ هدف `MIGRATION_REQUIRED=NO` است.

`ASSUMPTION`: هیچ apply تا تکمیل focused/full qualification و controlled integration روی walkthrough اجرا نمی‌شود؛ این assumption در gate اجرا دوباره بررسی می‌شود.

`FACT / APPLY BLOCKER`: مأموریت tracking code را `SR2-bqV0r_x-HBVeC0u02f5A3A` نوشته است، اما رکورد ذخیره‌شده و متصل به Shipment کد `SR2-bqVOr_x-HBVeC0uO2f5A3A` دارد (حرف `O` به‌جای رقم `0` در دو جایگاه). این دو مقدار بدون تأیید Product Owner یکی فرض نمی‌شوند. PLAN می‌تواند هویت ذخیره‌شده را نشان دهد، اما walkthrough APPLY تا رفع این ambiguity ممنوع است.

## Reference impact and PDA-07 target

- `LPAF_REFERENCE_IMPACT=NONE`: baseline v2.7 تغییر نمی‌کند.
- `PROJECT_ARCHITECTURE_IMPACT=UPDATE_REQUIRED`: authority و historical-repair semantics در ADR مستقل ثبت می‌شود.
- `PDA_07_TARGET`: repair capability و audit برابر `AUTHORIZED`; تمام protected behavior برابر `PRESERVED`; هر تفاوت دیگر `VIOLATION` یا `UNKNOWN` و blocker است.
