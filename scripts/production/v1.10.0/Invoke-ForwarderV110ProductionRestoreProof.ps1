#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$BackupEvidencePath,
    [string]$DumpPath,
    [string]$PackagePath,
    [ValidatePattern('^$|^[0-9a-fA-F]{64}$')][string]$ExpectedPackageSha256,
    [string]$EvidenceDirectory,
    [string]$WorkRoot = 'D:\1-webapp\forwarder-v1.10.0-restore-proof-work',
    [string]$PgBin = 'C:\Program Files\PostgreSQL\18\bin',
    [string]$LocalHost = '127.0.0.1',
    [ValidateRange(1,65535)][int]$LocalPort = 5432,
    [string]$LocalAdminUser = 'postgres',
    [string]$LocalMaintenanceDatabase = 'postgres',
    [ValidateRange(1,24)][int]$MaximumBackupAgeHours = 8,
    [switch]$Execute,
    [switch]$ConfirmDisposableRestore,
    [switch]$ToolingSelfTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ExpectedBefore = '20260921_shipment_evidence_ownership'
$ExpectedTarget = '20260926_fixed_shipment_responsible_expert'
$ExpectedSource = 'e36ee7cee157657c97dc42a539eaf1909f510a33'
$MigrationSequence = @(
    '20260922_notification_foundation',
    '20260923_notification_lifecycle',
    '20260924_request_cargo_items',
    '20260925_quote_communication',
    '20260926_fixed_shipment_responsible_expert'
)

function Stop-RestoreProof([string]$Message) { throw "RESTORE_PROOF_BLOCKED: $Message" }

function Need([bool]$Condition, [string]$Message) {
    if (-not $Condition) { Stop-RestoreProof $Message }
}

function Get-TextSha256([string]$Value) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($algorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)))).Replace('-', '').ToLowerInvariant()
    } finally { $algorithm.Dispose() }
}

function Invoke-LocalTool(
    [string]$File,
    [string]$Arguments,
    [string]$Password,
    [int]$TimeoutSeconds,
    [string]$StandardInput = '',
    [hashtable]$Environment = @{},
    [string]$WorkingDirectory = ''
) {
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $File; $start.Arguments = $Arguments
    $start.UseShellExecute = $false; $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true; $start.RedirectStandardError = $true
    $start.RedirectStandardInput = -not [string]::IsNullOrEmpty($StandardInput)
    if ($WorkingDirectory) { $start.WorkingDirectory = $WorkingDirectory }
    if ($Password) { $start.EnvironmentVariables['PGPASSWORD'] = $Password }
    foreach ($key in $Environment.Keys) { $start.EnvironmentVariables[$key] = [string]$Environment[$key] }
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        Need ($process.Start()) 'local tool did not start'
        if ($start.RedirectStandardInput) { $process.StandardInput.Write($StandardInput); $process.StandardInput.Close() }
        $stdout = $process.StandardOutput.ReadToEndAsync(); $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            Stop-RestoreProof 'local tool timeout'
        }
        return [pscustomobject]@{ ExitCode=$process.ExitCode; Stdout=[string]$stdout.Result; Stderr=[string]$stderr.Result }
    } finally {
        if ($start.EnvironmentVariables.ContainsKey('PGPASSWORD')) { $start.EnvironmentVariables.Remove('PGPASSWORD') }
        if ($start.EnvironmentVariables.ContainsKey('DATABASE_URL')) { $start.EnvironmentVariables.Remove('DATABASE_URL') }
        $process.Dispose()
    }
}

function Invoke-Psql([string]$Database, [string]$Sql, [string]$Password) {
    $arguments = '-X -w -q -A -t -F "|" -v ON_ERROR_STOP=1 -h "' + $LocalHost + '" -p ' + $LocalPort + ' -U "' + $LocalAdminUser + '" -d "' + $Database + '"'
    $result = Invoke-LocalTool (Join-Path $PgBin 'psql.exe') $arguments $Password 300 $Sql
    Need ($result.ExitCode -eq 0) 'read-only SQL validation failed'
    return @($result.Stdout -split "`r?`n" | Where-Object { $_ -match '\S' })
}

function Assert-PassRows([string[]]$Rows, [string]$Stage) {
    Need (@($Rows).Count -gt 0) "$Stage returned no checks"
    foreach ($row in @($Rows)) {
        $parts = $row.Split('|', 3)
        $code = if ($parts.Count -gt 0) { $parts[0] } else { 'INVALID_RESULT' }
        Need ($parts.Count -eq 3 -and $parts[1] -eq 'PASS') "$Stage blocked: $code"
    }
}

