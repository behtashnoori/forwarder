# Release 1.9.0 browser UAT evidence index

Date: 2026-08-04

No credentials, tokens, cookies, or personal data are retained.

| Viewport | Language / direction | Role | Workflow | Result | Screenshot | Console | Overflow |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1440×900 | Persian / RTL | Public | Header and landing layout | PASS | `desktop-1440x900-persian-admin.png` (prior bounded visual) | No error in current run | None |
| 768×1024 | English / LTR | Public | Responsive header/layout | PASS | Not retained | No error | None |
| 390×844 | Persian and English / RTL and LTR | Public | Compact header/layout | PASS | Not retained | No error | None |
| 412×915 | English / LTR | Public | Compact header/layout | PASS | Not retained | No error | None |
| Default desktop | Persian / RTL | Admin | Login and operational shipment list | PASS with blocker | Not retained | One console error captured across the authenticated session | Not observed |
| Default desktop | Persian / RTL | Admin | Release 1.9 initialization preview | FAIL | `desktop-1440x900-initialization-blocker.png` (prior blocker reference; current failure re-observed) | API 200; UI/API state mismatch | Not observed |
| Default desktop | Persian / RTL | Admin | Numeric identifier review | FAIL | Not retained | No error | Not observed |

Current blocker detail: the authenticated API returned one valid expected milestone and allowed confirmation, while the rendered panel showed zero and disabled the confirmation button. The list/detail UI also displayed numeric shipment, quote, request, plan, timeline, and checkpoint identifiers.

The authenticated tab accumulated one console error during the session. It was not cleared and re-probed after the initialization blocker, so the no-console-error gate is not approved.
