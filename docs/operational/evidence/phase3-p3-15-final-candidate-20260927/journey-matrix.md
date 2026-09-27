# P3-15 current critical-journey matrix

All rows are current candidate-bound automated results. Historical Slice
evidence is context only and was not used as a substitute for these executions.

| Journey | Result | Current proof |
| --- | --- | --- |
| `FWD-J01` anonymous intake and public tracking | PASS | `automated-final/P315-CORE/browser.log`, `automated-final/MT3/browser.log` |
| `FWD-J02` authenticated customer request and Quote | PASS | `automated-final/IPJ01/browser.log`, `automated-final/IPJ02-IPJ03/browser.log` |
| `FWD-J03` commercial handoff to operations | PASS | `automated-final/IPJ01/browser.log` |
| `FWD-J04` Expert daily Workspace | PASS | `automated-final/IPJ02-IPJ03/browser.log`, `automated-final/IPJ02-IPJ03-PHASE2/browser.log` |
| `FWD-J05` operational problem and follow-up | PASS | `automated-final/IPJ02-IPJ03-PHASE2/browser.log` |
| `FWD-J06` Organization administration | PASS | `automated-final/P314/browser.log`, `automated-final/IPJ02-IPJ03-PHASE2/browser.log` |
| `FWD-J07` Control Tower | PASS | `automated-final/P314/browser.log`, `automated-final/IPJ02-IPJ03-MONITORING/browser.log` |
| `FWD-J08` tenant and authorization protection | PASS | `automated-final/P309/browser.log`, `automated-final/P313/browser.log`, `automated-final/MT3/browser.log`, security matrix |
| `FWD-J09` shared multi-Customer/multi-Cargo Shipment | PASS | `P301..P314` current slices plus `ipj04-final/IPJ04/` |
| `FWD-IPJ-01` need/Quote to Operational Shipment | PASS | `IPJ01`: Customer accepts Quote in normal UI; Expert creates Shipment; fixed-owner and foreign/direct negatives persist |
| `FWD-IPJ-02` active Shipment to operational resolution | PASS | `IPJ02-IPJ03-PHASE2`: Workspace, Shipment, Exception, Action, follow-up, evaluator, Tower, resolution and history |
| `FWD-IPJ-03` Organization administration and tenant isolation | PASS | Admin normal navigation in `P314`; account/session, SLA, A/B tenant and direct-negative proofs in `IPJ02-IPJ03*`, `P309`, `P315-CORE` and security matrix |
| `FWD-IPJ-04` shared Shipment from assembly to closure | PASS | `ipj04-final`: real owner transfer followed on the same owned fixture by route/execution/allocation, correction, documents, partial delivery history, available ETA, A/B privacy, closure, refresh and post-close denial |

## Continuity and state

`FWD-IPJ-04` uses one owned PostgreSQL database across two browser chapters.
The first chapter performs the real owner-transfer command. The bounded setup
then uses Product services for route-time selection and reported-fact correction
and establishes the documented `completed` closure precondition. The second
chapter navigates the same Shipment, materializes ETA, verifies Customer A/B
privacy, creates the closure policy through normal Admin navigation, closes as
the new owner, reopens, and proves old-owner and post-closure denial.

No transfer, correction, ETA or closure history is manufactured directly in
the database. The direct `completed` fixture state is explicitly recorded as a
starting-state prerequisite because Phase 3 defines no separate completion
command in this slice.

```text
FWD_J01=PASS
FWD_J02=PASS
FWD_J03=PASS
FWD_J04=PASS
FWD_J05=PASS
FWD_J06=PASS
FWD_J07=PASS
FWD_J08=PASS
FWD_J09=PASS
FWD_IPJ_01=PASS
FWD_IPJ_02=PASS
FWD_IPJ_03=PASS
FWD_IPJ_04=PASS
```
