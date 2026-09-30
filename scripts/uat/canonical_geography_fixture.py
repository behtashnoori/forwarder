"""Provision the repository-qualified canonical geography in an owned test database."""
from backend.geonames_geography_catalog import (
    PACKAGE_SHA256,
    apply as apply_geography,
    plan as plan_geography,
)
from backend.international_geography_catalog import (
    COUNTRY_ONLY_SCOPE,
    apply_catalog as apply_country_catalog,
    load_catalog as load_country_catalog,
    plan_catalog as plan_country_catalog,
)


def ensure_canonical_geography() -> None:
    countries = load_country_catalog()
    country_plan = plan_country_catalog(countries, scope=COUNTRY_ONLY_SCOPE)
    if country_plan.conflicts:
        raise RuntimeError("Qualified country fixture plan contains conflicts")
    if country_plan.created_country_count:
        apply_country_catalog(
            expected_checksum=countries.checksum,
            executed_by="owned-canonical-geography-qualification",
            approval_reference="LPAF-V27-JOURNEY-CONTRACT-RECONCILIATION",
            environment="uat",
            catalog=countries,
            scope=COUNTRY_ONLY_SCOPE,
        )

    before = plan_geography()
    if before.conflicts:
        raise RuntimeError("Canonical geography fixture plan contains conflicts")
    if before.admin1_create or before.city_create:
        apply_geography(
            expected_checksum=PACKAGE_SHA256,
            operator="owned-canonical-geography-qualification",
            approval_reference="LPAF-V27-JOURNEY-CONTRACT-RECONCILIATION",
            environment="uat",
        )
    after = plan_geography()
    if after.conflicts or after.admin1_create or after.city_create:
        raise RuntimeError("Canonical geography fixture did not reach an idempotent state")
