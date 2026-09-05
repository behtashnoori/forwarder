# Forwarder UAT Shipment Summary RC1 operator runbook

Copy the complete package to one local server directory. Run PowerShell as Administrator on `SRV8756807400`.

```powershell
.\PRECHECK-UAT-Shipment-Summary-RC1-4c96ea4.ps1 -PreviousBackendReleasePath 'C:\1-webapp\forwarder-production\release-UAT-Fix-RC1-d55a76a' -PreviousFrontendReleasePath 'C:\1-webapp\forwarder-production\release-UAT-Consolidated-RC1-84eafd8'
```

Proceed only after `PRECHECK_MANIFEST=PASS` and `ABORTED_BEFORE_MUTATION`. Then execute:

```powershell
.\DEPLOY-UAT-Shipment-Summary-RC1-4c96ea4.ps1 -ConfirmDeployment -PreviousBackendReleasePath 'C:\1-webapp\forwarder-production\release-UAT-Fix-RC1-d55a76a' -PreviousFrontendReleasePath 'C:\1-webapp\forwarder-production\release-UAT-Consolidated-RC1-84eafd8'
```

Expected deployment completion is `DEPLOYED_AND_VERIFIED`. A failure after mutation automatically restores the production environment, Scheduled Task, IIS frontend path, and backend listener to the exact split predecessor. No database migration or downgrade is run.

Run the independent post-cutover evidence check:

```powershell
.\VERIFY-UAT-Shipment-Summary-RC1-4c96ea4.ps1
```

Expected markers are `IIS_TARGET=PASS`, `TASK_TARGET=PASS`, `LISTENER_TARGET=PASS`, `HEALTH=PASS`, `PING=PASS`, and `RELEASE_IDENTITY_MATCH=YES`.
