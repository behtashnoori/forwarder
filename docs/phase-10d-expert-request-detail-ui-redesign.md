# Phase 10D: Expert Request Detail UI Redesign

## 1. Scope
This phase only redesigned the expert-facing request detail presentation layer in `src/pages/RequestDetail.tsx`. Backend behavior, API calls, routing, auth behavior, status updates, note creation, and workflow logic were preserved.

## 2. Before
The previous layout had a basic header, simple details/notes tabs, plain customer/route/cargo cards, and a basic sidebar for operations, timeline, and request information. It was functional but visually flat and less aligned with the newer RTL operational dashboard style.

## 3. UI Changes Made
- Redesigned the header as a rounded white card with request tracking number, `جزئیات درخواست حمل و نقل`, status/SLA badges, and existing navigation controls.
- Restyled the `جزئیات` and `یادداشت‌ها` tabs with a rounded blue active state.
- Redesigned the customer information card with icon bubble, customer name, and phone.
- Redesigned the route card with separate `مبدا` and `مقصد` boxes, desktop direction arrow, and transport method section.
- Redesigned the cargo card with grouped description, weight, volume, value, and special instructions.
- Redesigned the operations sidebar card while preserving the existing status-change select and values.
- Redesigned the timeline as a vertical operational timeline with dots, connecting lines, status transition badges, notes, dates, and creator.
- Redesigned the request information card with tracking number, created date, assigned expert, SLA date, and SLA status.
- Polished the notes tab with rounded input card, subject input, content textarea, submit button, and internal notes list.
- Added null-safe optional location rendering for province-first requests and partial route payloads.
- Added safer optional cargo rendering so missing cargo data and zero numeric values render predictably.
- Added an empty timeline state for requests without recorded timeline events.

## 4. Behavior Preservation
- Backend unchanged.
- API behavior and response shape unchanged.
- Route unchanged.
- Auth/logout behavior unchanged.
- Data fetching through `fetchExpertRequestDetail` unchanged.
- Status change through `changeRequestStatus` unchanged.
- Note creation through `addMessage` unchanged.
- Timeline behavior and data usage unchanged.
- Details/notes tabs behavior unchanged.
- Expert request detail workflow unchanged.

## 5. Null Safety
Optional route fields (`province`, `county`, and `city`) are typed as nullable and rendered through a local display helper. The route object, origin, and destination also have local fallbacks for partial expert-detail payloads. Missing province/county/city or cargo fields display `ثبت نشده` instead of crashing. Cargo weight, volume, and value use explicit null/undefined checks so `0` remains a valid rendered value.

## 6. Icon Import Safety
All JSX lucide icons used in `RequestDetail.tsx` are imported from `lucide-react`, including `DollarSign`.

## 7. Responsive/RTL Notes
The page keeps `dir="rtl"`, uses a two-column desktop layout with main detail content and sidebar, and stacks all sections on mobile. Cards use wrapped content, constrained grids, and break-word text to avoid horizontal overflow.

## 8. Verification
- `npm.cmd run lint`: passed with existing unrelated warnings in shared UI/context files and `UserManagement`.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
- `py -m pytest -q`: blocked because the Windows Python launcher is not available in PATH in this session.
- `git -c safe.directory=D:/Projects/webapp/15-forwarder/forwarder diff --check`: passed. Git reported only a line-ending normalization warning for `src/pages/RequestDetail.tsx`.
- Local Vite smoke: `npm.cmd run dev -- --host 127.0.0.1 --port 5173` started successfully and reported the local URL.
- Manual browser smoke checks: blocked because the in-app browser runner could not start in this sandbox, and a persistent background dev-server launch for route probing was not available.

## 9. Deferred Items
- Customer quote acceptance workflow.
- Quote creation redesign.
- Message system redesign.
- Shared design primitives.
- App-wide theme alignment.
- Backend workflow changes.
