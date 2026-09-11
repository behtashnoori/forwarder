# Personal Analytics disposable browser qualification

Saved View and Dashboard Product Reality use the repository's canonical fresh-browser runner. From the repository root, invoke:

```powershell
.\scripts\run-shared-transport-e2e.ps1 -PersonalAnalytics
```

`CERT_ADMIN_URL` must be a loopback PostgreSQL administrator connection. The runner creates a uniquely named database and runtime, resolves the repository's single Alembic head, upgrades and verifies the database before invoking the deterministic Personal Analytics seed, starts fresh backend and frontend processes, and runs the unchanged `e2e/qualification.spec.ts`.

Cleanup is mandatory in success and failure paths: runner-owned processes, runtime files, database, and ephemeral browser credential are removed. Modes are mutually exclusive and unsupported parameters fail closed through PowerShell parameter binding. No credential is stored in this document or the repository.
