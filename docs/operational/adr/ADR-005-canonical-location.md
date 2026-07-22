# ADR-005: Canonical Location و Snapshot تاریخی

- Status: Accepted

## Context

Repository چند مدل مکان داخلی/بین‌المللی، بندر، گمرک و tracking reference دارد. ادغام فوری آن‌ها پرریسک است.

## Decision

یک abstraction `CanonicalLocation` هویت پایدار و type/source identity فراهم می‌کند و به رکوردهای موجود bridge می‌زند. RouteLeg و MilestoneEvent هم FK و هم `LocationSnapshot` immutable نگه می‌دارند. free text با `manual_unverified` مشخص می‌شود.

## Consequences

اصلاح master تاریخچه را بازنویسی نمی‌کند و migration additive می‌ماند. deduplication، source governance، timezone/geocode و code mapping نیازمند تأیید است.

## Rejected

ادغام/حذف همه جداول location در Phase 1 و ذخیره صرف free text یا صرف FK mutable.
