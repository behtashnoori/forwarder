# Forwarder Document Catalog V1 — Review and Evidence Matrix

Status: FROZEN REVIEW PACKAGE — APPLY NOT AUTHORIZED

Package structure: one International Base package. An Iran extension is deferred until at least one Iran-specific definition has authoritative source confirmation.

Evidence sources used for included rows:

- UNECE/UN/CEFACT UN/EDIFACT Data Element 1001 (`https://unece.org/fileadmin/DAM/trade/edifact/code/1001cl.htm`)
- UNECE CMR Convention (`https://unece.org/fileadmin/DAM/trans/conventn/cmr_e.pdf`)
- IMO FAL declarations and certificates (`https://www.imo.org/en/ourwork/facilitation/pages/declarationscertificates-default.aspx`)

| # | Original Code | Canonical Code | Persian Name | English Name | Domain Decision | Evidence Status | V1 Disposition | Package | Lifecycle | Reason |
|---:|---|---|---|---|---|---|---|---|---|---|
| 1 | `COMMERCIAL_INVOICE` | `COMMERCIAL_INVOICE` | فاکتور تجاری | Commercial Invoice | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 2 | `PROFORMA_INVOICE` | `PROFORMA_INVOICE` | پیش‌فاکتور | Proforma Invoice | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 3 | `PACKING_LIST` | `PACKING_LIST` | فهرست بسته‌بندی / صورت عدلبندی | Packing List | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 4 | `PURCHASE_ORDER` | `PURCHASE_ORDER` | سفارش خرید | Purchase Order | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 5 | `CERTIFICATE_OF_ORIGIN` | `CERTIFICATE_OF_ORIGIN` | گواهی مبدأ | Certificate of Origin | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 6 | `PREFERENTIAL_CERTIFICATE_OF_ORIGIN` | `PREFERENTIAL_CERTIFICATE_OF_ORIGIN` | گواهی مبدأ ترجیحی | Preferential Certificate of Origin | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 7 | `BILL_OF_LADING` | `BILL_OF_LADING` | بارنامه دریایی | Bill of Lading | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 8 | `SEA_WAYBILL` | `SEA_WAYBILL` | راهنامه دریایی | Sea Waybill | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 9 | `HOUSE_BILL_OF_LADING` | `HOUSE_BILL_OF_LADING` | بارنامه فرعی دریایی | House Bill of Lading | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 10 | `MASTER_BILL_OF_LADING` | `MASTER_BILL_OF_LADING` | بارنامه مادر دریایی | Master Bill of Lading | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 11 | `AIR_WAYBILL` | `AIR_WAYBILL` | راهنامه هوایی | Air Waybill | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 12 | `HOUSE_AIR_WAYBILL` | `HOUSE_AIR_WAYBILL` | راهنامه هوایی فرعی | House Air Waybill | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 13 | `MASTER_AIR_WAYBILL` | `MASTER_AIR_WAYBILL` | راهنامه هوایی مادر | Master Air Waybill | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 14 | `CMR_CONSIGNMENT_NOTE` | `CMR_CONSIGNMENT_NOTE` | راهنامه جاده‌ای CMR | CMR Road Consignment Note | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 15 | `RAIL_CONSIGNMENT_NOTE` | `RAIL_CONSIGNMENT_NOTE` | راهنامه ریلی | Rail Consignment Note | KEEP_AS_FALLBACK | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 16 | `CIM_CONSIGNMENT_NOTE` | `CIM_CONSIGNMENT_NOTE` | راهنامه ریلی CIM | CIM Rail Consignment Note | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | The generic rail source does not establish the CIM-specific identity strongly enough. |
| 17 | `SMGS_CONSIGNMENT_NOTE` | `SMGS_CONSIGNMENT_NOTE` | راهنامه ریلی SMGS | SMGS Consignment Note | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 18 | `CIM_SMGS_CONSIGNMENT_NOTE` | `CIM_SMGS_CONSIGNMENT_NOTE` | راهنامه مشترک CIM/SMGS | CIM/SMGS Consignment Note | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 19 | `MULTIMODAL_TRANSPORT_DOCUMENT` | `MULTIMODAL_TRANSPORT_DOCUMENT` | سند حمل چندوجهی | Multimodal Transport Document | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 20 | `FIATA_FBL` | `FIATA_FBL` | بارنامه حمل چندوجهی فیاتا | FIATA Multimodal Transport Bill of Lading | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 21 | `FIATA_FWB` | `FIATA_FWB` | راهنامه حمل چندوجهی فیاتا | FIATA Multimodal Transport Waybill | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 22 | `FIATA_FCR` | `FIATA_FCR` | گواهی دریافت فورواردر فیاتا | FIATA Forwarders Certificate of Receipt | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 23 | `FIATA_FCT` | `FIATA_FCT` | گواهی حمل فورواردر فیاتا | FIATA Forwarders Certificate of Transport | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 24 | `FIATA_FWR` | `FIATA_FWR` | قبض انبار فیاتا | FIATA Warehouse Receipt | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 25 | `WAREHOUSE_RECEIPT` | `WAREHOUSE_RECEIPT` | قبض انبار | Warehouse Receipt | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 26 | `DELIVERY_ORDER` | `DELIVERY_ORDER` | دستور تحویل | Delivery Order | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 27 | `ARRIVAL_NOTICE` | `ARRIVAL_NOTICE` | اعلامیه ورود | Arrival Notice | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 28 | `BOOKING_CONFIRMATION` | `BOOKING_CONFIRMATION` | تأییدیه رزرو حمل | Booking Confirmation | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 29 | `SHIPPING_INSTRUCTION` | `SHIPPING_INSTRUCTION` | دستور حمل | Shipping Instruction | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 30 | `CARGO_MANIFEST` | `CARGO_MANIFEST` | مانیفست بار | Cargo Manifest | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 31 | `FREIGHT_MANIFEST` | `FREIGHT_MANIFEST` | مانیفست کرایه | Freight Manifest | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 32 | `CONTAINER_MANIFEST` | `CONTAINER_MANIFEST` | مانیفست کانتینر | Container Manifest | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 33 | `AIR_CARGO_MANIFEST` | `AIR_CARGO_MANIFEST` | مانیفست بار هوایی | Air Cargo Manifest | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 34 | `SEA_CARGO_DECLARATION` | `SEA_CARGO_DECLARATION` | اظهارنامه بار دریایی | Sea Cargo Declaration | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 35 | `DANGEROUS_GOODS_DECLARATION` | `DANGEROUS_GOODS_DECLARATION` | اظهارنامه کالای خطرناک | Dangerous Goods Declaration | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 36 | `DANGEROUS_GOODS_MANIFEST` | `DANGEROUS_GOODS_MANIFEST` | مانیفست کالای خطرناک | Dangerous Goods Manifest | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 37 | `CUSTOMS_DECLARATION` | `CUSTOMS_DECLARATION` | اظهارنامه گمرکی | Customs Declaration | KEEP_AS_FALLBACK | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 38 | `IMPORT_CUSTOMS_DECLARATION` | `IMPORT_CUSTOMS_DECLARATION` | اظهارنامه واردات | Import Customs Declaration | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 39 | `EXPORT_CUSTOMS_DECLARATION` | `EXPORT_CUSTOMS_DECLARATION` | اظهارنامه صادرات | Export Customs Declaration | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 40 | `TRANSIT_DECLARATION` | `TRANSIT_DECLARATION` | اظهارنامه ترانزیت | Transit Declaration | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 41 | `TIR_CARNET` | `TIR_CARNET` | کارنه تیر | TIR Carnet | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 42 | `ATA_CARNET` | `ATA_CARNET` | کارنه آ.ت.آ | ATA Carnet | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 43 | `IMPORT_LICENSE` | `IMPORT_LICENSE` | مجوز واردات | Import Licence | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 44 | `EXPORT_LICENSE` | `EXPORT_LICENSE` | مجوز صادرات | Export Licence | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 45 | `REGISTRATION_ORDER` | `REGISTRATION_ORDER` | ثبت سفارش | Registration Order | HYBRID_CONFIRMED | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 46 | `STATISTICAL_REGISTRATION` | `STATISTICAL_REGISTRATION` | ثبت آماری | Statistical Registration | HYBRID_CONFIRMED | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 47 | `CUSTOMS_RELEASE_PERMIT` | `CUSTOMS_RELEASE_PERMIT` | پروانه گمرکی / پروانه سبز | Customs Release Permit | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 48 | `WAREHOUSE_RELEASE` | `IRAN_CARRIER_RELEASE` | ترخیصیه | Warehouse Release | RENAME | SOURCE_CONFIRMATION_REQUIRED | RENAME | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 49 | `DOMESTIC_WAYBILL` | `DOMESTIC_WAYBILL` | بارنامه داخلی | Domestic Waybill | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 50 | `INSURANCE_CERTIFICATE` | `INSURANCE_CERTIFICATE` | گواهی بیمه | Insurance Certificate | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 51 | `INSURANCE_POLICY` | `INSURANCE_POLICY` | بیمه‌نامه باربری | Cargo Insurance Policy | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 52 | `INSPECTION_CERTIFICATE` | `INSPECTION_CERTIFICATE` | گواهی بازرسی | Inspection Certificate | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 53 | `QUALITY_CERTIFICATE` | `QUALITY_CERTIFICATE` | گواهی کیفیت | Certificate of Quality | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 54 | `CERTIFICATE_OF_CONFORMITY` | `CERTIFICATE_OF_CONFORMITY` | گواهی انطباق | Certificate of Conformity | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 55 | `PHYTOSANITARY_CERTIFICATE` | `PHYTOSANITARY_CERTIFICATE` | گواهی بهداشت نباتی | Phytosanitary Certificate | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 56 | `VETERINARY_CERTIFICATE` | `VETERINARY_CERTIFICATE` | گواهی دامپزشکی | Veterinary Certificate | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 57 | `SANITARY_CERTIFICATE` | `SANITARY_CERTIFICATE` | گواهی بهداشتی | Sanitary Certificate | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 58 | `QUARANTINE_CERTIFICATE` | `QUARANTINE_CERTIFICATE` | گواهی قرنطینه | Quarantine Certificate | REMOVE | EXCLUDED_BY_DOMAIN_DECISION | REMOVE | — | — | Excluded by the certified Domain Resolution baseline and ADR-036. |
| 59 | `WEIGHT_CERTIFICATE` | `WEIGHT_CERTIFICATE` | گواهی وزن | Weight Certificate | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 60 | `FREIGHT_INVOICE` | `FREIGHT_INVOICE` | صورتحساب کرایه حمل | Freight Invoice | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 61 | `LETTER_OF_CREDIT` | `LETTER_OF_CREDIT` | اعتبار اسنادی | Letter of Credit | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 62 | `BILL_OF_EXCHANGE` | `BILL_OF_EXCHANGE` | برات | Bill of Exchange | KEEP | SOURCE_CONFIRMED | INCLUDE_SOURCE_CONFIRMED | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |
| 63 | `PAYMENT_CONFIRMATION` | `PAYMENT_CONFIRMATION` | تأییدیه پرداخت | Payment Confirmation | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 64 | `BANKING_IMPORT_DOCUMENT` | `BANKING_IMPORT_DOCUMENT` | سند بانکی واردات | Import Banking Document | SPLIT_REMOVE_GENERIC | EXCLUDED_BY_DOMAIN_DECISION | REMOVE | — | — | Excluded by the certified Domain Resolution baseline and ADR-036. |
| 65 | `GATE_PASS` | `GATE_PASS` | مجوز خروج | Gate Pass | DEFER | DOMAIN_CONFIRMATION_REQUIRED | DEFER | — | — | Durable managed artifact identity is not yet proven. |
| 66 | `RELEASE_ORDER` | `CONTAINER_RELEASE_ORDER` | مجوز آزادسازی | Release Order | RENAME | SOURCE_CONFIRMATION_REQUIRED | RENAME | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 67 | `RECEIPT_ADVICE` | `RECEIPT_ADVICE` | اعلام دریافت کالا | Receipt Advice | KEEP | SOURCE_CONFIRMATION_REQUIRED | DEFER | — | — | Exact authoritative evidence for this canonical specificity was not established in the bounded review. |
| 68 | `DELIVERY_NOTICE` | `GOODS_DELIVERY_NOTICE` | اعلام تحویل کالا | Delivery Notice | RENAME | SOURCE_CONFIRMED | RENAME | International Base | SOURCE_CONFIRMED | Named authoritative international source confirms the document type. |

## Frozen counts

- Original candidates: 68
- Canonical candidates after Domain Resolution: 65
- Included source-confirmed definitions: 46
- Included reviewed/non-active definitions: 0
- Deferred original candidates: 20
- Removed generic/umbrella candidates: 2
- Renamed candidates: 3
- Merged candidates: 0

Catalog presence and lifecycle do not create document requirements, uploaded files, associations, workflow states, or external-reference ownership.
