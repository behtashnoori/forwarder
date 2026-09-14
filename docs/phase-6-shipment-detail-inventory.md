# Phase 6 — Shipment Detail surface inventory

Inventory completed against frozen baseline `e1e766df3601226919510bdc7a778428993d5e4b` before presentation changes.

| Section | Business purpose | Authoritative read source | Actionable | Current actions | Duplicate | Role | Applicability | Current → target priority |
|---|---|---|---|---|---|---|---|---|
| Current state | Identify shipment, customer, status and route | Operational shipment summary | No | None | Partly | Primary | Direct + Project | High → Highest |
| Source/provenance | Explain direct/request/quote lineage | Shipment summary `source` | Navigation | Open request/project | No | Secondary | Direct + Project | High → Low |
| Route authoring | Create/validate/activate the initial route | Route-plan detail and governed commands | Yes | Create, edit, validate, activate | No | Primary when no active route | Direct + Project | High → High/current action |
| Route legs | Show planned/projected/actual movement | Active route-plan detail | Yes | Report departure/arrival | Yes, duplicated by active-route card | Primary | Direct + Project | High → High/single surface |
| Checkpoints/milestones | Execute and verify checkpoint progression | Active route-plan detail | Yes | Arrive, complete processing, depart, verify, correct | No | Primary | Direct + Project | Low/hidden → High |
| Timeline/reconciliation | Compare planned, projected and actual times | Route timeline projection | Yes | Reconcile | Partly overlaps route detail | Secondary | Direct + Project | Medium → Secondary within route |
| Replan | Preserve completed segments and revise future route | Route-plan revisions | Yes | Replan | No | Secondary | Direct + Project | Medium → Secondary within route |
| Derived timing deviation | Display projection-derived variance | Route timeline projection | No | None | Summary duplicated | Primary issue context | Direct + Project | Medium → High/issues |
| Operational delay | Manage recorded delays | Operational conditions read model | Yes | Existing delay commands | No | Primary issue | Direct + Project | Low/hidden → High |
| Operational exception | Manage current route exceptions | Route exception read model | Yes | Reconcile, resolve | Summary duplicated | Primary issue | Direct + Project | Low/hidden → High |
| Work items | Show governed items requiring attention | Shipment summary `open_work_items` | No on this surface | None | Summary duplicated | Primary issue | Direct + Project | Low/hidden → High |
| Documents | Show all authorized shipment/request evidence | Unified shipment-document endpoint | Yes | Upload, download, void | No | Primary | Direct + Project | Low/hidden → High |
| External references | Manage CMR/B/L/AWB and governed types | External-reference endpoint | Yes | Create, supersede, cancel | No | Primary adjacent concept | Direct + Project | Low/hidden → High |
| Document readiness | Show projected requirement state, separate from files | Document-readiness projection | Yes | Existing readiness commands | No | Primary for Project | Project only | Low/hidden → High in documents |
| Project execution | Preserve milestone execution | Project execution read models | Yes | Governed transitions/verification | No | Secondary | Project only | Low/hidden → Medium |
| Cargo/transport/tracking | Supporting physical details | Cargo and transport read models | Yes | Existing cargo/transport actions | No | Secondary | Direct + Project | Medium → Secondary |
| Economics | Separate commercial state from physical execution | Economics read model, permission gated | Yes | Existing economics commands | No | Secondary | Direct + Project | Medium → Collapsed |
| Unified history | One read-only business narrative | Unified shipment history read model | No | Refresh, filter, paginate, navigate | Competes with legacy detail panels | Primary history | Direct + Project | High/mid-page → High/final section |

No domain authority, schema, persistence model, or client workflow state is introduced by the target layout.