function Assert-ExtractedPackage([string]$Root) {
    $expected = @{}
    foreach ($line in Get-Content -LiteralPath (Join-Path $Root 'SHA256SUMS.txt')) {
        $parts = $line -split '  ', 2
        Need ($parts.Count -eq 2 -and $parts[0] -match '^[0-9a-f]{64}$') 'extracted checksum syntax invalid'
        $expected[$parts[1]] = $parts[0]
        $path = Join-Path $Root $parts[1].Replace('/', '\')
        Need (Test-Path -LiteralPath $path -PathType Leaf) 'extracted package file missing'
        Need ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $parts[0]) 'extracted package checksum mismatch'
    }
    $actual = @(Get-ChildItem -LiteralPath $Root -Recurse -File | ForEach-Object {
        $_.FullName.Substring($Root.TrimEnd('\').Length + 1).Replace('\','/')
    } | Where-Object { $_ -ne 'SHA256SUMS.txt' })
    Need (@($actual | Where-Object { -not $expected.ContainsKey($_) }).Count -eq 0) 'unexpected extracted package file'
}

function Invoke-PackageMigration([string]$Python, [string[]]$Arguments, [string]$DatabaseUrl) {
    $quoted = ($Arguments | ForEach-Object { '"' + $_.Replace('"','\"') + '"' }) -join ' '
    $environment = @{
        DATABASE_URL=$DatabaseUrl; APP_ENV='uat'; ENV='uat'; FLASK_ENV='uat'
        AUTO_MIGRATE_ON_STARTUP='false'; DB_CONNECT_TIMEOUT_SECONDS='10'
    }
    $packageRoot = Split-Path -Parent (Split-Path -Parent $Python)
    $result = Invoke-LocalTool -File $Python -Arguments $quoted -Password '' -TimeoutSeconds 900 -Environment $environment -WorkingDirectory $packageRoot
    Need ($result.ExitCode -eq 0) 'package migration command failed'
    return [string]$result.Stdout
}

function Remove-OwnedDatabase([string]$Name, [string]$Password) {
    Need ($Name -match '^forwarder_v110_restoreproof_[0-9]{14}_[0-9a-f]{8}$') 'refusing unsafe disposable database cleanup'
    $arguments = '--if-exists --maintenance-db="' + $LocalMaintenanceDatabase + '" -h "' + $LocalHost + '" -p ' + $LocalPort + ' -U "' + $LocalAdminUser + '" "' + $Name + '"'
    $dropped = Invoke-LocalTool (Join-Path $PgBin 'dropdb.exe') $arguments $Password 120
    Need ($dropped.ExitCode -eq 0) 'disposable database cleanup failed'
}

function Invoke-ToolingSelfTest {
    foreach ($relative in @('sql\migration-compatibility-readonly.sql','sql\adr047-production-classifier.sql','sql\post-migration-assertions-readonly.sql')) {
        $path = Join-Path $PSScriptRoot $relative
        Need (Test-Path -LiteralPath $path -PathType Leaf) 'restore-proof SQL payload missing'
        $sql = Get-Content -Raw -LiteralPath $path
        Need ($sql -match '(?is)^\s*BEGIN\s+TRANSACTION\s+READ\s+ONLY\s*;' -and $sql -match '(?is)COMMIT\s*;\s*$') 'restore-proof SQL envelope invalid'
    }
    Need (($MigrationSequence -join '|') -eq '20260922_notification_foundation|20260923_notification_lifecycle|20260924_request_cargo_items|20260925_quote_communication|20260926_fixed_shipment_responsible_expert') 'migration sequence invalid'
    Write-Output 'ISOLATED_RESTORE_TARGET=DISPOSABLE_ONLY'
    Write-Output 'FIVE_MIGRATION_SEQUENCE=EXACT'
    Write-Output 'PRODUCTION_ACCESS_PERFORMED=NO'
}

if ($ToolingSelfTest) { Invoke-ToolingSelfTest; exit 0 }
Need $Execute 'explicit execute mode required'
Need $ConfirmDisposableRestore 'explicit disposable restore confirmation required'
foreach ($value in @($BackupEvidencePath,$DumpPath,$PackagePath,$ExpectedPackageSha256,$EvidenceDirectory)) {
    Need (-not [string]::IsNullOrWhiteSpace($value)) 'required argument missing'
}
Need ($LocalHost -match '^[A-Za-z0-9_.-]+$' -and $LocalAdminUser -match '^[A-Za-z0-9_.-]+$' -and $LocalMaintenanceDatabase -match '^[A-Za-z0-9_.-]+$') 'local PostgreSQL identity invalid'
foreach ($file in @($BackupEvidencePath,$DumpPath,$PackagePath,(Join-Path $PSScriptRoot 'Verify-ForwarderV110ProductionPackage.ps1'))) {
    Need (Test-Path -LiteralPath $file -PathType Leaf) 'required input file missing'
}
foreach ($file in @('psql.exe','pg_restore.exe','createdb.exe','dropdb.exe')) {
    Need (Test-Path -LiteralPath (Join-Path $PgBin $file) -PathType Leaf) 'PostgreSQL 18 tool missing'
}
Need (Test-Path -LiteralPath $EvidenceDirectory -PathType Container) 'evidence directory must already exist'
if (-not (Test-Path -LiteralPath $WorkRoot -PathType Container)) { New-Item -ItemType Directory -Path $WorkRoot -ErrorAction Stop | Out-Null }

$backupEvidence = Get-Content -Raw -LiteralPath $BackupEvidencePath -ErrorAction Stop | ConvertFrom-Json
Need ($backupEvidence.schema -eq 'forwarder-v1.10.0-predeployment-backup-evidence-v2' -and $backupEvidence.status -eq 'PASS' -and [bool]$backupEvidence.verified) 'backup evidence invalid'
Need ($backupEvidence.production_host -eq 'SRV8756807400' -and $backupEvidence.product_version -eq '1.10.0') 'backup source identity invalid'
Need ($backupEvidence.database_revision -eq $ExpectedBefore -and [int]$backupEvidence.alembic_revision_count -eq 1 -and $backupEvidence.database_state -eq 'PRIMARY') 'backup baseline database identity invalid'
Need ($backupEvidence.dump_format -eq 'custom' -and $backupEvidence.catalog_verification -eq 'PASS' -and [int]$backupEvidence.pg_restore_list_exit_code -eq 0) 'backup catalog contract invalid'
Need (-not [bool]$backupEvidence.production_database_mutated -and -not [bool]$backupEvidence.production_deployment_performed) 'backup mutation declaration invalid'
$backupAge = ([DateTime]::UtcNow - [DateTime]::Parse([string]$backupEvidence.created_utc).ToUniversalTime()).TotalHours
Need ($backupAge -ge 0 -and $backupAge -le $MaximumBackupAgeHours) 'backup is outside the approved freshness window'
$actualDump = Get-Item -LiteralPath $DumpPath
$actualHash = (Get-FileHash -LiteralPath $DumpPath -Algorithm SHA256).Hash.ToLowerInvariant()
Need ($actualDump.Length -gt 0 -and $actualDump.Length -eq [int64]$backupEvidence.dump_size_bytes -and $actualHash -eq [string]$backupEvidence.dump_sha256) 'transferred dump identity mismatch'

& (Join-Path $PSScriptRoot 'Verify-ForwarderV110ProductionPackage.ps1') -PackagePath $PackagePath -ExpectedSha256 $ExpectedPackageSha256 | Out-Null
$psqlVersion = Invoke-LocalTool (Join-Path $PgBin 'psql.exe') '--version' '' 30
$restoreVersion = Invoke-LocalTool (Join-Path $PgBin 'pg_restore.exe') '--version' '' 30
Need ($psqlVersion.ExitCode -eq 0 -and $restoreVersion.ExitCode -eq 0 -and $psqlVersion.Stdout -match '(?i)PostgreSQL\)\s+18(?:\.|\s|$)' -and $restoreVersion.Stdout -match '(?i)PostgreSQL\)\s+18(?:\.|\s|$)') 'local PostgreSQL 18 tooling required'

$securePassword = Read-Host "Local PostgreSQL 18 password for $LocalAdminUser" -AsSecureString
$passwordPointer = [IntPtr]::Zero
$plainPassword = $null
$databaseName = 'forwarder_v110_restoreproof_' + [DateTime]::UtcNow.ToString('yyyyMMddHHmmss') + '_' + ([Guid]::NewGuid().ToString('N').Substring(0,8))
$runRoot = Join-Path (Resolve-Path -LiteralPath $WorkRoot).Path ('run-' + [Guid]::NewGuid().ToString('N'))
$databaseCreated = $false
$restored = $false
$migrationPassed = $false
$postAssertions = @()
$baselineTableCount = 0L; $baselineShipmentCount = 0L; $baselineQuoteCount = 0L
try {
    $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    Need (-not [string]::IsNullOrWhiteSpace($plainPassword)) 'local PostgreSQL password is empty'
    New-Item -ItemType Directory -Path $runRoot -ErrorAction Stop | Out-Null
    $packageRoot = Join-Path $runRoot 'package'
    New-Item -ItemType Directory -Path $packageRoot -ErrorAction Stop | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::ExtractToDirectory((Resolve-Path -LiteralPath $PackagePath).Path, $packageRoot)
    Assert-ExtractedPackage $packageRoot

    $createArguments = '--maintenance-db="' + $LocalMaintenanceDatabase + '" -T template0 -E UTF8 -h "' + $LocalHost + '" -p ' + $LocalPort + ' -U "' + $LocalAdminUser + '" "' + $databaseName + '"'
    $created = Invoke-LocalTool (Join-Path $PgBin 'createdb.exe') $createArguments $plainPassword 120
    Need ($created.ExitCode -eq 0) 'disposable database creation failed'
    $databaseCreated = $true
    $restoreArguments = '--exit-on-error --single-transaction --no-owner --no-privileges -h "' + $LocalHost + '" -p ' + $LocalPort + ' -U "' + $LocalAdminUser + '" -d "' + $databaseName + '" "' + (Resolve-Path -LiteralPath $DumpPath).Path + '"'
    $restore = Invoke-LocalTool (Join-Path $PgBin 'pg_restore.exe') $restoreArguments $plainPassword 3600
    Need ($restore.ExitCode -eq 0) 'isolated restore failed'
    $restored = $true

    $identitySql = @"
BEGIN TRANSACTION READ ONLY;
SELECT current_setting('server_version'),
       (SELECT count(*) FROM alembic_version),
       (SELECT min(version_num) FROM alembic_version),
       (SELECT count(*) FROM information_schema.tables WHERE table_schema='public'),
       (SELECT count(*) FROM operational_shipment),
       (SELECT count(*) FROM expert_quote);
COMMIT;
"@
    $identityRows = @(Invoke-Psql $databaseName $identitySql $plainPassword)
    Need ($identityRows.Count -eq 1) 'restored baseline identity result invalid'
    $identity = $identityRows[0].Split('|')
    Need ($identity.Count -eq 6 -and $identity[0] -match '^18(?:\.|$)' -and [int]$identity[1] -eq 1 -and $identity[2] -eq $ExpectedBefore) 'restored baseline identity mismatch'
    Need ([int64]::TryParse($identity[3],[ref]$baselineTableCount) -and [int64]::TryParse($identity[4],[ref]$baselineShipmentCount) -and [int64]::TryParse($identity[5],[ref]$baselineQuoteCount)) 'restored aggregate counts invalid'
    $baselineChecks = @(Invoke-Psql $databaseName (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'sql\migration-compatibility-readonly.sql')) $plainPassword)
    Assert-PassRows $baselineChecks 'baseline compatibility'
    $baselineAdr = @(Invoke-Psql $databaseName (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'sql\adr047-production-classifier.sql')) $plainPassword)
    Need ($baselineAdr.Count -eq 1) 'baseline ADR-047 result invalid'
    $baselineAdrParts = $baselineAdr[0].Split('|')
    Need ($baselineAdrParts.Count -eq 5 -and [int64]$baselineAdrParts[1] -eq 0 -and [int64]$baselineAdrParts[2] -eq 0 -and [int64]$baselineAdrParts[3] -eq 0 -and [int64]$baselineAdrParts[4] -eq 0) 'baseline ADR-047 unresolved rows present'

    $encodedPassword = [Uri]::EscapeDataString($plainPassword)
    $databaseUrl = 'postgresql+psycopg2://' + $LocalAdminUser + ':' + $encodedPassword + '@' + $LocalHost + ':' + $LocalPort + '/' + $databaseName
    $python = Join-Path $packageRoot 'runtime\python.exe'
    $beforeOutput = Invoke-PackageMigration $python @('-m','backend.migration_cli','current') $databaseUrl
    Need ($beforeOutput -match ('current=' + [regex]::Escape($ExpectedBefore))) 'package runtime did not confirm baseline revision'
    Invoke-PackageMigration $python @('-m','backend.migration_cli','upgrade',$ExpectedTarget,'--confirm') $databaseUrl | Out-Null
    $afterOutput = Invoke-PackageMigration $python @('-m','backend.migration_cli','current') $databaseUrl
    Need ($afterOutput -match ('current=' + [regex]::Escape($ExpectedTarget)) -and $afterOutput -match ('heads=' + [regex]::Escape($ExpectedTarget)) -and $afterOutput -match 'pending=no') 'target migration identity mismatch'
    Invoke-PackageMigration $python @('-m','backend.migration_cli','check') $databaseUrl | Out-Null
    $postAssertions = @(Invoke-Psql $databaseName (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'sql\post-migration-assertions-readonly.sql')) $plainPassword)
    Assert-PassRows $postAssertions 'post-migration assertions'
    $postAdr = @(Invoke-Psql $databaseName (Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'sql\adr047-production-classifier.sql')) $plainPassword)
    Need ($postAdr.Count -eq 1) 'post-migration ADR-047 result invalid'
    $postAdrParts = $postAdr[0].Split('|')
    Need ($postAdrParts.Count -eq 5 -and [int64]$postAdrParts[1] -eq 0 -and [int64]$postAdrParts[2] -eq 0 -and [int64]$postAdrParts[3] -eq 0 -and [int64]$postAdrParts[4] -eq 0) 'post-migration ADR-047 unresolved rows present'
    $migrationPassed = $true
} finally {
    $cleanupError = $null
    if ($databaseCreated) {
        try { Remove-OwnedDatabase $databaseName $plainPassword } catch { $cleanupError = $_ }
    }
    if (Test-Path -LiteralPath $runRoot -PathType Container) {
        try {
            $resolvedWork = (Resolve-Path -LiteralPath $WorkRoot).Path.TrimEnd('\')
            $resolvedRun = (Resolve-Path -LiteralPath $runRoot).Path
            Need ($resolvedRun.StartsWith($resolvedWork + '\run-', [StringComparison]::OrdinalIgnoreCase)) 'refusing unsafe work cleanup'
            [IO.Directory]::Delete($resolvedRun, $true)
        } catch { if ($null -eq $cleanupError) { $cleanupError = $_ } }
    }
    if ($passwordPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer) }
    $plainPassword = $null; $securePassword = $null; $databaseUrl = $null
    if ($null -ne $cleanupError) { throw $cleanupError }
}

