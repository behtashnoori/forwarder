# PDR-019 — Governed quotation customer response (FWD-05)

- Status: ACCEPTED — AS_EXPLICITLY_AMENDED; bounded FWD-05 development and qualification.
- Date: 2026-09-16
- Decision owner: mission issuer acting within declared Product/Architecture authority;
  no person or additional role authority inferred.
- Source: [reconciled ADR-047](adr/ADR-047-governed-quote-customer-response.md).
- Context: inspected HEAD `98a0364a6b6f97daf70152c7d3a5cefbb242cac0`.

| ID | Choices | Recommendation and effect | Risk/fail-safe | Status |
| --- | --- | --- | --- | --- |
| D01 Customer authority | tracking bearer; scoped quote bearer; general Identity/OTP | Scoped quote bearer delivered only through certified exact customer link; staff cannot fetch it; tracking POST loses write authority | Forwarding/theft residual risk; no named-human/non-repudiation claim. No grant => no decision. Stronger identity is separate scope | ACCEPTED_AS_EXPLICITLY_AMENDED |
| D02 Negotiation | final; require replacement; allow same-quote finalization | negotiation_requested -> accepted/declined on same still-current valid quote; accepted/declined terminal; identical no-op/replay has no new effects | Old/stale/final incompatible command conflicts; immutable facts retained; no chat/counteroffer | ACCEPTED_AS_EXPLICITLY_AMENDED |
| D03 Request effect | won/lost automatically; unchanged status | Response changes quote response only, request status unchanged; unread/current expert inbox visible | No Shipment/payment/booking/transport/commitment created | ACCEPTED_AS_EXPLICITLY_AMENDED |
| D04 Money | existing loose text; Commercial supported codes; Economics catalog | Commercial-owned IRR/USD/EUR contract; quote-major.v1 exact strings: EUR/USD major units scale <=2; IRR integral rial; additive exact decimal storage; exact historical codes/values preserved | No default for unknown history or FX/unit conversion; remove misleading toman assertion, never reinterpret history | ACCEPTED_AS_EXPLICITLY_AMENDED |
| D05 Validity | browser/server day; known domain source | TIME-BIZ-003/004 unchanged; explicit narrow Organization Admin issuer-zone configuration only as fallback when no certified customer/market zone exists | Missing source blocks new publish; snapshot zone/policy/deadline; no guessed Asia/Tehran from display | ACCEPTED_AS_EXPLICITLY_AMENDED |
| D06 Grant reads/delivery | unbounded; short-lived; 30-day receipt access | Read expiry 30 days after later publication/quote expiry; write until quote expiry; exact recipient reissue revokes previous grant; bounded purpose-separated token delivery via existing fake notification path | Live revoke/recipient/scope checks; no cookie-only POST; capability material private; real connection still backlog | ACCEPTED_AS_EXPLICITLY_AMENDED |

The 2026-09-16 continuation explicitly accepted both named documents with amendments.
Original proposal authority was absent; this amended record permits bounded
additive schema/runtime development and qualification after retained technical gates.
No Production, real messaging or LLM authority is granted.
Affected parties: Commercial, Product, Architecture, Security, Data, Notification, QA.

## Amended acceptance history

2026-09-16: ACCEPT_AS_EXPLICITLY_AMENDED by mission Owner. Original SHA256 verified:
FFD2FDAEF602A99FA8269B4037618807DA1596F47E32871D2F9429004A8B4A4A.
Original bytes and complete decision are preserved in evidence/fwd-05-quote-response/.
ADR-047 reconciles schema/compatibility and the explicit amendments: accepted
replacement denied; declined replacement explicit; negotiation finalizes or uses
new replacement; response display independent of request status; usable audited
admin timezone; exact valid recipient/BLOCKED follow-up; read reissue never extends
horizon; reference 28 remains NOT_PROVEN with pilot-only deferral. No historical
unit conversion, autonomous Agent, Identity/OTP, payment or operational action.
