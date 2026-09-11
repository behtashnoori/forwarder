# Forwarder production deployment contract

## Stable production contract

- Host: `SRV8756807400`; production root: `C:\1-webapp\forwarder-production`; runtime environment: `C:\1-webapp\forwarder-runtime\production.env`.
- The backend is the `Forwarder Backend Production` Scheduled Task and must own the sole listener on `127.0.0.1:5101`. Its command must reference the selected release's `runtime\python.exe`.
- IIS site `forwarder` serves the selected release's `dist`. Read it with `Get-Website -Name forwarder`; update it with `Set-WebConfigurationProperty` on the root virtual directory. Do not use the IIS provider's `physicalPath` object property.
- Precheck is read-only. It validates package hashes, environment, read-only database/Alembic identity, task XML, listener provenance, IIS path, capacity, and rollback prerequisites before any mutation.
- Deployment captures `production.env` and Scheduled Task XML, extracts application and runtime only beneath the target release, switches task and IIS together, then proves listener provenance and health. Failure restores the exact predecessor environment, task, IIS path, and backend listener. No migration or downgrade is permitted.

## Per-release identities

The descriptor and release-specific scripts define candidate artifact hashes, runtime hashes, Alembic head, target release, and explicit frontend/backend predecessor paths. The current predecessor is intentionally split: backend/task/listener is `release-UAT-Fix-RC1-d55a76a`; IIS frontend is `release-UAT-Consolidated-RC1-84eafd8`.
