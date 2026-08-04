# Reference Data Initial Catalog — Evidence and Product/Data Review

- **Status:** Reviewed and Accepted for bounded Release 1.5.0 implementation
- **Date:** 2026-08-01
- **Target:** 1.5.0 — Reference Data Initial Catalog
- **Governing decision:** [PDR-014](PDR-014-initial-reference-data-catalog.md)
- **Database head observed:** `20260807_master_data`
- **Production interaction:** None

## Acceptance outcome

Product, Data, Architecture, Operations, and Security accepted PDR-014 D01-D10 on 2026-08-01. `CARGO_GENERAL_GOODS` and `SERVICE_PROJECT_LOGISTICS` remain Deferred and are excluded from the executable catalog. The Accepted executable set is 15 CargoTypes, 12 ServiceTypes, and 9 Units of Measure. ADR-021 is clarified to include `ReferenceDataSeedRun`. Production execution and every later cargo capability remain unauthorized.

## 1. Governance findings

- Confirmed Accepted: PDR-013-D01, D04, D12, and ADR-021, limited to B1.
- At this Release 1.5.0 review date, PDR-013-D02/D03/D05–D11 and ADR-022–024 were Proposed and RFC-002/EPIC-002 were Draft. The later [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md) independently accepts bounded D05/D06/D07, internal-only D11, and ADR-022. D02/D03/D08–D10, customer/public D11, ADR-023/024, and unauthorized later capabilities remain Proposed.
- Confirmed B1 implementation: explicit `cargo_type`, `service_type`, and `unit_of_measure` tables; immutable uppercased code; bilingual labels; active state; order; hierarchy/dimension checks; optimistic version; admin API/UI; no data inserted by migration.
- Confirmed gap: B1 stores neither source/provenance nor seed-execution metadata, system ownership, user-selectability, precision recommendation, or primary/supporting service eligibility.
- Confirmed current data limitations: cargo is free text with unitless weight/volume and value without currency; no CargoType/ServiceType/UOM transaction reference exists.
- Result: only rows Accepted by the recorded workshop outcome are executable; Deferred rows remain documented below and are excluded from the version-controlled catalog.

## 2. Evidence matrix

| Raw Value | Source | Current Meaning | Proposed Canonical Concept | Duplicate/Conflict | Confidence |
| --- | --- | --- | --- | --- | --- |
| `cargo_description` / “Test cargo” | `ShipmentRequest`, request tests/forms | Unstructured customer goods narrative | Remain legacy free text; not a CargoType | Cannot infer category | High |
| `cargo_weight` with UI label kg | model, form, public/detail UI, XLSX | Numeric weight; persistence has no UOM | Future quantity + approved `UOM_KILOGRAM` only when explicitly selected | UI assumption conflicts with stored semantics | High |
| `cargo_volume` with UI label m³ | model, form, public/detail UI, XLSX | Numeric volume; persistence has no UOM | Future quantity + approved `UOM_CUBIC_METER` only when explicitly selected | UI assumption conflicts with stored semantics | High |
| `cargo_value` / Toman label | model, detail UI, XLSX | Declared/commercial value without stored currency | Deferred transactional value + currency | Not reference data | High |
| `cargo_type` | OpenAPI request example/schema only | Contract-only string; no runtime storage | Future CargoType reference | Contract/runtime drift | High |
| Sea Freight | TransportMethod seed/test | Sea movement method | TransportMode candidate, not ServiceType | Same axis as sea transport | High |
| Air Freight / Air Transport | TransportMethod seed and translations | Air movement method | One TransportMode concept | Naming duplicate | High |
| Land Transport / Road Transport / `road` | seed, fallback, translations | Road/land movement method | One road TransportMode concept | Naming and scope duplicate | High |
| Rail Transport / `rail` | seed, fallback, translations | Rail movement method | Rail TransportMode | Duplicate rows possible across domestic/international seed lists | High |
| `sea`, `air`, `road`, `rail` | LocationForm fallback | Frontend fallback method codes | TransportMode codes | Not linked to TransportMethod IDs/codes | High |
| domestic / international | ShipmentRequest/form | Geographic shipment scope | Project/Shipment scope | Must not become ServiceType | High |
| customer choice / forwarder suggestion | transport payload | Preference/selection authority | Transport preference | Not a service or mode | High |
| truck / wagon / container / other | execution-unit translations | ExecutionUnit type | ExecutionUnit/ContainerType domain | “container” conflicts with count-UOM candidate | High |
| customs / border customs | destination form/routes | Location/regulatory destination concept | Customs domain; customs-clearance service only if sold/coordinated | Location ≠ service | High |
| loading | lifecycle/status translations | ExecutionUnit operational state/activity | Operational activity | Must not automatically become ServiceType | Medium |
| packaging examples: pallet/carton/box/bag/drum/roll/package | implementation contract; no runtime field | Packaging/handling form | PackagingType or handling unit, deferred | Not universal UOM | High |
| item/unit/piece | implementation contract | Count expression | Candidate `UOM_PIECE` | Three overlapping English terms | Medium |
| set / pair | implementation contract | Count by grouped composition | Deferred specialized count UOM | Conversion/composition undefined | Medium |
| kilogram / kg | implicit UI plus contract | Weight unit | Candidate `UOM_KILOGRAM` | Legacy values not safely mappable | High |
| gram / g | contract only | Weight unit | Candidate `UOM_GRAM` | No repository usage | Medium |
| metric ton / t | contract only | Weight unit | Candidate `UOM_METRIC_TON` | Must not use ambiguous `T` | Medium |
| cubic meter / m³ | implicit UI plus contract | Volume unit | Candidate `UOM_CUBIC_METER` | Legacy values not safely mappable | High |
| liter / L | contract only | Volume unit | Candidate `UOM_LITER` | No repository usage | Medium |
| meter / centimeter / kilometer | contract only | Length/distance units | Candidate length UOMs | Kilometer may be route distance rather than cargo quantity | Medium |
| Dangerous Goods | RFC/discovery examples and contract | Regulatory characteristic | Future cross-cutting cargo attribute | Overlaps every commodity type | High |
| Perishable / Temperature-Controlled Goods | RFC/discovery examples and contract | Handling/temperature characteristic | Future cross-cutting cargo attribute | Overlaps every commodity type | High |
| Other | PDR/contract | Known value outside taxonomy | Controlled user selection with explanation | Schema cannot enforce selection policy | High |
| Unclassified | PDR-013-D12/ADR-021 | Unknown legacy/system classification | System-owned non-user-selectable value | Schema cannot enforce ownership/selectability | High |

