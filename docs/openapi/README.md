# Forwarder OpenAPI Documentation

This directory contains the initial OpenAPI documentation for the Forwarder backend.

## Files

- `openapi.yaml` - single-file OpenAPI 3.0.3 specification.

## Scope

The current specification focuses on the main API surfaces covered by route review and characterization tests:

- Public shipment request
- Public tracking
- Expert auth and expert console
- CRM
- User management
- Admin panel
- Customer gamification
- Site settings

## Auth Notes

The spec documents a shared `bearerAuth` security scheme for protected endpoints.

Role requirements are documented in operation descriptions and tags:

- public endpoints have no `security` entry.
- expert endpoints use bearer token auth.
- admin endpoints use bearer token auth with admin role behavior in the backend.
- CRM endpoints use bearer token auth with `business_expert` role behavior in the backend.

## Known Limitations

This is a first-pass contract document. Some response schemas are intentionally flexible with `additionalProperties: true` because current characterization tests lock important keys but do not yet define every nested field as a strict schema.

Do not treat flexible schemas as permission to change runtime behavior. They indicate documentation confidence, not a new API contract.
