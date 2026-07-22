# ADR-010: Idempotency و Optimistic Locking

- Status: Accepted

## Decision

تمام create/conversion/event/transitionهای حساس `Idempotency-Key` و mutation aggregate `expected_version`/If-Match دارند. source/external identity constraint دیتابیس برقرار است. aggregate version با هر write افزایش می‌یابد.

## Behavior

key و payload یکسان همان response را replay می‌کند؛ key با payload متفاوت 409 است؛ version قدیمی 409 است. transaction، aggregate و outbox را اتمیک ثبت می‌کند.

## Consequences

retry امن و lost update کنترل می‌شود. storage/expiry idempotency record و UX conflict resolution نیازمند تأیید است.

## Rejected

last-write-wins، dedupe صرف application memory و retry بدون identity پایدار.
