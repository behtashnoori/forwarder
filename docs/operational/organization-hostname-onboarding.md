# Organization hostname onboarding

Organization identity is the immutable `operational_organization.id`. A hostname is only an exact routing alias. Adding, replacing, or retiring a hostname never moves users, requests, projects, documents, policies, or other Organization data.

## Security boundary

The application resolves the normalized HTTP `Host` observed by Flask. It deliberately ignores request bodies, query strings, email domains, company names, expert identities, and `X-Forwarded-Host`. Resolution uses an exact active `organization_hostname.hostname` mapping joined to an active Organization. Unknown, inactive, malformed, or ambiguous routing state fails closed to platform `INTAKE`.

Production must prevent direct access to the application origin. IIS/reverse-proxy rules must preserve the externally validated Host, accept traffic only for configured bindings, replace rather than append untrusted forwarding headers, and restrict the backend listener to the trusted proxy/network. TLS certificate names and IIS bindings must match every enabled hostname. Do not enable a database mapping until DNS, binding, TLS, and origin-access controls are ready.

## Add an Organization hostname

1. Create or verify the Organization in Forwarder.
2. Create its Organization Admin and expert memberships.
3. As `PLATFORM_ADMIN`, register the exact normalized hostname mapping. Organization Admins may read their mappings but cannot mutate them.
4. Create and verify the DNS record.
5. Add the IIS binding for the exact hostname.
6. Add or verify its TLS certificate and HTTPS redirect policy.
7. Verify the hostname resolves to the intended active Organization.
8. Submit a synthetic public shipment request using that hostname.
9. Verify `ownership_scope=TENANT` and the expected `operational_organization_id`.
10. Verify assignment considers only eligible experts with one active membership in that Organization.
11. If no expert is eligible, verify the request remains visible in `درخواست‌های تخصیص‌نیافته`.

Local/UAT certification fixtures use `samand.logisticmarket.ir` for `samand-tarabar` and `companyb.logisticmarket.ir` for `company-b`. They do not assert that Production DNS records or bindings exist.

## Domain migration

1. Register the new hostname against the same Organization while the old mapping remains active.
2. Provision DNS, IIS binding, and TLS for the new hostname.
3. Verify submission, ownership, expert assignment, public links, and branding on the new hostname.
4. Mark the new mapping primary.
5. Keep the old hostname active during the transition and redirect only after client and integration verification.
6. Deactivate the old mapping later. No tenant data migration is required.

## Forwarder Ops Kit alignment

Future onboarding inputs and checks must include Organization identity, Organization Admin, hostname mapping, DNS result, IIS binding, TLS certificate coverage, trusted-proxy Host preservation, direct-origin denial, a tenant-owned test submission, and assignment evidence. The Ops Kit must never derive Organization identity by parsing a subdomain and must not write Production mappings without a separately authorized change window.

## Platform intake

Unmapped traffic remains unowned `INTAKE`. Platform-only APIs can list it and explicitly route it to an active Organization; routing immediately invokes tenant-scoped auto-assignment. Organization Admin APIs never expose global intake. A dedicated Platform Admin intake screen remains a frontend follow-up.