Need ($restored -and $migrationPassed) 'restore proof did not complete'
$testedUtc = [DateTime]::UtcNow
$resultPath = Join-Path (Resolve-Path -LiteralPath $EvidenceDirectory).Path (([IO.Path]::GetFileName($DumpPath)) + '.restore-evidence.json')
Need (-not (Test-Path -LiteralPath $resultPath)) 'restore evidence output collision'
$record = [ordered]@{
    schema='forwarder-production-restore-evidence-v1'; restore_test_status='PASS'; tested_utc=$testedUtc.ToString('o')
    source_dump_sha256=$actualHash; source_dump_size_bytes=$actualDump.Length
    source_database_revision=$ExpectedBefore; restored_database_disposable=$true; disposable_database_removed=$true
    local_postgresql_major=18; restored_database_name_sha256=(Get-TextSha256 $databaseName)
    baseline_compatibility='PASS'; baseline_public_table_count=$baselineTableCount
    baseline_operational_shipment_count=$baselineShipmentCount; baseline_expert_quote_count=$baselineQuoteCount
    migration_sequence=$MigrationSequence; production_derived_migration_rehearsal='PASS'
    target_database_revision=$ExpectedTarget; target_alembic_head_count=1; pending_migrations=$false
    post_migration_assertions='PASS'; post_migration_assertion_count=@($postAssertions).Count
    adr047_production_data='PASS'; notification_migration_rows=0; synthetic_historical_cargo_rows=0
    target_application_source=$ExpectedSource; package_sha256=$ExpectedPackageSha256.ToLowerInvariant()
    production_accessed=$false; production_database_mutated=$false; production_deployment_performed=$false
    customer_rows_emitted=$false; credentials_emitted=$false; reference_impact='NONE'
}
$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($resultPath, (($record | ConvertTo-Json -Depth 8) + "`n"), $utf8)
Write-Output 'ISOLATED_RESTORE=PASS'
Write-Output 'PRODUCTION_DERIVED_MIGRATION_REHEARSAL=PASS'
Write-Output ('TARGET_MIGRATION_HEAD=' + $ExpectedTarget)
Write-Output 'ADR047_PRODUCTION_DATA=PASS'
Write-Output ('RESTORE_EVIDENCE=' + $resultPath)
Write-Output 'PRODUCTION_DATABASE_MUTATED=NO'
Write-Output 'PRODUCTION_DEPLOYMENT_PERFORMED=NO'
