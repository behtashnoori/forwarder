# PDR-019 — Governed quotation customer response (FWD-05)

- Status: PROPOSED — explicit Product acceptance required; not implementation authority.
- Date: 2026-09-16
- Decision owner: mission issuer acting within declared Product/Architecture authority;
  no person or additional role authority inferred.
- Source: [full ADR-047 proposal](adr/ADR-047-governed-quote-customer-response.md).
- Context: inspected HEAD `98a0364a6b6f97daf70152c7d3a5cefbb242cac0`.

| ID | Choices | Recommendation and effect | Risk/fail-safe | Status |
| --- | --- | --- | --- | --- |
| D01 Customer authority | tracking bearer; scoped quote bearer; general Identity/OTP | Scoped quote bearer delivered only through certified exact customer link; staff cannot fetch it; tracking POST loses write authority | Forwarding/theft residual risk; no named-human/non-repudiation claim. No grant => no decision. Stronger identity is separate scope | PROPOSED |
| D02 Negotiation | final; require replacement; allow same-quote finalization | negotiation_requested -> accepted/declined on same still-current valid quote; accepted/declined terminal; identical no-op/replay has no new effects | Old/stale/final incompatible command conflicts; immutable facts retained; no chat/counteroffer | PROPOSED |
| D03 Request effect | won/lost automatically; unchanged status | Response changes quote response only, request status unchanged; unread/current expert inbox visible | No Shipment/payment/booking/transport/commitment created | PROPOSED |
| D04 Money | existing loose text; Commercial supported codes; Economics catalog | Commercial-owned IRR/USD/EUR contract; canonical integral BIGINT exact strings on new API; exact historical codes/values preserved | No default for unknown history or FX/unit conversion; remove misleading toman assertion, never reinterpret history | PROPOSED |
| D05 Validity | browser/server day; known domain source | TIME-BIZ-003/004 unchanged; explicit narrow Organization Admin issuer-zone configuration only as fallback when no certified customer/market zone exists | Missing source blocks new publish; snapshot zone/policy/deadline; no guessed Asia/Tehran from display | PROPOSED |
| D06 Grant reads/delivery | unbounded; short-lived; 30-day receipt access | Read expiry 30 days after later publication/quote expiry; write until quote expiry; exact recipient reissue revokes previous grant; bounded purpose-separated token delivery via existing fake notification path | Live revoke/recipient/scope checks; no cookie-only POST; capability material private; real connection still backlog | PROPOSED |

Acceptance must explicitly name ADR-047 and PDR-019 or specify amendments. This
record grants no Schema, runtime, Production, real messaging or LLM authority.
Affected parties: Commercial, Product, Architecture, Security, Data, Notification, QA.
