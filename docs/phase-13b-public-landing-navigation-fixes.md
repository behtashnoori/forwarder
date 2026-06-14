# Phase 13B: Public Landing and Navigation Fixes

## 1. Scope
This phase improves the public landing page copy, public navigation links, tracking visibility, footer fallback wording, and request-success return flow. It is limited to the frontend public flow.

## 2. Customer Feedback Addressed
- Service positioning: the landing page now presents Forwarder as a service for registering, managing, coordinating, and tracking shipment requests.
- Top whitespace: the landing section uses tighter vertical spacing so the tracking area appears sooner.
- Tracking visibility: the tracking card clearly explains that customers can enter a tracking code to view request status.
- Contact/about links: header navigation now points to real landing-page sections.
- Success return/home flow: the success state keeps the tracking number visible and adds an explicit return-to-home action.

## 3. Changes Made
- `src/pages/Index.tsx`: updated public landing copy, reduced top spacing, added real `about`, `tracking`, and `contact` anchors, clarified domestic/international request copy, and improved tracking text.
- `src/components/Header.tsx`: converted about/contact buttons into real anchors and preserved expert/admin access behavior.
- `src/components/Footer.tsx`: simplified fallback copy so it describes the shipment-request service and avoids unsupported claims.
- `src/components/LocationForm.tsx`: added a clear home return action to the post-request success state while preserving tracking and new-request actions.

## 4. Behavior Preservation
- Backend unchanged.
- API behavior unchanged.
- Request form behavior preserved.
- Tracking behavior preserved.
- ExpertConsole unchanged.
- RequestDetail unchanged.
- AdminPanel unchanged.
- Reports/export unchanged.

## 5. Non-goals
- No request-form redesign.
- No calendar change.
- No notification implementation.
- No SLA.
- No priority.
- No PDF/report change.

## 6. Verification
- `npm.cmd run lint`: passed with existing unrelated warnings in shared UI/context files and `UserManagement`.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
- `git -c safe.directory=D:/Projects/webapp/15-forwarder/forwarder diff --check`: passed. Git reported only line-ending normalization warnings.
- Smoke checks: local dev server served the landing page with HTTP 200. Browser/manual interaction checks were limited in this sandbox.
