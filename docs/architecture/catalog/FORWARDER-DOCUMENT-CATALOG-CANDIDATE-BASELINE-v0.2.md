# Forwarder Document Master Catalog — Authoritative Candidate Baseline v0.2

Status: AUTHORITATIVE REVIEW BASELINE

Purpose: Candidate-lineage source for controlled catalog package generation. This is review input, not an applied seed.

## Original 68-row candidate baseline + resolved lineage

| # | Original Code | Persian Name | English Name | Resolved Decision | Canonical Outcome |
|---:|---|---|---|---|---|
| 1 | `COMMERCIAL_INVOICE` | فاکتور تجاری | Commercial Invoice | `KEEP` | `COMMERCIAL_INVOICE` |
| 2 | `PROFORMA_INVOICE` | پیش‌فاکتور | Proforma Invoice | `KEEP` | `PROFORMA_INVOICE` |
| 3 | `PACKING_LIST` | فهرست بسته‌بندی / صورت عدلبندی | Packing List | `KEEP` | `PACKING_LIST` |
| 4 | `PURCHASE_ORDER` | سفارش خرید | Purchase Order | `KEEP` | `PURCHASE_ORDER` |
| 5 | `CERTIFICATE_OF_ORIGIN` | گواهی مبدأ | Certificate of Origin | `KEEP` | `CERTIFICATE_OF_ORIGIN` |
| 6 | `PREFERENTIAL_CERTIFICATE_OF_ORIGIN` | گواهی مبدأ ترجیحی | Preferential Certificate of Origin | `KEEP` | `PREFERENTIAL_CERTIFICATE_OF_ORIGIN` |
| 7 | `BILL_OF_LADING` | بارنامه دریایی | Bill of Lading | `KEEP` | `BILL_OF_LADING` |
| 8 | `SEA_WAYBILL` | راهنامه دریایی | Sea Waybill | `KEEP` | `SEA_WAYBILL` |
| 9 | `HOUSE_BILL_OF_LADING` | بارنامه فرعی دریایی | House Bill of Lading | `KEEP` | `HOUSE_BILL_OF_LADING` |
| 10 | `MASTER_BILL_OF_LADING` | بارنامه مادر دریایی | Master Bill of Lading | `KEEP` | `MASTER_BILL_OF_LADING` |
| 11 | `AIR_WAYBILL` | راهنامه هوایی | Air Waybill | `KEEP` | `AIR_WAYBILL` |
| 12 | `HOUSE_AIR_WAYBILL` | راهنامه هوایی فرعی | House Air Waybill | `KEEP` | `HOUSE_AIR_WAYBILL` |
| 13 | `MASTER_AIR_WAYBILL` | راهنامه هوایی مادر | Master Air Waybill | `KEEP` | `MASTER_AIR_WAYBILL` |
| 14 | `CMR_CONSIGNMENT_NOTE` | راهنامه جاده‌ای CMR | CMR Road Consignment Note | `KEEP` | `CMR_CONSIGNMENT_NOTE` |
| 15 | `RAIL_CONSIGNMENT_NOTE` | راهنامه ریلی | Rail Consignment Note | `KEEP_AS_FALLBACK` | `RAIL_CONSIGNMENT_NOTE` |
| 16 | `CIM_CONSIGNMENT_NOTE` | راهنامه ریلی CIM | CIM Rail Consignment Note | `KEEP` | `CIM_CONSIGNMENT_NOTE` |
| 17 | `SMGS_CONSIGNMENT_NOTE` | راهنامه ریلی SMGS | SMGS Consignment Note | `KEEP` | `SMGS_CONSIGNMENT_NOTE` |
| 18 | `CIM_SMGS_CONSIGNMENT_NOTE` | راهنامه مشترک CIM/SMGS | CIM/SMGS Consignment Note | `KEEP` | `CIM_SMGS_CONSIGNMENT_NOTE` |
| 19 | `MULTIMODAL_TRANSPORT_DOCUMENT` | سند حمل چندوجهی | Multimodal Transport Document | `KEEP` | `MULTIMODAL_TRANSPORT_DOCUMENT` |
| 20 | `FIATA_FBL` | بارنامه حمل چندوجهی فیاتا | FIATA Multimodal Transport Bill of Lading | `KEEP` | `FIATA_FBL` |
| 21 | `FIATA_FWB` | راهنامه حمل چندوجهی فیاتا | FIATA Multimodal Transport Waybill | `KEEP` | `FIATA_FWB` |
| 22 | `FIATA_FCR` | گواهی دریافت فورواردر فیاتا | FIATA Forwarders Certificate of Receipt | `KEEP` | `FIATA_FCR` |
| 23 | `FIATA_FCT` | گواهی حمل فورواردر فیاتا | FIATA Forwarders Certificate of Transport | `KEEP` | `FIATA_FCT` |
| 24 | `FIATA_FWR` | قبض انبار فیاتا | FIATA Warehouse Receipt | `KEEP` | `FIATA_FWR` |
| 25 | `WAREHOUSE_RECEIPT` | قبض انبار | Warehouse Receipt | `KEEP` | `WAREHOUSE_RECEIPT` |
| 26 | `DELIVERY_ORDER` | دستور تحویل | Delivery Order | `KEEP` | `DELIVERY_ORDER` |
| 27 | `ARRIVAL_NOTICE` | اعلامیه ورود | Arrival Notice | `KEEP` | `ARRIVAL_NOTICE` |
| 28 | `BOOKING_CONFIRMATION` | تأییدیه رزرو حمل | Booking Confirmation | `KEEP` | `BOOKING_CONFIRMATION` |
| 29 | `SHIPPING_INSTRUCTION` | دستور حمل | Shipping Instruction | `KEEP` | `SHIPPING_INSTRUCTION` |
| 30 | `CARGO_MANIFEST` | مانیفست بار | Cargo Manifest | `KEEP` | `CARGO_MANIFEST` |
| 31 | `FREIGHT_MANIFEST` | مانیفست کرایه | Freight Manifest | `KEEP` | `FREIGHT_MANIFEST` |
| 32 | `CONTAINER_MANIFEST` | مانیفست کانتینر | Container Manifest | `KEEP` | `CONTAINER_MANIFEST` |
| 33 | `AIR_CARGO_MANIFEST` | مانیفست بار هوایی | Air Cargo Manifest | `KEEP` | `AIR_CARGO_MANIFEST` |
| 34 | `SEA_CARGO_DECLARATION` | اظهارنامه بار دریایی | Sea Cargo Declaration | `KEEP` | `SEA_CARGO_DECLARATION` |
| 35 | `DANGEROUS_GOODS_DECLARATION` | اظهارنامه کالای خطرناک | Dangerous Goods Declaration | `KEEP` | `DANGEROUS_GOODS_DECLARATION` |
| 36 | `DANGEROUS_GOODS_MANIFEST` | مانیفست کالای خطرناک | Dangerous Goods Manifest | `KEEP` | `DANGEROUS_GOODS_MANIFEST` |
| 37 | `CUSTOMS_DECLARATION` | اظهارنامه گمرکی | Customs Declaration | `KEEP_AS_FALLBACK` | `CUSTOMS_DECLARATION` |
| 38 | `IMPORT_CUSTOMS_DECLARATION` | اظهارنامه واردات | Import Customs Declaration | `KEEP` | `IMPORT_CUSTOMS_DECLARATION` |
| 39 | `EXPORT_CUSTOMS_DECLARATION` | اظهارنامه صادرات | Export Customs Declaration | `KEEP` | `EXPORT_CUSTOMS_DECLARATION` |
| 40 | `TRANSIT_DECLARATION` | اظهارنامه ترانزیت | Transit Declaration | `KEEP` | `TRANSIT_DECLARATION` |
| 41 | `TIR_CARNET` | کارنه تیر | TIR Carnet | `KEEP` | `TIR_CARNET` |
| 42 | `ATA_CARNET` | کارنه آ.ت.آ | ATA Carnet | `KEEP` | `ATA_CARNET` |
| 43 | `IMPORT_LICENSE` | مجوز واردات | Import Licence | `KEEP` | `IMPORT_LICENSE` |
| 44 | `EXPORT_LICENSE` | مجوز صادرات | Export Licence | `KEEP` | `EXPORT_LICENSE` |
| 45 | `REGISTRATION_ORDER` | ثبت سفارش | Registration Order | `HYBRID_CONFIRMED` | `REGISTRATION_ORDER` |
| 46 | `STATISTICAL_REGISTRATION` | ثبت آماری | Statistical Registration | `HYBRID_CONFIRMED` | `STATISTICAL_REGISTRATION` |
| 47 | `CUSTOMS_RELEASE_PERMIT` | پروانه گمرکی / پروانه سبز | Customs Release Permit | `KEEP` | `CUSTOMS_RELEASE_PERMIT` |
| 48 | `WAREHOUSE_RELEASE` | ترخیصیه | Warehouse Release | `RENAME` | `IRAN_CARRIER_RELEASE` |
| 49 | `DOMESTIC_WAYBILL` | بارنامه داخلی | Domestic Waybill | `KEEP` | `DOMESTIC_WAYBILL` |
| 50 | `INSURANCE_CERTIFICATE` | گواهی بیمه | Insurance Certificate | `KEEP` | `INSURANCE_CERTIFICATE` |
| 51 | `INSURANCE_POLICY` | بیمه‌نامه باربری | Cargo Insurance Policy | `KEEP` | `INSURANCE_POLICY` |
| 52 | `INSPECTION_CERTIFICATE` | گواهی بازرسی | Inspection Certificate | `KEEP` | `INSPECTION_CERTIFICATE` |
| 53 | `QUALITY_CERTIFICATE` | گواهی کیفیت | Certificate of Quality | `KEEP` | `QUALITY_CERTIFICATE` |
| 54 | `CERTIFICATE_OF_CONFORMITY` | گواهی انطباق | Certificate of Conformity | `KEEP` | `CERTIFICATE_OF_CONFORMITY` |
| 55 | `PHYTOSANITARY_CERTIFICATE` | گواهی بهداشت نباتی | Phytosanitary Certificate | `KEEP` | `PHYTOSANITARY_CERTIFICATE` |
| 56 | `VETERINARY_CERTIFICATE` | گواهی دامپزشکی | Veterinary Certificate | `KEEP` | `VETERINARY_CERTIFICATE` |
| 57 | `SANITARY_CERTIFICATE` | گواهی بهداشتی | Sanitary Certificate | `KEEP` | `SANITARY_CERTIFICATE` |
| 58 | `QUARANTINE_CERTIFICATE` | گواهی قرنطینه | Quarantine Certificate | `REMOVE` | `EXCLUDED` |
| 59 | `WEIGHT_CERTIFICATE` | گواهی وزن | Weight Certificate | `KEEP` | `WEIGHT_CERTIFICATE` |
| 60 | `FREIGHT_INVOICE` | صورتحساب کرایه حمل | Freight Invoice | `KEEP` | `FREIGHT_INVOICE` |
| 61 | `LETTER_OF_CREDIT` | اعتبار اسنادی | Letter of Credit | `KEEP` | `LETTER_OF_CREDIT` |
| 62 | `BILL_OF_EXCHANGE` | برات | Bill of Exchange | `KEEP` | `BILL_OF_EXCHANGE` |
| 63 | `PAYMENT_CONFIRMATION` | تأییدیه پرداخت | Payment Confirmation | `KEEP` | `PAYMENT_CONFIRMATION` |
| 64 | `BANKING_IMPORT_DOCUMENT` | سند بانکی واردات | Import Banking Document | `SPLIT_REMOVE_GENERIC` | `EXCLUDED` |
| 65 | `GATE_PASS` | مجوز خروج | Gate Pass | `DEFER` | `DEFERRED` |
| 66 | `RELEASE_ORDER` | مجوز آزادسازی | Release Order | `RENAME` | `CONTAINER_RELEASE_ORDER` |
| 67 | `RECEIPT_ADVICE` | اعلام دریافت کالا | Receipt Advice | `KEEP` | `RECEIPT_ADVICE` |
| 68 | `DELIVERY_NOTICE` | اعلام تحویل کالا | Delivery Notice | `RENAME` | `GOODS_DELIVERY_NOTICE` |