## 3. Proposed CargoType catalog

All accepted executable entries are top-level (`parent_code = —`) and active. The row table retains the workshop proposals and final row dispositions; only the 15 Accepted rows are present in the executable catalog.

| Order | Code | Persian title | English title | Definition | Inclusion examples | Exclusion examples | Source/rationale |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 10 | `CARGO_GENERAL_GOODS` | کالاهای عمومی | General Goods | Ordinary non-specialized goods not better represented by an approved category | mixed non-regulated merchandise | regulated chemicals; named machinery | Broad fallback category requested by contract; boundaries need Product review |
| 20 | `CARGO_AUTOMOTIVE_MECHANICAL_COMPONENTS` | قطعات خودرویی و مکانیکی | Automotive and Mechanical Components | Parts and assemblies primarily used in vehicles or mechanical systems | brake parts, gears, bearings | complete vehicles; industrial machines | Cross-industry proposal; avoids automotive-only model |
| 30 | `CARGO_INDUSTRIAL_MACHINERY_EQUIPMENT` | ماشین‌آلات و تجهیزات صنعتی | Industrial Machinery and Equipment | Machines and capital equipment used in industrial operations | production machine, industrial pump | spare component; vehicle | Contract candidate |
| 40 | `CARGO_RAW_MATERIALS` | مواد اولیه | Raw Materials | Unprocessed or minimally processed inputs not covered by a more specific material category | mineral input, bulk feedstock | metal product; finished consumer good | Contract candidate; overlap must be resolved by specificity rule |
| 50 | `CARGO_METALS_METAL_PRODUCTS` | فلزات و محصولات فلزی | Metals and Metal Products | Primary metals, semi-finished metals, and metal products | steel coil, aluminum billet | finished machinery | Contract/RFC examples |
| 60 | `CARGO_CHEMICALS` | مواد شیمیایی | Chemicals | Chemical substances and preparations excluding separately governed petroleum/petrochemical products | industrial chemical, resin | medicine; crude oil | Contract/RFC examples; hazard remains separate attribute |
| 70 | `CARGO_PETROLEUM_PETROCHEMICAL` | فرآورده‌های نفتی و پتروشیمی | Petroleum and Petrochemical Products | Petroleum-origin fuels, oils, and petrochemical products | lubricants, polymer feedstock | unrelated chemical; metal | Contract candidate |
| 80 | `CARGO_FOOD_AGRICULTURAL` | محصولات غذایی و کشاورزی | Food and Agricultural Products | Food, beverages, crops, and agricultural products | fruit, grain, packaged food | pharmaceuticals | Contract/RFC examples; perishability remains separate |
| 90 | `CARGO_PHARMACEUTICAL_MEDICAL` | کالاهای دارویی و پزشکی | Pharmaceutical and Medical Goods | Medicines, medical supplies, and medical devices | medicine, surgical supply | general chemical | Contract candidate |
| 100 | `CARGO_ELECTRICAL_ELECTRONIC` | کالاهای برقی و الکترونیکی | Electrical and Electronic Goods | Electrical equipment, electronics, and their primary assemblies | motor, circuit board, appliance electronics | mechanical-only component | Contract candidate |
| 110 | `CARGO_CONSTRUCTION_MATERIALS` | مصالح ساختمانی | Construction Materials | Materials primarily supplied for building and civil works | cement, tile, insulation | construction machinery | Contract candidate |
| 120 | `CARGO_TEXTILE_APPAREL` | منسوجات و پوشاک | Textile and Apparel | Fibers, fabrics, garments, and textile products | fabric roll, clothing | unrelated consumer goods | Contract candidate |
| 130 | `CARGO_CONSUMER_FINISHED_GOODS` | کالاهای مصرفی و نهایی | Consumer and Finished Goods | Finished goods intended primarily for end use and not better represented elsewhere | household goods, retail products | industrial equipment; food | Contract candidate; overlaps General Goods and needs Product acceptance |
| 140 | `CARGO_VEHICLES_MOBILE_EQUIPMENT` | وسایل نقلیه و تجهیزات متحرک | Vehicles and Mobile Equipment | Complete vehicles and self-propelled/mobile equipment transported as cargo | car, forklift, mobile crane | vehicle components | Contract candidate |
| 900 | `CARGO_OTHER` | سایر کالاها | Other | Known cargo that does not fit an approved category | novel explicitly described goods | unknown or missing description | Contract policy; later user selection requires explanation |
| 999 | `CARGO_UNCLASSIFIED` | طبقه‌بندی‌نشده | Unclassified | System-owned state for cargo lacking an evidence-backed classification | legacy unknown description | known out-of-taxonomy cargo | Accepted no-guessed-backfill policy; enforcement gap remains |

