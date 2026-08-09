# Release 1.9.0 UX consistency report

Date: 2026-08-04

Responsive public-page checks passed at 1440×900, 768×1024, 390×844, and 412×915 with no horizontal overflow. Persian RTL and English LTR direction changes were correct. The compact header remained sticky.

The bounded Back to Top implementation is initially hidden, has an accessible label, uses logical `end` positioning for RTL/LTR, suppresses itself while blocking overlays are present, and disables forced smooth animation when reduced motion is requested. Admin tabs are offset below the sticky header.

Authenticated operational UAT is blocked by the initialization-preview mismatch recorded in the final RC review. Numeric legacy identifiers are also visible throughout the operational list/detail interface. Full sticky-action and Back to Top interaction approval therefore remains pending.