## Resolved domain decisions

- `RAIL_CONSIGNMENT_NOTE`: keep as generic fallback when CIM/SMGS regime is unknown or not applicable.
- `CUSTOMS_DECLARATION`: keep as generic fallback; prefer import/export/transit-specific definitions when procedure is known.
- `FREIGHT_MANIFEST`: keep as distinct from Cargo Manifest and Freight Invoice.
- `CONTAINER_MANIFEST`: keep as distinct from Cargo Manifest, Sea Cargo Declaration, and Packing List.
- `PAYMENT_CONFIRMATION`: keep as external payment evidence, not an internal workflow state.
- `REGISTRATION_ORDER`: hybrid evidence type; structured number/status/validity/amendment belongs to a future authorization/reference model.
- `STATISTICAL_REGISTRATION`: same hybrid boundary.
- `WAREHOUSE_RELEASE` → `IRAN_CARRIER_RELEASE` — Persian: `ترخیصیه شرکت حمل‌ونقل`; English: `Iran Carrier Cargo Release`.
- `RELEASE_ORDER` → `CONTAINER_RELEASE_ORDER` — Persian: `دستور آزادسازی کانتینر`; English: `Container Release Order`.
- `DELIVERY_NOTICE` → `GOODS_DELIVERY_NOTICE` — Persian: `اعلامیه تحویل کالا`; English: `Goods Delivery Notice`.
- `QUARANTINE_CERTIFICATE`: remove as universal umbrella.
- `BANKING_IMPORT_DOCUMENT`: remove as one broad generic definition; specific financial evidence types only.
- `GATE_PASS`: deferred pending proof of a durable managed artifact.
- `BARFARABARAN_REFERENCE`: DOMAIN_CONFIRMATION_REQUIRED and outside DocumentDefinition.

## Future candidates discovered during review (not part of original 68)

- `PROOF_OF_DELIVERY`
- `REMITTANCE_ADVICE`
- `SWIFT_PAYMENT_MESSAGE` (product/source confirmation required)

## External-reference boundary

- Document type ≠ document/reference number.
- Customs Declaration ≠ Cotage number.
- Warehouse Receipt ≠ Warehouse Receipt ID.
- Registration Order evidence ≠ Registration Order number.
- Payment Confirmation ≠ payment transaction/status.
- `BARFARABARAN_REFERENCE` remains outside DocumentDefinition until domain identity/cardinality/lifecycle are proven.

## Package-readiness note

ADR-036 architecture may proceed with deferred rows excluded. Initial governed package generation may contain fewer than 68 definitions after renames, removals, and deferrals. This file is the lineage authority for Stage 1 of the controlled multi-step catalog goal.