### CargoType exclusions/deferments

| Candidate | Classification | Reason |
| --- | --- | --- |
| Dangerous Goods | Future cargo attribute | Cross-cutting regulatory characteristic, not exclusive commodity type |
| Perishable / Temperature-Controlled Goods | Future cargo attribute | Cross-cutting handling characteristic |
| Deep industry children | Deferred | Repository has no frequency/evidence to justify depth |

## 4. Proposed ServiceType catalog

The 12 Accepted executable entries are active. “Primary/supporting eligibility” remains a recommendation only; PDR-013-D02/D03 remain Proposed and no relationship is implemented.

| Order | Code | Persian title | English title | Definition | Eligibility recommendation | Scope notes | Source/rationale |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 10 | `SERVICE_FREIGHT_TRANSPORT` | خدمات حمل بار | Freight Transport Service | Commercial coordination or sale of freight movement independent of mode and geography | Primary or supporting | Mode belongs to TransportMode; domestic/international belongs to shipment scope | Separates sold service from current mode strings |
| 20 | `SERVICE_CUSTOMS_CLEARANCE` | ترخیص گمرکی | Customs Clearance | Coordination/performance of customs-clearance work | Supporting; primary only if Product approves | Customs location is not this service | Contract candidate |
| 30 | `SERVICE_WAREHOUSING` | انبارداری | Warehousing | Temporary storage and warehouse coordination | Supporting | Does not implement Warehouse/WMS | Contract candidate |
| 40 | `SERVICE_LOADING` | بارگیری | Loading | Commercially scoped loading service | Supporting | Operational loading event/status remains separate | Contract candidate with activity conflict noted |
| 50 | `SERVICE_UNLOADING` | تخلیه بار | Unloading | Commercially scoped unloading service | Supporting | Operational unloading activity remains separate | Contract candidate |
| 60 | `SERVICE_PACKING_REPACKING` | بسته‌بندی و بسته‌بندی مجدد | Packing and Repacking | Packing or repacking supplied as a service | Supporting | PackagingType remains separate | Contract candidate |
| 70 | `SERVICE_CARGO_CONSOLIDATION` | تجمیع بار | Cargo Consolidation | Combining cargo consignments as a coordinated service | Supporting | No allocation/split/merge behavior authorized | Contract candidate |
| 80 | `SERVICE_CARGO_DECONSOLIDATION` | تفکیک بار تجمیعی | Cargo Deconsolidation | Separating consolidated cargo as a coordinated service | Supporting | No cargo allocation behavior authorized | Contract candidate |
| 90 | `SERVICE_DOCUMENTATION` | خدمات اسنادی | Documentation Service | Preparation/coordination of logistics documentation | Supporting | Does not change Document Platform ownership | Contract candidate |
| 100 | `SERVICE_INSURANCE_COORDINATION` | هماهنگی بیمه | Insurance Coordination | Coordination of cargo/shipment insurance without becoming insurer of record | Supporting | Commercial/legal scope requires review | Contract candidate |
| 110 | `SERVICE_DISTRIBUTION_LAST_MILE` | توزیع و تحویل نهایی | Distribution and Last Mile | Coordinated final distribution/delivery service | Primary or supporting | Delivery lifecycle semantics remain unchanged | Contract candidate |
| 120 | `SERVICE_PROJECT_LOGISTICS` | لجستیک پروژه‌ای | Project Logistics | Coordinated logistics service for complex/project cargo | Primary | Commercial package; must not create Project relationships here | Contract candidate |
| 900 | `SERVICE_OTHER` | سایر خدمات | Other Service | Known sold/coordinated service outside the approved vocabulary | Supporting; primary only if approved | Later selection requires explanation and review | Controlled fallback proposal |

