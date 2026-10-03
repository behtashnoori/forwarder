# Structured ETA progress and visual hierarchy qualification

Date: 2026-10-03  
Entry canonical: `b0e82ba825536d33188b3b85318ec9851f452a67`  
Product implementation: `8e71060d6d806f9612c09fa78ae1eeacbb52bbc1`  
Schema: `20261017_document_type_ownership` (one head)  
Migration required: NO

## Product result

`HW_ETA_PROGRESS_ENTRY_001` is resolved by exposing the existing immutable
`PROGRESS` / `DISTANCE_REMAINING_KM` reported fact in Shipment → Tracking & ETA
→ `پیشرفت مسیر`. The form uses the same command, exact active plan/leg/stage
execution and pinned basis validation, occurred-at semantics, actor/source and
append-only correction history as the pre-existing generic report path. No
second progress model or ETA engine was created.

Once an authoritative Arrival exists for the leg, a new progress command is
denied. This mission grants no historical-repair authority, so a retroactive
occurred-at value does not bypass that guard. Zero remaining distance remains a
structured observation: it does not create Arrival and the unchanged ruleset
retains any stop before a later movement.

`HW_VISUAL_HIERARCHY_001` is resolved with the existing shared UI library. The
active navigation surface is light blue with dark-blue text and a two-pixel
indicator, shared page/section/subsection levels stay within the requested
24–28 / 18–20 / 16 px scale, form groups and entity cards use restrained
neutral surfaces, and primary/success CTAs use solid semantic colors. The
Vazirmatn family, Product information architecture, user actions and semantic
status meanings are unchanged.

## ETA numerical proof

The PostgreSQL 18 qualification selects an immutable 900 km basis whose
movement interval is 720–960 minutes. A valid latest progress fact reports
450 km remaining.

```
remaining fraction = 450 / 900 = 0.5
earliest movement   = 720 × 0.5 = 360 minutes = 6 hours
latest movement     = 960 × 0.5 = 480 minutes = 8 hours
```

The current-leg arrival estimate excludes the target arrival stop under the
documented `ARRIVAL_POINT_BEFORE_NEXT_MOVEMENT` rule. The unchanged
`ETA_RULESET_V2` returned occurrence time +6 h to +8 h.

## Required ETA cases

| Case | Result and evidence |
|---|---|
| E1 — no progress | PASS — PostgreSQL returns `PROGRESS_UNDEFINED`; text location never qualifies as distance. |
| E2 — 900 / 450 | PASS — PostgreSQL returns +6 h / +8 h using `ETA_RULESET_V2`. |
| E3 — zero remaining | PASS — accepted as a destination-node observation, does not create Arrival, and retains the next-leg stop. |
| E4 — distance greater than basis | PASS — command rejects `900.001`; negative values also reject. |
| E5 — multiple facts | PASS — newest applicable fact drives ETA and both immutable rows remain. |
| E6 — wrong leg/execution | PASS — nonexistent stage rejects; an old-plan stage rejects after replan. |
| E7 — partial cargo coverage | PASS — PostgreSQL reports `PROGRESS_AMBIGUOUS` rather than a whole-cargo ETA. |
| E8 — arrived | PASS — final ETA is `DESTINATION_REACHED`; a new in-transit progress command is denied once Arrival exists. |
| E9 — tenant/role | PASS — owner command succeeds; outsider, peer platform user and changed owner fail closed. |
| E10 — history | PASS — A→B→A corrections remain append-only; PostgreSQL update/delete triggers enforce immutability; Persian UI shows occurrence, recorded time and actor. |

## Automated checks

| Check | Result |
|---|---|
| Focused backend reported-fact/ETA | PASS — 30 tests |
| Disposable PostgreSQL 18 base→head and ETA matrix | PASS — 1 comprehensive test; server major 18; source rows preserved; migration round-trip and guards pass |
| Full frontend | PASS — 111 files / 529 tests |
| Focused frontend rerun | PASS — 5 files / 38 tests |
| TypeScript | PASS — `tsc --noEmit` |
| Production build | PASS — Vite build; only the established chunk-size advisory |
| ESLint | PASS — 0 errors; 16 pre-existing warnings |
| Structure | PASS |
| Diff hygiene | PASS — `git diff --check` |

## Browser and visual evidence

Chrome exercised the baseline at the exact entry SHA and the candidate against
the same disposable clone of the preserved PostgreSQL database. No business
submit, ETA calculate/save or Arrival action was clicked. Baseline evidence
confirms that the dedicated entry was absent. Candidate evidence confirms:

- the `پیشرفت مسیر` section and `ثبت فاصله باقی‌مانده` form are visible;
- the numerical input, kilometre unit and occurred-at control are present;
- the raw enum name is absent;
- Tracking & ETA exposes `aria-current=page` and the visible non-color active indicator;
- Summary, Route, Cargo, Tracking, Expert Request/Quote, Admin and Customer
  Request pages render at 1440 px;
- Tracking renders at 390 px with RTL preserved and no horizontal overflow.

The paired PNGs are under `screenshots/`; hashes are recorded in
`SCREENSHOT-SHA256.txt`. `browser-baseline-result.json` and
`browser-candidate-result.json` preserve machine assertions.

## Preservation boundary

Before integration, a read-only query of the preserved runtime recorded:
Actual Cargo 100, pinned basis 900 km, one Execution, Planned Allocation 100,
Actual Allocation 100, one Departure, zero Arrival, zero structured progress
and zero ETA snapshots. The post-integration comparison is intentionally
written to the external runtime handoff receipt after this evidence commit so
the evidence commit can also be the final canonical identity. Human Product
Walkthrough remains `IN_PROGRESS`; `RELEASE_READY=NO`.

