# Human Walkthrough — Admin findings register

Date observed: 2026-09-27. Source: Product Owner Human Walkthrough. This is a
historical observation and remediation register; it does not convert the Human
Product Walkthrough into PASS. Final automated evidence and exact SHAs are
recorded separately after candidate freeze.

| Finding | Historical observation | Current remediation disposition |
| --- | --- | --- |
| `HW-UX-ADMIN-001` | Reference cards exposed English/technical descriptions as primary content. | Resolved in candidate: versioned Persian Product descriptions are primary; stable codes are under «جزئیات فنی». |
| `HW-UX-ADMIN-002` | UOM presentation lacked useful Persian grouping and practical explanations. | Resolved in candidate: Persian descriptions and count/weight/volume/length-distance group presentation; millimetre added without schema change. |
| `HW-ADMIN-PACKAGING-001` | No Product-owned Packaging baseline. | Resolved in candidate: nine versioned baseline definitions in Reference Catalog V1. |
| `HW-ADMIN-MEANS-001` | No Product-owned Transport Means baseline. | Resolved in candidate: four deliberately small baseline definitions, distinct from Request Transport Method. |
| `HW-ADMIN-EQUIPMENT-001` | No Product-owned Equipment/Load Unit baseline. | Resolved in candidate: road, rail, container and air ULD definitions, distinct from Means. |
| `HW-ADMIN-REASON-001` | Operational Reasons used English/technical administration language. | Resolved in candidate: Persian-first family and reason forms. |
| `HW-ADMIN-REASON-002` | Organization Admin had to enter an immutable reason code. | Resolved in candidate: the server creates UUID-backed stable codes; the UI does not request one. |
| `HW-ADMIN-SLA-001` | Tenant-entered free text appeared to define SLA semantics. | Resolved in candidate: Organization Admin selects a system-governed target and can add only an optional presentation alias. |
| `HW-ADMIN-LOGISTICS-001` | Organization Admin received an authorization failure on its own logistics network. | Resolved in candidate: same-tenant global adoption and private-point permissions are explicitly admitted; System-only and foreign operations remain denied. |
| `HW-UX-ADMIN-003` | A generic English authorization error appeared in normal Persian Admin UX. | Resolved in candidate: affected Admin surfaces map authorization/transport failures to bounded Persian messages. |

The observations above remain true historical facts even after remediation.
Their current status is `RESOLVED_IN_AUTOMATED_CANDIDATE`; the Product Owner's
manual confirmation remains `HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS`.