### Service candidate classification and exclusions

| Candidate | Classification | Outcome |
| --- | --- | --- |
| Domestic Freight Transport | Composite scope + service | Exclude; use Freight Transport plus domestic shipment scope |
| International Freight Transport | Composite scope + service | Exclude; use Freight Transport plus international shipment scope |
| Road/Rail/Sea/Air Freight Service | TransportMode-composite | Exclude from ServiceType; preserve as mode |
| Multimodal Coordination | Composite/commercial package | Defer pending distinction from Freight Transport and Project Logistics |
| Transit Service | Ambiguous regulatory/geographic/commercial concept | Defer pending Product definition |
| Loading/Unloading | Operational activity and possible sold service | Proposed only when explicitly contracted; never infer from events |
| Packing/Repacking | Operational activity and possible sold service | Proposed only when explicitly contracted |
| Project Logistics | Commercial package | Proposed broad service; no relationships in this release |

## 5. Proposed UnitOfMeasure catalog

The nine Accepted executable entries are active. Precision remains a recommendation for future quantities, not implemented schema behavior.

| Order | Code | Persian title | English title | Symbol | Dimension | Definition | Precision recommendation | Source/rationale |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | `UOM_PIECE` | عدد | Piece | `pcs` | COUNT | Count of discrete individual items | 0 decimal places | Resolves item/unit/piece overlap conservatively; Product review required |
| 20 | `UOM_GRAM` | گرم | Gram | `g` | WEIGHT | SI mass unit equal to one-thousandth kilogram | Up to 3 | Contract candidate |
| 30 | `UOM_KILOGRAM` | کیلوگرم | Kilogram | `kg` | WEIGHT | SI base logistics mass unit | Up to 3 | Current UI implicitly labels weight as kg, but legacy values are not mapped |
| 40 | `UOM_METRIC_TON` | تن متریک | Metric Ton | `t` | WEIGHT | Exactly 1,000 kilograms; no conversion is implemented | Up to 3 | Explicitly disambiguates ton and symbol |
| 50 | `UOM_LITER` | لیتر | Liter | `L` | VOLUME | Volume unit equal to one cubic decimeter | Up to 3 | Contract candidate |
| 60 | `UOM_CUBIC_METER` | متر مکعب | Cubic Meter | `m³` | VOLUME | SI-derived cubic volume unit | Up to 3 | Current UI implicitly labels volume as m³; legacy values are not mapped |
| 70 | `UOM_CENTIMETER` | سانتی‌متر | Centimeter | `cm` | LENGTH | One-hundredth meter | Up to 2 | Contract candidate |
| 80 | `UOM_METER` | متر | Meter | `m` | LENGTH | SI length unit | Up to 3 | Contract candidate |
| 90 | `UOM_KILOMETER` | کیلومتر | Kilometer | `km` | LENGTH | One thousand meters | Up to 3 | Contract candidate; likely route use must not imply cargo use |

### UOM exclusions/deferments

