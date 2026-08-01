# Forwarder 1.3.1 — Central Route Scroll Restoration Report

- **Status:** Release candidate; all pre-commit Scroll gates passed
- **Date:** 2026-08-01
- **Change type:** PATCH
- **Primary capability:** CAP-007 Customer Portal
- **Supporting scope:** Shared frontend shell/router
- **Database / backend / environment impact:** None
- **Deployment impact:** Frontend-only immutable package; no backend restart or migration; deployment is not authorized by this closure task

## Root cause

`BrowserRouter` rendered `Routes` without a central scroll policy. React Router changed the location but retained the document viewport, so PUSH/REPLACE from a long route could open a short route at the old vertical offset. No page-level `scrollTo` or `history.scrollRestoration` override caused the defect. This matches the defect shape stated in the delivery contract; however, the named discovery report is not present in the repository, so its exact conclusion could not be independently cited.

## Confirmed behavior matrix

| Navigation Type | Current Behavior | Expected Behavior | Fix Required |
|---|---|---|---|
| Link PUSH to different pathname | Retains prior document position | Top, auto | Yes — central reset |
| `navigate(path)` PUSH | Retains prior document position | Top, auto | Yes — central reset |
| `navigate(path, { replace: true })` | Retains prior document position | Top, auto | Yes — central reset |
| Browser Back/Forward (POP) | Browser-native restoration is available | Preserve/restore browser position | No override; manager must abstain |
| Same-path query change | Retains position | Preserve by default | Manager abstains |
| Valid hash | Native placement can hide under sticky header and async target may be absent | Target below sticky header | Central bounded retry with offset |
| `state.preserveScroll: true` | No shared contract existed | Preserve | Central opt-out |
| Modal/dialog open/close | Local dialogs do not change route; focus returns through Radix | Do not reset underlying page | Manager abstains; modal route state supported |
| Async target rendering | No shared handling | Find late hash without fighting user | Short bounded retries cancelled by user input |
| Initial load | Browser owns initial position | Preserve browser behavior | Manager abstains |

## Implementation and accessibility

`RouteScrollManager` is mounted once inside `BrowserRouter`. It resets only non-POP PUSH/REPLACE pathname changes, uses `behavior: "auto"`, leaves `history.scrollRestoration` untouched, and supports `preserveScroll`, `modal`/`backgroundLocation`, and optional `focusMainContent`. Focus targets a main heading or `[data-route-focus="true"]`, adds `tabIndex=-1` only when requested, never focuses body, and uses `preventScroll`. POP never receives route focus. Hash positioning accounts for the sticky header and abandons retries after wheel, touch, pointer, or scroll-key interaction. No smooth-scroll behavior or per-page reset was added.

## Compatibility and exceptions

The patch is frontend-only and backward compatible with existing routes. Native POP restoration remains browser-controlled and therefore depends on browser history behavior and page layout stability. Hash lookup retries for 300 ms; later targets require the page to render an anchor earlier or navigate again. Optional focus is opt-in to avoid changing established focus behavior. Route-backed dialogs should pass `modal: true` or `backgroundLocation`; current dialogs are local state and cause no navigation.

## Test scope and readiness

Focused tests cover Link, navigate, replace, POP abstention, query-only changes, hash offset, explicit preservation, async/user interaction, optional focus, dialog close, and viewport widths 360/390/412 with no manager-induced horizontal overflow. A real Chromium check at 360 px scrolled the mobile root to `scrollY=108`, followed the SPA `/about` link, and observed `scrollY=0`; at 360, 390, and 412 px the document `scrollWidth` equalled `clientWidth`. Focused tests passed 12/12, full frontend regression passed 89/89, ESLint completed with zero errors, the production build passed, and the TypeScript differential introduced zero diagnostics. The immutable release package is prepared only after the implementation commit and annotated tag are created.
