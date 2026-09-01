# S1 Reference-Data Readiness

**Scope:** public international request location selection only. This bounded
change does not add geography, alter migrations, touch Production, or change
Global Network terminology.

## Evidence-backed current model

* `Country` and `InternationalCity` are separate database-managed, platform
  reference entities. Their active flags are independent. Legacy scripts such
  as `backend/seed_international_data.py` are static seed inputs; admin CRUD
  in `backend/services/location_admin_service.py` is the current managed
  lifecycle path. The model is therefore hybrid, not an external live API.
* The public `LocationForm` loads `/api/countries`, then
  `/api/international-cities?country_id=…`. Its non-Iran flow requires an
  international city/port on both endpoints. Canonical request validation also
  requires a resolved, active, country-matching `InternationalCity`.
* Iran has a separate destination-only alternative through a governed domestic
  city, Iran port, or customs office. It does not make Global LogisticsPoint or
  tenant `LogisticsPoint` selectable in the public request form.
* Global LogisticsPoint is a platform reference catalog; organization adoption
  and materialization create a tenant operational point. Those points are
  complements to the public selector, not substitutes in this workflow. Their
  availability is tenant-specific and is intentionally excluded from this
  global public-form readiness rule.

## Local Turkmenistan characterization

The local non-production `instance/test_referral.db` contains the relevant
tables but no Country or InternationalCity rows. Turkmenistan is therefore
**NOT REPRODUCED locally**: not present, no local ID, no active city count, and
no alternative location count can be inferred. No Production/UAT database was
accessed. The supplied UAT observation remains the evidence for the real
environment finding.

## Invariant

For the public international request workflow, a country is selectable only
when it is active and has at least one active `InternationalCity`. A selected
international city must be active and belong to the selected country. Countries
without that continuation are intentionally unavailable in this selector;
they are not silently presented as an empty dead end. This invariant is global
to this public workflow, not tenant/project scoped. Historical request rows are
not rewritten and remain readable through their persisted/snapshotted route
fields.

## Remediation

`GET /api/countries` now filters active countries by an active
`InternationalCity`. No geographic record was invented or changed. The API is
the single source consumed by the public selector, so this is the smallest
change that prevents the observed selectable-parent/empty-child failure class.
The endpoint deliberately does not count global or tenant logistics points,
because the public form cannot submit them as an international location.

## Readiness matrix for repository-local data

| Dataset | Countries assessed | READY | NOT_READY | UNKNOWN |
| --- | ---: | ---: | ---: | ---: |
| `instance/test_referral.db` | 0 | 0 | 0 | 0 |

This local test database cannot certify UAT/Production reference-data
completeness. A controlled future non-production catalog audit must run against
the intended release dataset and record country, active city count, and public
selector readiness. No authoritative project data source exists here that
authorizes adding Turkmenistan cities.

## Regression evidence

`test_public_country_selector_only_exposes_countries_with_active_international_city`
proves: ready active country is exposed; active country with no city is hidden;
inactive child is not counted; inactive country is hidden. Existing canonical
location tests prove country/child ancestry and active-state rejection during
request normalization.
