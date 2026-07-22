# ADR-002: جداسازی Request از Operation

- Status: Accepted

## Context

`ShipmentRequest` در مدل فعلی intake، route/cargo، assignment، quote linkage و tracking را حمل می‌کند. توسعه عملیات روی آن God aggregate می‌سازد.

## Decision

ShipmentRequest فقط چرخه تجاری است. اجرای حمل در aggregate مستقل `OperationalShipment` قرار می‌گیرد و lineage با request/accepted quote حفظ می‌شود. conversion command idempotent است.

## Consequences

status، permission و audit تجاری/عملیاتی مستقل می‌شوند. compatibility projection و migration additive لازم است. `won` صرفاً eligibility است، نه اجرای حمل.

## Rejected

افزودن leg/milestone/operational status به ShipmentRequest و rename کردن ShipmentRequest به shipment.
