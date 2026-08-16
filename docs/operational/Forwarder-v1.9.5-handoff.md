# Forwarder v1.9.5 Production deployment handoff

Baseline: accepted Production `v1.9.4` at `20260826_org_document_policy`.

Target: application `v1.9.5`, database revision `20260827_org_hostname`.

The hostname `samand.logisticmarket.ir` is not assumed to exist. Mapping, DNS, IIS binding, and TLS are separately authorized server-phase operations.

## Controlled server sequence

1. Verify the artifact SHA-256 and package manifest.
2. Capture the current server-state snapshot.
3. Verify the active Production release and version.
4. Back up the database.
5. Verify document-storage backup/state as required.
6. Extract the new immutable release.
7. Prepare and verify its runtime/virtual environment.
8. Stop Production safely.
9. Migrate `20260826_org_document_policy` to `20260827_org_hostname`.
10. Validate WSGI from the new release.
11. Switch the backend and IIS release path.
12. Run core HTTP smoke checks.
13. Create the Samand Organization hostname mapping.
14. Configure and verify DNS.
15. Configure the IIS hostname binding.
16. Configure and verify TLS.
17. Verify the hostname resolves to the Samand Organization.
18. Submit a public shipment through the Samand hostname.
19. Verify `ownership_scope=TENANT`.
20. Verify Samand Organization ownership.
21. Verify referral selects only a Samand expert.
22. Verify tenant-owned unassigned behavior when no eligible expert exists.
23. Verify Organization Admin visibility is tenant-scoped.
24. Capture the post-deployment server-state snapshot.
25. Update the Forwarder Ops README/checkpoint.

Rollback is application-first. Remove hostname routing configuration under change control, downgrade to `20260826_org_document_policy`, reactivate immutable v1.9.4, and reverse infrastructure changes through their owning procedures.

No deployment, Production access, server database access, DNS/IIS/TLS change, or push is part of release preparation.
