# S5 UX Semantic Clarity

## Document requirements

The organization policy screen now calls its setting the **current policy** for
future records and explicitly explains that `DISABLED`, `OPTIONAL`, and a
runtime incomplete state are different. The shipment document card identifies
every displayed requirement as belonging to that shipment and explains in
plain Persian that later policy changes do not alter it. No API comparison or
retroactive reconciliation was added: empty/fresh records show no such card.

## Logistics locations

The Platform Admin catalog is labeled **شبکه مرجع لجستیکی پلتفرم** and explains
that catalog presence does not make a location operational for an organization.
The Organization Admin adoption screen uses **شبکه مرجع لجستیکی**, makes
adoption explicitly organization-scoped, and retains its existing separate
action, now labelled **افزودن به شبکه عملیاتی سازمان**, for creation of the
tenant operational point. The tenant list is labeled **شبکه عملیاتی سازمان**.

## Preservation and verification

Document policy resolution, captured requirements, readiness calculation,
GlobalPoint lifecycle, adoption/materialization, LogisticsPoint lifecycle, and
tenant ownership were not changed. The UI additions are readable text and
non-color-only context; existing responsive flex/grid layouts remain intact.

Focused frontend semantic tests: 16 passed. Relevant backend preservation
tests: 28 passed. The production frontend build passed. No migration, data,
package, lockfile, or Production change occurred.

## Deferred scope

The nearby Project network and type-management screens retain older mixed
English terminology. They are adjacent but not needed to explain the proven
Global catalog/adoption/operational journey and are deferred from this bounded
semantic slice.
