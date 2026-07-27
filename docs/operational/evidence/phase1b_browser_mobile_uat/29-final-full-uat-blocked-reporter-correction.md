# Final full UAT blocker: Reporter correction authorization

- Date: 2026-07-26
- Workflow: Reporter permission matrix / milestone lifecycle
- Viewport: 1440 x 900
- Role: `phase1b_uat_reporter`
- Expected: Reporter can report milestone events but cannot correct verified
  milestones.
- Actual: Six active `Correct` controls were rendered. Submitting a synthetic
  correction succeeded and displayed `Milestone corrected.`
- Database evidence: the Reporter membership did not contain
  `milestone.correct`; nevertheless a new `milestone_event` row with
  `event_type=corrected`, `actor_user_id=3`, and a matching
  `checkpoint.milestone_corrected` audit row were committed.
- Mutation count: 1 unauthorized privileged mutation.
- Root-cause evidence: the correction UI in
  `OperationalShipmentDetail.tsx` is guarded by `checkpoint.report`.
- Console: zero errors, zero duplicate-key warnings, zero unhandled promises;
  React Router future warnings only.
- Sanitization: PASS. All identities and data are synthetic. No password,
  token, cookie, authorization header, DSN, or real customer data is present.
- Status: `OPEN_HIGH`

The gate stopped immediately. No product or harness fix was made.
