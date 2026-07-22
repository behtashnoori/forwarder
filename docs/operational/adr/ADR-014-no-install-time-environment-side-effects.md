# ADR-014: No install-time environment side effects

## Status

Accepted

## Decision

Package installation must not create or modify environment files, secrets, schemas, seed data, or runtime configuration. Environment setup is a separate, explicit manual command that copies only a tracked safe template and refuses implicit overwrite.

## Consequences

Developers must run `npm run setup:env` intentionally. CI and container dependency installation remain deterministic and cannot inherit repository-provided credentials.
