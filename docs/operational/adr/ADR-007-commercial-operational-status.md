# ADR-007: جداسازی Status تجاری و عملیاتی

- Status: Accepted

## Decision

`ShipmentRequest.status` فقط وضعیت تجاری را نگه می‌دارد. `OperationalShipment.lifecycle_status`، `RouteLeg.status`، verification state milestone و `ExceptionCase.status` مستقل‌اند. delayed/overdue/at-risk condition مشتق‌اند.

## Consequences

گزارش و permission معنای روشن دارند. compatibility layer می‌تواند summary نشان دهد، اما write status عملیاتی روی request ممنوع است.

## Rejected

افزودن booked/departed/arrived/delivered به ShipmentRequest.status یا استنتاج execution از won.
