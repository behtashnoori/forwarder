# ADR-028 — Administrator-Managed Reference Data

- **Status:** Accepted
- **Date:** 2026-08-04
- **Scope:** Platform architecture, installation, release validation, administration
- **Supersedes:** Any interpretation of PDR-014 or ADR-021 that makes catalog population or Seed execution a deployment or release prerequisite

## Decision

The application must be fully installable and operational without any Reference Data Seed. Deployment consists only of the application, database schema, and explicit migrations. Authorized administrators create Reference Data gradually through the Admin UI. Seed, import, export, plan, and catalog-apply commands are optional migration utilities; they are never installation, deployment, health, smoke-test, or release-validation requirements. No release may depend on Reference Data population.

Reference Data includes `LogisticsPointType`, `MilestoneType`, `ServiceType`, `DocumentDefinition`, `CargoType`, `UnitOfMeasure`, Cargo Catalog entries, and equivalent governed lookups. It supports administrator-controlled create, update, activate, and deactivate; immutable business codes; duplicate protection; no hard deletion; full audit; and organization rules where applicable.

System Data is distinct: roles, permissions, feature flags, internal configuration, framework metadata, and indispensable bootstrap objects may be installer-generated. Master Data is user-created in normal operation and includes Project, Customer, LogisticsPoint, Carrier, Vehicle, Driver, and Organization. Operational Data is created only through business execution and includes Shipment, RoutePlan, Quote, Operational Milestone, Operational Event, Invoice, and Evidence.

An empty governed catalog is valid. Administration UI must explain that no records exist and invite an authorized administrator to create the first item. It must not display a Seeder prompt or create records automatically. Dependent business actions may truthfully report that no active choice exists, but application startup, health, and unrelated workflows must continue to operate.

## Release and validation policy

A release is deployable when its backend, frontend, and applicable migrations pass. Reference Data population is outside release validation. Smoke testing verifies that an authorized administrator can create the first Reference Data record; it does not require a predefined catalog. Package manifests and runbooks must record Seed as optional/not executed, never pending deployment work.

## Consequences

Historical catalogs and apply tooling remain available for controlled import or environment migration. Their checksums, planning, authorization, and audit controls still apply when voluntarily used. They grant no canonical ownership over administrator-created values and cannot become a hidden runtime dependency. Existing historical evidence remains factual, but this ADR governs all current and future installation, deployment, package, smoke-test, and release language.
