# Phase 0 State Transition Matrix

تمام transitionها command-based، permission-checked، version-checked و audit-recorded هستند. `ShipmentRequest.status` ماتریس تجاری موجود را حفظ می‌کند و در این سند برای اجرای حمل توسعه نمی‌یابد.

## OperationalShipment

| From | Command | To | Guard | Side effect قراردادی |
|---|---|---|---|---|
| — | CreateFromAcceptedQuote | planned | quote eligible، idempotency unique | lineage + outbox |
| planned | SubmitBooking | booking_pending | plan baseline، owner | event |
| booking_pending | ConfirmBooking | booked | booking reference | event |
| booked | StartExecution | in_execution | required start milestone/evidence | event/work queue refresh |
| in_execution | PutOnHold | on_hold | reason، permission | exception/work item |
| on_hold | ResumeExecution | in_execution | blocker resolved/override | audit/event |
| in_execution | CompleteShipment | completed | all required milestones verified، blocker صفر | completion event |
| planned/booking_pending/booked | CancelShipment | cancelled | reason، no prohibited dependency | cancellation event |
| in_execution/on_hold | CancelShipment | cancelled | elevated permission + reason | exception/audit |

Terminal: `completed`, `cancelled`. Reopen فقط ADR/command آینده؛ در MVP مجاز نیست.

## RouteLeg

| From | Command | To | Guard |
|---|---|---|---|
| planned | MarkReady | ready | plan published، required preconditions |
| ready | RecordDeparture | departed | verified departure MilestoneEvent |
| departed | RecordArrival | arrived | verified arrival MilestoneEvent |
| arrived | CompleteLeg | completed | required leg milestones verified |
| planned/ready | CancelLeg | cancelled | plan revision/permission/reason |
| ready/departed | BlockLeg | blocked | open blocker exception |
| blocked | UnblockLeg | prior active state | blocker resolved، audit |

## Milestone verification state

| From | Event/Command | To | Guard |
|---|---|---|---|
| planned | DueTimeReached | due | actual ندارد |
| planned/due | SubmitMilestoneEvent | reported | source/evidence معتبر شکلی |
| reported | VerifyMilestoneEvent | verified | verifier permission/policy |
| reported | RejectMilestoneEvent | rejected | reason |
| planned/due | WaiveMilestone | waived | elevated permission + reason |
| verified | CorrectMilestone | reported | correction event supersedes؛ actual پاک نشود |
| planned/due | CancelMilestone | cancelled | plan revision/reason |

`overdue` condition مشتق از due time و absence of verified event است؛ status lifecycle مستقل نیست.

## ExceptionCase

| From | Command | To | Guard |
|---|---|---|---|
| — | OpenException | open | rule/manual source + dedupe |
| open | Acknowledge | acknowledged | actor |
| acknowledged | StartInvestigation | investigating | owner |
| investigating | RequestAction | action_pending | action/due/assignee |
| action_pending/investigating | Resolve | resolved | resolution + evidence |
| resolved | Close | closed | verification/permission |
| resolved/closed | Reopen | open | new evidence/reason |

## WorkItem

| From | Command | To | Guard |
|---|---|---|---|
| open | Claim | assigned | assignee scope |
| open/assigned | Snooze | snoozed | until + reason؛ blocker policy |
| snoozed | Wake | open/assigned | due/event |
| assigned | CompleteAction | done | linked command outcome |
| any nonterminal | Dismiss | dismissed | policy + reason؛ source exception حذف نشود |

## Transition response contract

- success: aggregate id/version، state، emitted event ids؛
- stale version: `409 OPERATION_VERSION_CONFLICT`؛
- invalid state: `409 INVALID_STATE_TRANSITION`؛
- guard failure: `422 TRANSITION_GUARD_FAILED`؛
- forbidden: `403 OPERATION_FORBIDDEN`؛
- duplicate command: replay همان response ذخیره‌شده.

## شروط زمانی

همه زمان‌ها در storage UTC و در UI timezone-aware هستند. event خارج از ترتیب پذیرفته می‌شود، اما projection با `occurred_at`, `recorded_at` و precedence deterministic بازسازی می‌گردد. thresholdهای overdue **نیازمند تأیید** هستند.
