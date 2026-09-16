# FWD-06 final controlled local delivery

Recorded 2026-09-16, Asia/Tehran. Product candidate C2 is committed HEAD `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`. Native PostgreSQL and live browser qualification below ran against this clean committed candidate. This evidence-only follow-up changes no runtime code. Its own final Git identity is supplied in the delivery response and Git log; the product sync snapshot below was fetched before this report was added.

| Final report field | Result |
| --- | --- |
| MISSION_RESULT | PASS_CONTROLLED_LOCAL_FWD06 |
| M1_STATUS | Exact proposed text accepted by the Owner's supplied continuation; acceptance/lifecycle recorded, proposal preserved unchanged. Local development and qualification only. |
| ACCEPTED_PROPOSAL_SHA256 | `6792ADD2CC064A73977386D62263EDA13A0C534CE5A7E118679A1422CD55673A` |
| CURRENT_M1_AND_ADR_HASHES | Acceptance `7F9BD718AFF81FE8D040E123A86FC2B357AFB3D76DFA5E7BC51306E0985D4EED`; current ADR-048 `7E7F6F76AB108D77646C2CF6DA15DDB118911C9DE837684FF369041C3FC6E021`. All changed decision/evidence documents are listed in M1-HASH-REGISTER.md (register excludes itself). |
| MANUAL_TIME_POLICY | `tracking.manual-iran.v1`, Gregorian-normalized local wall, server-owned `Asia/Tehran`, blank occurrence inputs, shared Persian/Gregorian date selection; invalid date, missing policy, gaps/overlaps, conflicts and forged basis rejected. |
| MACHINE_SOURCE_BOUNDARY | Existing authenticated expert offset-bearing API contract retained, source literal `offset`, original wall/numeric offset stored, NULL manual policy. Payload flags do not confer authority and are rejected. No new machine principal, Agent, foreign-zone manual selector or authority introduced. |
| FIVE_FIELD_PERSISTENCE | Exactly five approved nullable event columns; complete manual/offset envelopes; direct-service revalidation, PostgreSQL shape/precision/consistency guards and populated-snapshot immutability. Event, derived mirror and keyed receipt commit atomically. |
| LEGACY_HISTORY_AND_MIRROR | No default, backfill or historical conversion. Historical raw values/relationships and five NULLs verified unchanged. Historical occurrence displays unknown after valid occurrences; created_at alone uses proven-legacy-UTC. New occurred_at mirror is derived UTC-naive and immutable with its snapshot. |
| MIGRATION_AND_RECOVERY | Sole predecessor `20260916_fwd05_quote_response`; sole new head `20260916_fwd06_tracking_time`. Upgrade, empty downgrade/re-upgrade, populated downgrade refusal before DDL verified. Actual pre-M1 application reads retained schema in DB-enforced read-only mode; old writes stop. Reinstantiated new app retains snapshot/mirror and replays retained receipt. No old-write compatibility claim. |
| TRACKING_FORM_AND_TIMELINE | Existing four subject types, internal code/DB identity/optional physical identity clarified; duplicate Persian error retains inputs. Authorized internal history separate from visible status/location scope; occurrence/recording distinct; late events do not regress current status; stable owner tie-breaker retained. Original first-add error remains NOT_REPRODUCED_ON_THIS_BASELINE. |
| PUBLIC_ALLOWLIST | Visible active-unit query and global visible last_recorded_at; no hidden event leakage to timeline/summary/count. Public projection excludes provenance, actor, tenant, receipt, internal notes and private catalog identity. No internal ID newly published. |
| IDEMPOTENCY_AND_AUTHORIZATION | Root lock, tenant/operation/resource/key/payload-bound receipt; same-key race yields 201/200 and one append, changed payload 409. Fresh root/unit, membership/tenant/assignment authorization and eligibility/enabled/active checks before replay. Geography/FWD-02 resolution retained. No-key compatibility has no replay guarantee. |
| POSTGRESQL_TESTS | Exact C2 native run: 1 PASS, 32 warnings, no SKIP/XFAIL, 16.52s. Owned synthetic loopback cluster stopped; diagnostics `C:/Users/pc/AppData/Local/Temp/forwarder-fwd05-qualification-77a585e433db40b6bf946843ec78f22c`. |
| BROWSER_UAT | Exact C2 live run: 21 PASS, real backend/official synthetic fixture, real login/assignment/eligibility transition, UTC and America/New_York same Tehran instant, Persian/Gregorian round trip, create/duplicate/save/reopen, ordinary expert and customer RTL desktop/mobile. JSON/screenshots `C:/Users/pc/AppData/Local/Temp/forwarder-fwd06-browser-e849c7e0974741e68dbdc8b98894857f`. Browser DB is owned SQLite; native PostgreSQL is qualified independently. |
| REGRESSION | Fresh broad FWD-01–05/tracking: 178 PASS, 127 SKIP, 233463 warnings, no XFAIL, 133.70s. Focused: 44 PASS, 1 SKIP, 1548 warnings. Environment/opt-in skips are not PASS. Architecture, changed Python Ruff, frontend TypeScript/ESLint, secret scan (0 findings), staged diff checks PASS. C1 migration-head suite 19 PASS, frontend presentation/local-time suite 12 PASS, production bundle build PASS reused after impact review: C2 changes text/projection/guards, no build dependency/config change. Pre-existing build size/Browserslist warnings remain. |
| KNOWN_GAPS | Reference28 mapping NOT_PROVEN; historical provenance/legacy replay proof, Production identity/qualification, onboarding and real customer delivery remain limited as earlier records. No user-selected display-zone control was added: browser zones vary, server instant and stored provenance do not. Read-only old-app rollback is bounded; incompatible old writes must remain stopped. Earlier failures and BLOCKED records are retained and not relabeled as PASS. |
| NEXT_SLICE_HANDOFF | FWD-06 local delivery complete. Document/map/control-tower/dashboard/canonical-cutover/GPS/correction/notification-policy/real-Agent slices not started. No next mission implicitly authorized. |
| MODEL_DOWNSHIFT_RECOMMENDATION | MODEL_DOWNSHIFT_CANDIDATE = Terra Light after time/schema/authorization/concurrency PASS. No actual model change asserted; token/credit usage unavailable and not estimated. |
| COMMITS | Product `71414b6af5a750f2f39682407f2315b540a86322`; integrity/recovery C2 `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`; this final evidence commit is resolved by Git log/final response. |
| LOCAL_HEAD | Product qualification/sync snapshot: `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`; final evidence HEAD supplied in final response. |
| REMOTE_HEAD | Fetched product snapshot: `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`; final evidence remote HEAD supplied after push/fetch. |
| LOCAL_REMOTE_SYNC | Product snapshot LOCAL_HEAD == REMOTE_HEAD, AHEAD=0, BEHIND=0 on existing feature branch. Final evidence push/fetch verified separately in response. No force/main merge/release tag. |
| WORKTREE_STATUS | Clean at exact C2 qualification and product sync; final status verified after evidence commit. No unrelated files staged. |
| EVIDENCE_PATH | `docs/operational/evidence/fwd-06-tracking-timeline/`; external diagnostic directories above contain no Git-staged environment/session/DB/log files. |
| REAL_MESSAGES_SENT | NO |
| LLM_APIS_CALLED_BY_PRODUCT | NO |
| PRODUCTION_CHANGED | NO |

