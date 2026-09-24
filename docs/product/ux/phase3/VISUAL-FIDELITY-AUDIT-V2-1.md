# Visual fidelity audit — V2.1

Scope: static synthetic prototype only. Visual artifact commit `32d5a14ae70f0b74747f4ab4c3a7bea185002dc5`; Chrome 154.0.8037.57, desktop 1440×1000, customer 390×844. Baseline source: canonical `d83b1aa7c0011221188e753c0f38d2058859400b`. Final browser/source hashes are in [visual-review.json](evidence/browser-v2-1/visual-review.json). Human final approval is NOT_RUN.

## Category audit

| Category | CURRENT_FORWARDER_BASELINE | V2_BEFORE | V2_1_AFTER | RESULT |
| --- | --- | --- | --- | --- |
| TYPOGRAPHY | Vazirmatn; 12/14/16px; 500/600 hierarchy | Font named but not bundled, actual fallback; frequent 800/900 | Local Vazirmatn; 12px metadata, 14–16px body, 24px title, 600 headings | ALIGNED |
| SPACING | 4/8/16/24px, 24px card padding | Mixed 13/17/18px spacing; uneven disclosure spacing | 8/16/24 rhythm, compact record rows, 24px major panels | ALIGNED |
| COLOR | Primary HSL215 85%35%; pale lavender-gray page; white surface | Navy/teal hero and unrelated hex palette | Exact primary/background/border values; pale supporting tones | ALIGNED |
| SURFACES | Card white, background tinted, subtle gradients | Repeated equally bordered/elevated white cards | Distinct next action, attention, incomplete and activity; flat nested records | ALIGNED |
| BORDERS | HSL220 15%88%, soft | Several unrelated border hues and nested frames | Canonical neutral, limited status/selected tint; excess nested borders removed | ALIGNED |
| SHADOWS | Small 0 2px 8px; larger for elevation | Broad 7–30px shadows | Canonical small/medium/large; no shadow on inner rows | ALIGNED |
| RADIUS | Controls12, cards/dialog16, tab inner8, pills full | 8/9/10/11/13/19px mixed | Consistent 12/16/8/full system | ALIGNED |
| BUTTONS | Blue primary; outline/ghost/link; 40px standard | Dark navy primary repeated for filters/selection | Blue main CTA; soft selected filters and delivery selector; outline secondary | ALIGNED |
| FORMS | Tinted background,12px radius,40px minimum, focus ring2 | White10px fields, inconsistent filter/textarea | Same background/radius/ring; measured42.5px for Persian line-height; mobile44px+ | ALIGNED |
| TABLES | Medium48px header,16px cells, muted hover/selection | Default-like headers/separators | Same palette/type/hover, RTL/numeric alignment,14px vertical density | INTENTIONAL_PHASE3_EVOLUTION |
| TABS | Muted track, light selected item, subtle shadow | More borders, darker role state | Canonical track/selected/small radius language | ALIGNED |
| NAVIGATION | White translucent header, soft hover, primary focus | Heavy role fill and generic list | Same light shell; active blue cue; V2 side navigation retained | INTENTIONAL_PHASE3_EVOLUTION |
| STATUS | Primary/green/warning/red hues, full-radius badge | Mixed teal, navy and dark status accents | Same hue family, darker text/pale surfaces, words and check/clock/issue markers | INTENTIONAL_PHASE3_EVOLUTION |
| TIMELINE | No canonical shared Timeline component found | Generic circles and low hierarchy | Date groups, small consistent markers, clear event/time spacing, correction text/history retained | INTENTIONAL_PHASE3_EVOLUTION |
| MODALS | Tinted panel,16px radius,24px padding, shadow-lg | White19px panel | Canonical panel/controls; V2 width and mobile sheet retained; lighter overlay | INTENTIONAL_PHASE3_EVOLUTION |
| RESPONSIVE | Mobile-first utilities and wrapping customer top nav | Bottom nav width overflow risk, fallback font | V2 bottom nav retained with44px+ targets, correct width/padding, initial ETA visible | INTENTIONAL_PHASE3_EVOLUTION |
| RTL | RTL root/controls, flex icon placement | RTL but inconsistent control/focus treatment | Logical spacing, right-aligned forms/tables, dropdown left, focus ring visible | ALIGNED |

Result: **11 ALIGNED, 6 INTENTIONAL_PHASE3_EVOLUTION, 0 NEEDS_CHANGE** in the defined agent visual audit. This is readiness for human review, not the human verdict.

