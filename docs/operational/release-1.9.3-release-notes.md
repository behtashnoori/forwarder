# Forwarder 1.9.3 release notes

Forwarder 1.9.3 publishes the completed Admin Multi-Tenant Isolation work. It adds explicit Platform Admin and Organization Admin separation; Organization-scoped user administration; tenant-scoped dashboards, reports, searches, and exports; tenant-safe assignment and referral policy; Platform-only global site, branding, document, master-data, and reference mutation; improved controlled tenant authorization errors; and readiness for controlled onboarding of additional Organizations.

The shared application URL remains unchanged. This release introduces neither Organization storefronts/subdomains nor an Organization-management UI. Company onboarding remains controlled operational tooling. Existing quarantined synthetic legacy data remains protected: the migration does not clear quarantine, fabricate Organizations, or synthesize ownership.

The Production database boundary advances from v1.9.2 head `20260824_mt1_graph` to sole head `20260825_admin_multitenant` using `python -m backend.migration_cli upgrade 20260825_admin_multitenant --confirm` after approved backup and change authorization.
