# ADR-004: مدل RouteLeg و Milestone

- Status: Accepted

## Decision

هسته `OperationalShipment → RoutePlan → RouteLeg → Milestone` است. RouteLeg segment ترتیبی برنامه بین دو مکان است؛ Milestone نقطه کنترل planned/actual است؛ `MilestoneEvent` شاهد append-only actual/verification است.

## Invariants

یک baseline plan فعال، sequence یکتا، plan منتشرشده immutable، زمان معتبر و completion مشروط به milestoneهای required و verified.

## Consequences

plan از fact جدا می‌شود و multimodal/revision ممکن است. مدل نسبت به status ساده پیچیده‌تر، اما ممیزی‌پذیر است.

## Rejected

timeline صرفاً مشتق از ShipmentRequest.status و یک status واحد برای leg/milestone/event.