## Current pattern → candidate comparison

| Required comparison | Current reference | V2.1 application |
| --- | --- | --- |
| A Form/control | Real Button/Input/Textarea source rendered in reference-current-form.png | aligned-allocation-form.png and aligned-form-focus.png |
| B Page header | Header.tsx source: white/90, border, blur, font hierarchy; synthetic reference shell is explicitly reconstructed | expert-overview.png; header170.2px versus V2 recorded193.6px |
| C Tabs/navigation | Real Tabs source rendered in reference-current-tabs.png; navigation context components source-only | expert-route.png; expert-overview.png sidebar; no claim that the sidebar existed in canonical |
| D Card/panel | Real Card source in reference-current-panel.png | expert-overview.png, distinct action and activity panels |
| E Table/list | Real Table source in reference-current-panel.png | expert-cargo.png; expert-documents.png |
| F Status | Real Badge source in reference-current-panel.png | expert-route.png, expert-closure.png; pale variants intentionally evolved |
| G Modal | ui/dialog.tsx inspected; actual Dialog not mounted because portal/context behavior is outside static source harness | aligned-allocation-form.png; source values mapped, no fake canonical modal screenshot |
| H Customer mobile | CustomerPortalLayout.tsx source: slate50, white wrapping nav,1152px max-width,16px margins; reference-current-390.png is component specimen, not customer runtime | customer-summary-390-viewport.png and five mobile page captures |

[Side-by-side gallery](evidence/VISUAL-COMPARISON.html). Exact reference source file hashes: [reference-source.json](evidence/browser-v2-1/reference-source.json).

The canonical Switch specimen retains the source's physical translate-x styling, which can protrude under RTL; the prototype retains its existing RTL direction with canonical size/color. It is not a reason to reproduce that presentation in the candidate. Canonical files are untouched. The reference font is the same locally bundled family; original canonical index.html's Google Fonts network loading is deliberately absent.

## Persona consistency and page-story preservation

| Persona | Pages reviewed | Density / relationship result |
| --- | --- | --- |
| Expert | Overview, customers/requests, cargo, route planned/actual, execution, allocation cargo/unit, documents, timeline/history, problems, deliveries, closure | Compact shared header; 3/2-column executions; same primary/control language; no nested independent cards for every chain node |
| Customer | Summary, combined route/location/timeline, cargo, documents, delivery; desktop and390px | Same type/blue/radius/surfaces; lighter story and comfortable mobile reading; other customer/private data excluded by preserved V2 behavior |
| Admin | Definitions, route-time comparison, closure requirements, exception decision | Grouped policies, compact definition rows, consistent switches, calm incomplete state, reason field and clear decision hierarchy |

All 20 [V2 page-story rows](STORYTELLING-AUDIT-V2.md) remain byte-identical: PAGE_GOAL, PRIMARY_USER_QUESTION, PRIMARY_ACTION, KEY_RELATIONSHIP, IMPORTANT_STATE and NEXT_STEP are unchanged. Customer route/location and timeline remain the single combined V2 destination; no extra action or workflow stage was added.

## Accessibility / browser evidence

- All64 V2 preservation checks rerun in Chrome: PASS. This includes three navigation journeys, allocation validation/dual-view updates, transfer, document filtering/receipt synchronization, private followup filtering, admin reason enforcement, history, dialogs and21 role/state combinations.
- All20 desktop pages and five customer mobile surfaces: page overflow zero. Bottom nav targets at least44×44; page end can be scrolled above nav. Mobile initial ETA text is visible at y672.7–725.9 in844px height.
- Canonical/candidate input radius12px and background rgb(248,247,252), button radius12px and primary rgb(13,77,165) match in computed Chrome styles.
- Visible2px focus, modal Tab cycle and Escape: PASS. Labels and native semantic inputs preserved. Reduced-motion CSS respected. Status wording remains explicit.
- Eight sampled palette text pairs exceed4.5:1; minimum metadata5.27:1; primary8.01:1. This is a scoped visual accessibility review, not a full WCAG or assistive-technology certification.
- Console/page errors0, failed resources0, external browser requests0; font loaded locally. Reference render and candidate are local and synthetic.

The human question “does it feel like Forwarder?” is intentionally left to the final owner review. No material candidate NEEDS_CHANGE was found in this audit.