LPAF v2.2 remains global active. Verified v2.4 candidate hash `217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397` remains pilot only; architecture mother is unchanged. Reference28 exception remains limited to the previously recorded FWD-06 scope.

## Repeat commands

From `D:/1-webapp/forwarder-dev` on the existing feature branch:

```powershell
python -B scripts/uat/run_fwd05_disposable_postgres.py backend/tests/test_fwd06_m1_postgresql.py --disable-warnings
powershell -ExecutionPolicy Bypass -File scripts/uat/run-fwd06-browser-uat.ps1
python -B -m pytest -q --tb=short --disable-warnings -p no:cacheprovider backend/tests/test_fwd01_notifications.py backend/tests/test_fwd02_geography.py backend/tests/test_fwd03_transport_intent.py backend/tests/test_fwd04_quote_amount_contract.py backend/tests/test_fwd05_runtime.py backend/tests/test_fwd05_http_boundary.py backend/tests/test_fwd06_tracking_characterization.py backend/tests/test_tracking_locations.py backend/tests/test_tracking_projection.py backend/tests/test_multi_unit_tracking_api.py backend/tests/test_multi_unit_tracking_service.py backend/tests/test_public_tracking_timeline.py backend/tests/test_fwd06_m1_time.py
```

The launchers create owned synthetic fixtures. Neither launch command targets Production or an existing colleague/customer database. Expected Tehran instant is independently specified as `2026-07-15T08:30:00Z` for wall `2026-07-15T12:00`. Harness failures and their corrections are described in IMPLEMENTATION-2026-09-16.md.
