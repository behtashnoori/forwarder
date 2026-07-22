# ADR-001: حفظ Modular Monolith

- Status: Accepted
- Date: 2026-07-22

## Context

سامانه فعلی Flask/SQLAlchemy یک deployable و database مشترک با blueprint/serviceهای قابل تفکیک دارد. شواهد scale یا team autonomy برای microservice وجود ندارد.

## Decision

معماری هدف Modular Monolith با bounded moduleهای Commercial، Execution، Visibility، Control Tower و Platform است. مالکیت table/service و import rule صریح می‌شود؛ write بین ماژولی فقط از application contract.

## Consequences

transaction و rollout ساده می‌ماند و extraction آینده با outbox seam ممکن است. discipline مرزبندی و architecture test لازم است. استخراج سرویس بدون ADR و evidence ممنوع است.

## Rejected

microservice فوری، ادامه monolith بدون boundary و shared utilityهای دارای business write.