| Candidate | Classification | Outcome |
| --- | --- | --- |
| unit/item | Ambiguous synonym | Consolidate proposal under Piece; do not seed separately |
| package | PackagingType / ambiguous count | Defer |
| pallet | Handling unit / PackagingType | Defer |
| carton, box, bag, drum, roll | PackagingType | Defer |
| container | ExecutionUnit/ContainerType | Defer; never treat current container unit as UOM |
| set, pair | Specialized count UOM | Defer until composition/exact-UOM policy is accepted |
| conversion factors | Conversion policy | Excluded from 1.5.0 |

## 6. Seed architecture and CLI behavior

Preferred format after approval: strict UTF-8 JSON because it is deterministic, non-executable, readily schema-validated, and supports exact checksum calculation. Documentation retains rationale/examples. The source contains `schema_version`, `catalog_version`, `source_version`, ordered domain arrays, and a SHA-256 checksum calculated over canonical JSON excluding the checksum field.

Planned command contract:

```text
python -m backend.reference_data_cli plan
python -m backend.reference_data_cli apply --confirm --operator <name> --approval-reference <reference> --expected-checksum <checksum>
```

Plan/apply rules:

| Existing state | Required result |
| --- | --- |
| Code absent | Create in approved parent-first order |
| Code and all governed fields match | Unchanged/no-op |
| Code exists with changed label/definition/parent/symbol/dimension/order | Conflict; no writes |
| Code exists inactive | Conflict; never reactivate silently |
| Same normalized title under different code | Possible duplicate conflict |
| Parent missing/inactive | Validation failure before writes |
| Invalid UOM dimension | Validation failure before writes |
| Production/manual value not in catalog | Preserve and report; never delete |

The apply transaction begins only after complete validation and zero conflicts. Output is secret-safe and includes catalog/source/schema version, checksum, environment, execution ID, created/unchanged/conflict counts, and final outcome. Normal apply has no update or delete mode. Startup and Alembic migrations never invoke it.

### Resolved implementation gate

The B1 schema had no suitable global seed-execution audit record, and `OperationalAudit` remains organization/actor-scoped and is not repurposed. The accepted resolution is the bounded `ReferenceDataSeedRun` design under clarified ADR-021. Its additive migration, approved catalog, CLI, and tests are part of Release 1.5.0 implementation; Production execution remains separately prohibited.

## 7. Impact assessment

- **Schema/migration:** The accepted additive `20260808_reference_seed` migration creates only `ReferenceDataSeedRun`; it inserts no catalog rows. Further provenance changes require separate approval.
- **Admin UI:** No change made. Current UI shows active/inactive but cannot label system versus manual provenance.
- **Backward compatibility:** Legacy cargo fields and all TransportMethod behavior remain unchanged. No conversion, classification, or backfill occurs.
- **Version:** The accepted initial catalog plus explicit CLI is a backward-compatible MINOR, 1.5.0.
- **Deployment:** Release 1.5.0 requires only the application and additive database migration. Catalog apply is optional migration tooling, not a post-deploy requirement; administrators may create all Reference Data through Admin UI. No automatic Seed is authorized. Release 1.4.0 remains untouched (current policy: ADR-028).

## 8. Completion gates

| Gate | Result |
| --- | --- |
| Repository Vocabulary Audited | PASS — repository evidence recorded |
| CargoType Catalog Proposed | PASS — 16 proposed values |
| ServiceType Catalog Proposed | PASS — 13 proposed values plus classification |
| UOM Catalog Proposed | PASS — 9 proposed values plus exclusions |
| Domain Conflicts Resolved | PASS — General Goods and Project Logistics Deferred |
| Product/Data Decision Recorded | PASS — PDR-014 Accepted |
| Seed CLI Idempotent | IMPLEMENTED; verification recorded by implementation report |
| Dry Run | IMPLEMENTED as read-only `plan` |
| Conflict Detection | IMPLEMENTED fail-closed |
| PostgreSQL Verification | PASS — full canonical migration chain, first apply, repeated apply, and disposable database cleanup |
| Seed Data Executable | YES for explicit non-Production plan/apply; Production execution unauthorized |
| Cargo Catalog Excluded | PASS |
| ShipmentCargoItem Excluded | PASS |
| Allocation Excluded | PASS |
| Search/Dashboard Excluded | PASS |
| Ready for Product/Data Review | COMPLETE |
| Ready for Commit | Subject to implementation test gates; no staging/commit performed |

## 9. Exact recommended next action

Complete the bounded implementation verification, including PostgreSQL when a disposable test database is available. Review the exact plan output before any authorized environment apply. Production execution requires a separate explicit authorization and is not part of this work.
