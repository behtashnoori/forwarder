# Phase 9B: Landing Page Redesign

## 1. Scope

Phase 9B redesigned only the main public landing page presentation.

Runtime scope was limited to `src/pages/Index.tsx`. The phase did not change backend code, API behavior, routing, global theme files, Tailwind tokens, dependencies, expert/admin/customer pages, or Phase 7 polished pages.

## 2. Before

The previous landing page rendered:

- `Header`
- a large image-backed `Hero` section with blue gradient overlay
- a main section with tabbed request/tracking entry
- local `ShippingTypeSelector`
- local `TrackingSection`
- inline `LocationForm` after choosing domestic or international shipment
- `Footer`

The shipment choices were stacked gradient blocks, and tracking was hidden behind a tab.

## 3. UI Changes Made

- Removed the large hero from the landing page render.
- Moved the services section immediately below `Header`.
- Added the exact landing heading `خدمات فوروارد`.
- Added the subtitle `نوع ارسال خود را انتخاب کنید`.
- Replaced the tabbed selector with two equal shipment cards:
  - `حمل داخلی`
  - `حمل بین‌المللی`
- Added a centered desktop two-column grid with mobile one-column behavior.
- Restyled shipment cards with white background, subtle border, `shadow-sm`, hover `shadow-md`, blue icons, title, description, and `درخواست ارسال` button.
- Moved tracking below the service cards as a smaller secondary section.
- Used a local white / `#FAFAFA` landing background without changing global theme files.

## 4. Behavior Preservation

- Domestic request behavior is unchanged: selecting domestic still sets `shippingType` to `domestic` and renders the existing `LocationForm`.
- International request behavior is unchanged: selecting international still sets `shippingType` to `international` and renders the existing `LocationForm`.
- Tracking behavior is unchanged: empty values do nothing, non-empty values navigate to `/customer/track/${encodeURIComponent(code)}`.
- `Header` is still rendered as-is, preserving `ExpertLogin` and conditional admin access behavior.
- `Footer` is still rendered as-is.
- Backend/API behavior is unchanged.
- Routing is unchanged.
- Global theme files are unchanged.

## 5. Responsive/RTL Notes

- Service cards use one column on mobile and two columns on desktop.
- The service grid is capped around `800px` and centered.
- Persian text remains RTL through the existing global direction.
- Card text is centered and short enough to wrap safely.
- Tracking input stacks with the button on small screens and uses a row layout on wider screens.

## 6. Verification

Commands run before implementation:

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short` | Passed | Existing untracked `docs/phase-9a-landing-theme-audit-roadmap.md` was present from Phase 9A. |
| `npm.cmd run lint` | Passed | 0 errors, 13 existing warnings. |
| `npm.cmd run build` | Passed | Existing Browserslist/caniuse-lite and chunk-size warnings. |
| `npm.cmd run check:structure` | Passed | Structure check passed. |
| `python -m pytest -q` | Passed | 89 tests passed, 724 existing warnings. |
| `git diff --check` | Passed | No whitespace errors. |

Commands run after implementation:

| Command | Result | Notes |
| --- | --- | --- |
| `npm.cmd run lint` | Passed | 0 errors, 13 existing warnings. |
| `npm.cmd run build` | Passed | Existing Browserslist/caniuse-lite and chunk-size warnings. The hero image asset is no longer emitted because the landing page no longer imports `Hero`. |
| `npm.cmd run check:structure` | Passed | Structure check passed. |
| `python -m pytest -q` | Passed | 89 tests passed, 724 existing warnings. |
| `git diff --check` | Passed | No whitespace errors. Git printed the normal Windows LF-to-CRLF working-copy warning for `src/pages/Index.tsx`. |

Browser smoke checks on `http://127.0.0.1:8080/`:

| Check | Result |
| --- | --- |
| Landing loads and shows `خدمات فوروارد` | Passed |
| `حمل داخلی` request button opens existing `LocationForm` | Passed |
| `حمل بین‌المللی` request button opens existing `LocationForm` | Passed |
| Tracking input with `NO-SUCH-9B` navigates to `/customer/track/NO-SUCH-9B` | Passed |
| Expert login button remains visible | Passed |

## 7. Deferred Items

- App-wide theme alignment.
- Shared design primitives.
- Global token changes.
- ExpertConsole polish.
- UserManagement polish.
- Footer redesign.
- Production design pass.
