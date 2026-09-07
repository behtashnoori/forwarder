[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$EnvironmentFile,[Parameter(Mandatory=$true)][string]$BackupIdentity,[switch]$ConfirmStagingMigration)
$ErrorActionPreference='Stop'
if(-not $ConfirmStagingMigration){throw 'MIGRATION_DENIED: pass -ConfirmStagingMigration only after backup confirmation'}
if(-not(Test-Path -LiteralPath $EnvironmentFile) -or [string]::IsNullOrWhiteSpace($BackupIdentity)){throw 'MIGRATION_DENIED: environment file or backup identity is missing'}
$env:APP_ENV='staging'; . $EnvironmentFile
if($env:APP_ENV -notin @('staging','uat') -or $env:PORT -eq '5101'){throw 'MIGRATION_DENIED: target is ambiguous or production-like'}
python -m alembic -c backend/migrations/alembic.ini upgrade 20260915_project_access_foundation
python -m alembic -c backend/migrations/alembic.ini current
