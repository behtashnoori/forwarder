# ADR-008: برج کنترل مبتنی بر Work Queue

- Status: Accepted

## Decision

Control Tower یک read model و Work Queue رتبه‌بندی‌شده روی exception، SLA، overdue milestone و data freshness است. هر WorkItem type، severity، owner، due، state، source reference و commandهای claim/snooze/complete/dismiss دارد.

## Consequences

dashboard اقدام‌پذیر و قابل سنجش با MTTA/MTTR است. WorkItem منبع حقیقت event/milestone نیست و از projection قابل rebuild است. ranking/SLA thresholds نیازمند تأیید است.

## Rejected

dashboard صرفاً آماری، status رنگی بدون owner/action و ذخیره حقیقت حمل در queue.
