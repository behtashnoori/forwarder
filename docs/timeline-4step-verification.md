# 4-Step Customer Timeline — Verification

This document describes how to verify the 4-step customer timeline (`workflow_steps_simple`) manually and how it behaves in each scenario.

## API

- **Public tracking:** `GET /api/public/track/<identifier>` — returns both `workflow_steps` (legacy 7-step) and `workflow_steps_simple` (4-step).
- **Customer workflow:** `GET /api/customer/workflow/<customer_id>?request_id=<id>` — returns both `workflow_steps` (legacy 8-step) and `workflow_steps_simple` (4-step).

## 4-Step Schema

Each step in `workflow_steps_simple` has:

- `name` — step key: `request_submitted`, `expert_assigned`, `in_progress`, `final_decision`
- `order` — 1–4
- `title` — Persian label (step 4 is dynamic)
- `is_completed` — boolean
- `completed_at` — ISO date string or `null`
- `meta` (optional) — e.g. `{"warning": "closed_without_decision"}` for step 4 when request is closed without a won/lost decision

## Verification Scenarios

### 1. Request with status `in_progress`

**Expectation:** Steps 1–3 completed, step 4 pending.

**Example response snippet:**

```json
"workflow_steps_simple": [
  { "name": "request_submitted", "order": 1, "title": "ارسال درخواست", "is_completed": true, "completed_at": "2025-02-23T12:00:00" },
  { "name": "expert_assigned", "order": 2, "title": "اختصاص کارشناس", "is_completed": true, "completed_at": "..." },
  { "name": "in_progress", "order": 3, "title": "در حال پیگیری", "is_completed": true, "completed_at": "..." },
  { "name": "final_decision", "order": 4, "title": "پذیرش / عدم پذیرش", "is_completed": false, "completed_at": null }
]
```

### 2. Request with status `won`

**Expectation:** Step 4 completed with title `"پذیرش مشتری"` and a non-null `completed_at`.

**Example response snippet:**

```json
{ "name": "final_decision", "order": 4, "title": "پذیرش مشتری", "is_completed": true, "completed_at": "2025-02-23T14:00:00" }
```

### 3. Request with status `lost`

**Expectation:** Step 4 completed with title `"عدم پذیرش مشتری"` and a non-null `completed_at`.

**Example response snippet:**

```json
{ "name": "final_decision", "order": 4, "title": "عدم پذیرش مشتری", "is_completed": true, "completed_at": "2025-02-23T14:00:00" }
```

### 4. Request with status `closed` and no won/lost in history

**Expectation:** Step 4 pending, title `"پذیرش / عدم پذیرش"`, and `meta.warning` set to `"closed_without_decision"`.

**Example response snippet:**

```json
{ "name": "final_decision", "order": 4, "title": "پذیرش / عدم پذیرش", "is_completed": false, "completed_at": null, "meta": { "warning": "closed_without_decision" } }
```

### 5. Request with status `closed` but a prior status_change to `won` (or `lost`)

**Expectation:** Step 4 completed with title `"پذیرش مشتری"` (or `"عدم پذیرش مشتری"`) and `completed_at` from the last won/lost log entry.

**How to create:** In expert console, set the request to `won` or `lost`, then set it to `closed`. The 4-step timeline uses `ExpertConsoleLog` to find the last `status_change` with `new_status` in `won`/`lost` and uses that for step 4.

## Automated Tests

Run the unit tests:

```bash
cd forwarder
python -m pytest backend/tests/test_public_tracking_timeline.py -v
```

These tests cover all of the scenarios above (in_progress, won, lost, closed without decision, closed with prior won/lost, and that the public tracking response includes `workflow_steps_simple`).

## Frontend

- **Public tracking page** uses `workflow_steps_simple` when present (fallback: `workflow_steps`), renders exactly 4 steps, and shows an optional “وضعیت فعلی” label from `status`.
- **Customer request detail page** does the same and shows the optional status label.

No database data is removed or reset; this is a presentation/mapping change only.
