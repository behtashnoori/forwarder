# Shipment Guidance — Read-only State Matrix Audit

This audit was completed before implementation changes. It applies existing
domain authorities: stages express Operational Progress, the active closure
policy determines blockers versus warnings, and command authorization controls
action visibility. `R` means required, `W` warning-only, and `I` informational.

| Case | Facts | Current state / process | Tasks | Attention / blockers / warnings | Readiness | Primary next action | Secondary actions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | No Route | planned / prerequisite blocked | Route R needs action; later work unavailable | BLOCKER: active route absent | progress 0; case not ready | تعریف مسیر عملیاتی | warning-only enrichment, if any |
| B | Route, no Execution | planned / prerequisite blocked | Route done; Execution R needs action | BLOCKER: execution absent | progress 0; case not ready | تکمیل اجرای حمل | warning-only enrichment |
| C | Execution, allocation incomplete | planned / Stage 1 available | Route/Execution done; allocation W; Stage R available | WARNING: allocation incomplete/differs; no allocation blocker | stage progress 0/N; case not ready | شروع مرحله اول | تکمیل تخصیص کالا |
| D | Stage 1 not started | planned / next required lifecycle | Stage R needs action | NEEDS ACTION: Stage 1 | stage progress 0/N; case not ready | شروع مرحله اول | warnings only after required action |
| E | Stage 1 STARTED | planned / current required work | Stage R in progress | NEEDS ACTION: incomplete started stage | stage progress 0/N; case not ready | تکمیل مرحله اول | later lifecycle actions excluded |
| F | Stage 1 complete, Stage 2 available | planned / next required lifecycle | Stage R in progress | NEEDS ACTION: Stage 2 | stage progress 1/N; case not ready | شروع مرحله دوم | warnings only after required action |
| G | Middle required stage STARTED | planned / current required work | Stage R in progress | NEEDS ACTION: incomplete middle stage | stage progress K/N; case not ready | تکمیل مرحله جاری | later lifecycle actions excluded |
| H | All stages complete; no Final Delivery | planned / closure blocker | Stages done; Final Delivery R needs action | BLOCKER: `FINAL_DELIVERY_EXISTS`; W cargo/allocation/ETA remain visible | stage progress N/N; case not ready | ثبت تحویل نهایی | warning-only improvements |
| I | All stages complete; Final Delivery; Actual Cargo unknown | planned / closure evaluation | Delivery done; Cargo W | WARNING: `ACTUAL_CARGO_UNKNOWN` | stage progress N/N; case follows mandatory criteria | بررسی و بستن پرونده when all mandatory criteria pass | تکمیل واقعیت کالای حمل‌شده |
| J | All stages complete; Final Delivery; allocation mismatch | planned / closure evaluation | Delivery done; allocation W | WARNING: `ACTUAL_ALLOCATION_DIFFERS_FROM_PLANNED` | stage progress N/N; case follows mandatory criteria | بررسی و بستن پرونده when all mandatory criteria pass | اصلاح تخصیص واقعی |
| K | Required Document missing | planned / closure blocker | Documents R needs action | BLOCKER: `REQUIRED_DOCUMENTS_READY` | operational progress independent; case not ready | رفع سند اجباری | warnings only after blocker |
| L | Blocking operational issue open | planned / closure blocker | Issue-resolution R needs action | BLOCKER: `NO_BLOCKING_OPERATIONAL_ISSUE` | operational progress independent; case not ready | رفع مشکل عملیاتی مسدودکننده | warnings only after blocker |
| M | Structured progress missing / ETA unavailable | planned / lifecycle continues | Tracking W unless another authority makes it required | WARNING: `ETA_UNAVAILABLE`; missing update is not invented as blocker | operational progress unchanged; case follows mandatory criteria | required lifecycle/closure action, or closure review | ثبت موقعیت یا پیشرفت |
| N | Closure ready | planned / ready for closure review | All required tasks done; warnings may remain | No blockers; warnings remain visible | closure ready | بررسی و بستن پرونده | optional improvements |
| O | Shipment closed | closed / terminal | Required task state remains readable | INFORMATIONAL only; historical warnings may remain readable | closed | none | none |
| P | Unauthorized user | state remains readable / command unavailable | Task state readable within read authority | Categories remain factual; inaccessible details stay filtered | unchanged | none | none |

## Read-only implementation audit

The pre-change projection had four conflicting decision paths:

1. `_tasks` used legacy `ACTUAL_QUANTITY_KNOWN` and `ALL_CARGO_DELIVERED`
   criteria and separately inferred tracking readiness.
2. `_attention` used current closure-policy mandatory flags.
3. `_action` assigned independent section numbers and then inserted only the
   first attention blocker through another section-number map.
4. readiness counted task statuses produced by path 1 while closure readiness
   came from path 2.

Consequences:

- warning-only Actual Cargo and missing tracking could outrank mandatory Final
  Delivery;
- Delivery task state could disagree with the authoritative
  `FINAL_DELIVERY_EXISTS` blocker;
- the primary CTA could repeat requirement copy rather than an executable
  action;
- Attention rendered every item with the same amber treatment;
- “5 of 5 stages” and the independent task percentage lacked explicit
  Operational Progress / Case Readiness labels.

The correction must preserve domain semantics while making one classified
condition set feed Tasks, Attention, Case Readiness and Next Action.

## Required invariants

1. Started required stage precedes later work.
2. Missing Final Delivery after all required stages precedes warnings.
3. Warnings remain visible but do not block or outrank required work.
4. Closure-ready state recommends closure review before enrichment.
5. Closed Shipment has no operational CTA.
6. Unauthorized user has no inaccessible CTA.
7. Task impact, Attention category and Next Action agree on blocking versus warning-only meaning.
