# ADR-006: مهاجرت Additive و Backward-Compatible

- Status: Accepted

## Decision

الگوی expand → migrate → verify → switch → contract اجرا می‌شود. ابتدا table/FK/index جدید، سپس backfill idempotent و shadow read، بعد cohort write/read. حذف legacy فقط پس از deprecation gate است.

## Controls

dry-run، checkpoint، quarantine، data gate، feature flag، rollback routing، N/N-1 compatibility و migration job مستقل از startup.

## Consequences

rollout طولانی‌تر ولی کم‌ریسک و برگشت‌پذیر است. dual write مستقل ممنوع؛ write aggregate/outbox اتمیک است.

## Rejected

big-bang migration، startup migration/seed و بازنویسی status یا داده legacy.
