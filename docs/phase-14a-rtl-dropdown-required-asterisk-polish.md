# Phase 14A: RTL Dropdown and Required Asterisk Polish

## Changed Files
- `src/components/LocationForm.tsx`
- `src/components/ui/select.tsx`
- `docs/phase-14a-rtl-dropdown-required-asterisk-polish.md`

## Runtime Behavior
Runtime behavior was not changed. This phase only changes visible UI presentation:
- select/dropdown RTL alignment;
- red asterisks for fields already required by the current frontend validation.

## Required Fields Marked
- Domestic origin province: `استان مبدا`
- Domestic destination province: `استان مقصد`
- International origin country: `کشور مبدا`
- International origin city/port: `شهر/بندر مبدا`
- International destination country: `کشور مقصد`
- International destination city/port: `شهر/بندر مقصد`
- Iran entry port, when destination is Iran: `بندر ورود`
- Iran entry province, when destination is Iran: `استان ورود`
- Contact phone: `شماره تماس`
- Domestic transport method when customer chooses method: `روش حمل برای مسیر داخلی`
- International transport method when customer chooses method: `روش حمل برای مسیر بین‌المللی`

Optional customer name, optional province detail fields, optional cargo fields, and optional date fields were not marked.

## Dropdowns Fixed
The shared select component now applies RTL direction and right alignment to:
- select trigger text;
- select content;
- select menu items;
- menu item text wrappers, including title/description option content.

This covers the shipment request form province, county, city, country, port, and transport method dropdowns that use the shared select component.

## Backend/API/DB
- Backend changed: No.
- Database changed: No.
- API request/response shape changed: No.
- Workflow changed: No.

## Verification
- `npm.cmd run lint`: passed on rerun with existing unrelated warnings in shared UI/context files and `UserManagement`.
- `npm.cmd run build`: passed.
- `npm.cmd run check:structure`: passed.
- `git -c safe.directory=D:/Projects/webapp/15-forwarder/forwarder diff --check`: passed. Git reported only line-ending normalization warnings.
- `python -m pytest -q`: blocked because `python` is not available in PATH in this session.
