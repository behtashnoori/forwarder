# Forwarder v1.10.0 Production operator tooling

This directory contains the laptop-qualified, operator-mediated Production
tooling for Forwarder v1.10.0. It does not authorize deployment. Codex does not
run these tools against Production; a human operator runs them locally on the
Windows Production server after the applicable gate and authorization.

The first server phase is read-only and uses
`Collect-ForwarderV110ProductionReadOnly.ps1` plus the SQL files under `sql/`.
The collector emits one sanitized JSON result and performs no server mutation
other than creating that explicitly requested result file.

Application bytes in the Production package are built only from
`e36ee7cee157657c97dc42a539eaf1909f510a33`. These tooling files are
stage-specific controls and are not Product runtime behavior.

Hard identities:

- Product version: `1.10.0`
- Application source: `e36ee7cee157657c97dc42a539eaf1909f510a33`
- Starting database revision: `20260921_shipment_evidence_ownership`
- Target database revision: `20260926_fixed_shipment_responsible_expert`
- Backend listener: live collector evidence must confirm the governed endpoint;
  the qualified historical contract is `127.0.0.1:5101`.
- Scheduled Task: `Forwarder Backend Production`
- IIS site: `forwarder`
- External environment: `C:\1-webapp\forwarder-runtime\production.env`

`REFERENCE_IMPACT=NONE`
