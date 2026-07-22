# ADR-009: Verification مبتنی بر MilestoneEvent

- Status: Accepted

## Decision

actual milestone فقط از `MilestoneEvent` گزارش‌شده و طبق policy verified حاصل می‌شود. event append-only است و actor/source، occurred/recorded time، location snapshot، evidence و dedupe identity دارد. correction با event جدید و supersedes انجام می‌شود.

## Consequences

audit و provenance کامل و out-of-order reconciliation ممکن است. برای منابع trusted می‌توان auto-verification policy داشت؛ authority و evidence catalog نیازمند تأیید است.

## Rejected

ویرایش مستقیم actual، حذف رخداد اشتباه و اعتماد یکسان به manual/partner/system source.
