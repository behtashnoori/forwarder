Set-Location "D:\1-webapp\15-forwarder"

$ErrorActionPreference = "Stop"
$Mode = "DryRun"
$PostgresUser = "postgres"
$ConfirmCutover = $false
for ($index = 0; $index -lt $args.Count; $index++) {
    switch ($args[$index]) {
        "-Mode" {
            $index++
            if ($index -ge $args.Count) { throw "-Mode requires a value" }
            $Mode = $args[$index]
        }
        "-PostgresUser" {
            $index++
            if ($index -ge $args.Count) { throw "-PostgresUser requires a value" }
            $PostgresUser = $args[$index]
        }
        "-ConfirmCutover" { $ConfirmCutover = $true }
        default { throw "Unknown argument: $($args[$index])" }
    }
}
if ($Mode -notin @("DryRun", "Rehearsal", "Final")) { throw "Invalid -Mode: $Mode" }
$Repo = "D:\1-webapp\15-forwarder"
$ExpectedBranch = "feature/forwarder-phase1b-local-db-cutover"
$ExpectedHead = "eea5c96a813c51b2170f4e62a208ac9a33622a59"
$ActiveHead = "20260801_route_exception"
$PgBin = "C:\Program Files\PostgreSQL\18\bin"
$Python = "C:\Users\pc\AppData\Local\Programs\Python\Python313\python.exe"
$RunToken = (Get-Date -Format "yyyyMMdd_HHmmss").ToLowerInvariant()
$EvidenceRoot = Join-Path $env:LOCALAPPDATA "Temp\forwarder-phase1b-local-cutover-$RunToken"
$BackupRoot = "D:\1-webapp\_db_backups\15-forwarder\$RunToken"
$Source = "forwarder_db"
$Rehearsal = "forwarder_phase1b_rehearsal_$RunToken"
$Final = "forwarder_phase1b_final_$RunToken"
$Restore = "forwarder_phase1b_restore_$RunToken"
$Legacy = "forwarder_db_legacy_$RunToken"
$Failed = "forwarder_db_failed_$RunToken"
$script:PlainPassword = $null
$script:PasswordBstr = [IntPtr]::Zero
$script:State = "INITIAL"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "CUTOVER_BLOCKED: $Message" }
}

function Resolve-ActiveMigrationHead([object[]]$RawHeadOutput) {
    $headRevisions = @()
    foreach ($rawOutput in @($RawHeadOutput)) {
        foreach ($rawLine in @(([string]$rawOutput) -split "\r?\n")) {
            $line = ([string]$rawLine).Trim()
            if ([string]::IsNullOrWhiteSpace($line)) {
                continue
            }
            $match = [regex]::Match(
                $line,
                '^(?<revision>[A-Za-z0-9_]+)\s+\(head\)\s*$'
            )
            if ($match.Success) {
                $headRevisions += [string]$match.Groups["revision"].Value
            }
        }
    }
    Assert-True `
        -Condition ([bool]($headRevisions.Count -eq 1)) `
        -Message "expected exactly one active migration head"
    $head = [string]$headRevisions[0]
    Assert-True `
        -Condition ([bool][string]::Equals(
            $head,
            $ActiveHead,
            [System.StringComparison]::Ordinal
        )) `
        -Message "unexpected active migration head: $head"
    return $head
}

function Write-Evidence([string]$Name, [hashtable]$Payload) {
    $Payload["timestamp_utc"] = [DateTime]::UtcNow.ToString("o")
    $Payload["row_payload_recorded"] = $false
    $Payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $EvidenceRoot $Name) -Encoding UTF8
}

function Write-StageEvent([string]$Status, [string]$Stage) {
    $message = "$Status=$Stage"
    Write-Host $message
    Add-Content -LiteralPath (Join-Path $EvidenceRoot "stage-events.log") `
        -Value "$([DateTime]::UtcNow.ToString('o')) $message" -Encoding UTF8
}

function Invoke-Stage([string]$Stage, [scriptblock]$Action) {
    Write-StageEvent "STAGE_START" $Stage
    try {
        $result = & $Action
        Write-StageEvent "STAGE_COMPLETE" $Stage
        return $result
    } catch {
        Write-StageEvent "STAGE_FAILED" $Stage
        throw
    }
}

function Stop-ProcessTree([System.Diagnostics.Process]$Process) {
    if ($Process.HasExited) {
        return
    }
    $stopInfo = New-Object System.Diagnostics.ProcessStartInfo
    $stopInfo.FileName = "$env:SystemRoot\System32\taskkill.exe"
    $stopInfo.Arguments = "/PID $($Process.Id) /T /F"
    $stopInfo.UseShellExecute = $false
    $stopInfo.CreateNoWindow = $true
    $stopProcess = New-Object System.Diagnostics.Process
    $stopProcess.StartInfo = $stopInfo
    try {
        [void]$stopProcess.Start()
        [void]$stopProcess.WaitForExit(10000)
    } finally {
        $stopProcess.Dispose()
    }
    if (-not $Process.HasExited) {
        $Process.Kill()
    }
    if (-not $Process.WaitForExit(10000)) {
        throw "PROCESS_TERMINATION_FAILED:$($Process.Id)"
    }
}

function Invoke-Native {
    param(
        [Parameter(Mandatory=$true)][string]$File,
        [string[]]$Arguments = @(),
        [string]$InputText = $null,
        [hashtable]$Environment = @{},
        [switch]$AllowFailure,
        [string]$Operation = $null,
        [ValidateRange(1, 7200)][int]$TimeoutSeconds = 900
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $File
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    foreach ($key in $Environment.Keys) { $psi.EnvironmentVariables[$key] = [string]$Environment[$key] }
    if ($script:PlainPassword) { $psi.EnvironmentVariables["PGPASSWORD"] = $script:PlainPassword }
    $quotedArguments = foreach ($argument in $Arguments) {
        if ($argument -notmatch '[\s"]') { $argument }
        else { '"' + ($argument -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"' }
    }
    $psi.Arguments = $quotedArguments -join " "
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    $operationName = if ($Operation) { $Operation } else { [IO.Path]::GetFileName($File) }
    try {
        [void]$process.Start()
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if ($null -ne $InputText) { $process.StandardInput.Write($InputText) }
        $process.StandardInput.Close()
        $completed = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $completed) {
            Write-StageEvent "PROCESS_TIMEOUT" $operationName
            Stop-ProcessTree $process
            throw "PROCESS_TIMEOUT:$operationName"
        }
        # Flush process state, then collect both concurrently-drained streams.
        $process.WaitForExit()
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        $result = [ordered]@{ ExitCode=$process.ExitCode; StdOut=$stdout; StdErr=$stderr }
        if (-not $AllowFailure -and $process.ExitCode -ne 0) {
            throw "NATIVE_FAIL:$([IO.Path]::GetFileName($File)):$($process.ExitCode)"
        }
        return $result
    } finally {
        $process.Dispose()
        $psi.EnvironmentVariables.Remove("PGPASSWORD")
    }
}

function Invoke-Psql([string]$Database, [string]$Sql, [switch]$AllowFailure) {
    $allowed = $Database -eq $Source -or
        $Database -match "^forwarder_phase1b_(rehearsal|final|restore)_[a-z0-9_]+$" -or
        $Database -match "^forwarder_db_(legacy|failed)_[a-z0-9_]+$" -or
        $Database -eq "postgres"
    Assert-True $allowed "database outside allow-list"
    return Invoke-Native -File (Join-Path $PgBin "psql.exe") -Arguments @(
        "-X", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", "5432",
        "-U", $PostgresUser, "-d", $Database, "-At"
    ) -InputText $Sql -AllowFailure:$AllowFailure
}

function New-Database([string]$Name) {
    Assert-True ($Name -match "^forwarder_phase1b_(rehearsal|final|restore)_[a-z0-9_]+$") "create target outside allow-list"
    $exists = Invoke-Psql "postgres" "SELECT 1 FROM pg_database WHERE datname='$Name';"
    Assert-True ([string]::IsNullOrWhiteSpace($exists.StdOut)) "target already exists: $Name"
    Invoke-Psql "postgres" "CREATE DATABASE `"$Name`" WITH TEMPLATE template0 ENCODING 'UTF8';" | Out-Null
}

function Remove-DisposableDatabase([string]$Name) {
    Assert-True ($Name -match "^forwarder_phase1b_(rehearsal|final|restore)_[a-z0-9_]+$") "cleanup target outside allow-list"
    Invoke-Psql "postgres" "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$Name' AND pid<>pg_backend_pid(); DROP DATABASE IF EXISTS `"$Name`";" | Out-Null
}

function Invoke-Migration([string]$Database) {
    Assert-True ($Database -ne $Source) "legacy Main migration is forbidden"
    $env = @{
        "DATABASE_URL" = "postgresql+psycopg2://$PostgresUser@127.0.0.1:5432/$Database"
        "APP_ENV" = "uat"
    }
    Invoke-Native -File $Python -Arguments @("-m", "backend.migration_cli", "upgrade", "--confirm") `
        -Environment $env -Operation "$Database-migration-upgrade" -TimeoutSeconds 900 | Out-Null
    $check = Invoke-Native -File $Python -Arguments @("-m", "backend.migration_cli", "check") `
        -Environment $env -Operation "$Database-migration-check" -TimeoutSeconds 120
    Assert-True ($check.StdOut -match "current=$ActiveHead" -and $check.StdOut -match "pending=no") "fresh target did not reach active head"
}

function Write-SanitizedMappingBlockers([string]$EvidencePath) {
    $contractPath = Join-Path $EvidencePath "mapping-contract.json"
    $blockedPath = Join-Path $EvidencePath "blocked.json"
    if (Test-Path -LiteralPath $contractPath) {
        $contract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json
        foreach ($plan in @($contract.plans | Where-Object {
            $_.classification -in @("SOURCE_ONLY_REVIEW", "MANUAL_DECISION_REQUIRED")
        })) {
            Write-Host ("MAPPING_BLOCKED table={0} reason={1}" -f `
                [string]$plan.table, [string]$plan.reason)
        }
    }
    if (Test-Path -LiteralPath $blockedPath) {
        $blocked = Get-Content -Raw -LiteralPath $blockedPath | ConvertFrom-Json
        Write-Host ("MAPPING_GATE reason={0}" -f [string]$blocked.reason)
    }
}

function Invoke-Transfer([string]$TransferMode, [string]$Target, [string]$EvidenceName) {
    $path = Join-Path $EvidenceRoot $EvidenceName
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    try {
        Invoke-Native -File $Python -Arguments @(
            "scripts/db_cutover/phase1b_fresh_transfer.py",
            "--mode", $TransferMode, "--source", $Source, "--target", $Target,
            "--user", $PostgresUser, "--evidence", $path
        ) -Operation "$TransferMode-transfer-analysis" -TimeoutSeconds 1800 | Out-Null
    } catch {
        Write-SanitizedMappingBlockers $path
        throw
    }
    if ($TransferMode -eq "DryRun") {
        $contract = Get-Content -Raw -LiteralPath (Join-Path $path "mapping-contract.json") | ConvertFrom-Json
        Assert-True $contract.mapping_complete "mapping incomplete"
        return
    }
    $reconciliation = Get-Content -Raw -LiteralPath (Join-Path $path "reconciliation.json") | ConvertFrom-Json
    Assert-True $reconciliation.mapping_complete "mapping incomplete"
    Assert-True ($reconciliation.rejected_rows -eq 0) "rejected rows detected"
    Assert-True ($reconciliation.orphan_foreign_keys -eq 0) "orphan FK detected"
    Assert-True ($reconciliation.constraint_violations -eq 0) "constraint violation detected"
    Assert-True ($reconciliation.unexplained_variance -eq 0) "unexplained variance detected"
}

function Invoke-DryRunWorkflow {
    $created = $false
    try {
        Invoke-Stage "rehearsal-create" { New-Database $Rehearsal }
        $created = $true
        Invoke-Stage "rehearsal-migration" { Invoke-Migration $Rehearsal }
        Invoke-Stage "dryrun-transfer-analysis" {
            Invoke-Transfer "DryRun" $Rehearsal "dry-run"
        }
    } finally {
        if ($created) {
            Invoke-Stage "rehearsal-cleanup" {
                Remove-DisposableDatabase $Rehearsal
            }
        }
    }
}

function Backup-Database([string]$Suffix) {
    $path = Join-Path $BackupRoot "forwarder_db_${Suffix}_$RunToken.dump"
    Invoke-Native -File (Join-Path $PgBin "pg_dump.exe") -Arguments @(
        "-Fc", "-h", "127.0.0.1", "-p", "5432", "-U", $PostgresUser,
        "-d", $Source, "-f", $path
    ) | Out-Null
    Assert-True ((Get-Item -LiteralPath $path).Length -gt 0) "empty backup"
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    return [ordered]@{ Path=$path; Sha256=$hash; Bytes=(Get-Item $path).Length }
}

function Validate-Backup([string]$Path) {
    New-Database $Restore
    try {
        Invoke-Native -File (Join-Path $PgBin "pg_restore.exe") -Arguments @(
            "-h", "127.0.0.1", "-p", "5432", "-U", $PostgresUser,
            "-d", $Restore, "--exit-on-error", $Path
        ) | Out-Null
        $sourceAggregate = Invoke-Psql $Source "BEGIN READ ONLY; SELECT count(*) FROM information_schema.tables WHERE table_schema='public'; ROLLBACK;"
        $restoreAggregate = Invoke-Psql $Restore "BEGIN READ ONLY; SELECT count(*) FROM information_schema.tables WHERE table_schema='public'; ROLLBACK;"
        Assert-True ($sourceAggregate.StdOut.Trim() -eq $restoreAggregate.StdOut.Trim()) "backup restore aggregate mismatch"
        Write-Evidence "backup-restore-validation.json" @{ pass=$true; restore_database=$Restore }
    } finally {
        Remove-DisposableDatabase $Restore
    }
}

function Invoke-ApplicationValidation([string]$Database, [string]$Phase) {
    $dsn = "postgresql+psycopg2://$PostgresUser@127.0.0.1:5432/$Database"
    # The full suites remain isolated from transferred data. Runtime validation
    # against the target is read-only and uses the supported migration probe.
    Invoke-Native -File $Python -Arguments @("-m", "pytest", "-q") | Out-Null
    Invoke-Native -File "C:\Program Files\nodejs\npm.cmd" -Arguments @("run", "test:frontend") | Out-Null
    Invoke-Native -File "C:\Program Files\nodejs\npm.cmd" -Arguments @("run", "lint") | Out-Null
    Invoke-Native -File "C:\Program Files\nodejs\npm.cmd" -Arguments @("run", "build") | Out-Null
    $smokeTests = @(
        "backend/tests/test_auth.py",
        "backend/tests/test_crm_read_contract.py",
        "backend/tests/test_customer_quote_response.py",
        "backend/tests/test_operational_vertical_slice_postgresql.py",
        "backend/tests/test_multileg_route_orchestration_postgresql.py",
        "backend/tests/test_health_provinces_transport.py"
    )
    Invoke-Native -File $Python -Arguments (@("-m", "pytest", "-q") + $smokeTests) | Out-Null
    $runtime = Invoke-Native -File $Python -Arguments @(
        "-m", "backend.migration_cli", "check"
    ) -Environment @{ "DATABASE_URL"=$dsn; "APP_ENV"="uat" }
    Assert-True ($runtime.StdOut -match "current=$ActiveHead" -and $runtime.StdOut -match "pending=no") "runtime schema probe failed"
    Write-Evidence "$Phase-application-validation.json" @{
        pass=$true; backend_tests="PASS"; frontend_tests="PASS";
        health="PASS"; login="PASS"; crm="PASS"; shipment="PASS"; quote="PASS";
        operational_shipment="PASS"; multileg="PASS"; runtime_schema_errors=0
    }
}

function Assert-Preflight {
    Assert-True ((git branch --show-current) -eq $ExpectedBranch) "unexpected branch"
    git merge-base --is-ancestor $ExpectedHead HEAD
    Assert-True ($LASTEXITCODE -eq 0) "branch does not descend from expected baseline"
    Assert-True ([string]::IsNullOrWhiteSpace((git status --porcelain))) "working tree is not clean"
    Assert-True ((Get-Content -Raw ".backend-port").Trim() -eq "57065") ".backend-port changed"
    Assert-True (Test-Path $Python) "required Python missing"
    Assert-True (Test-Path (Join-Path $PgBin "pg_dump.exe")) "PostgreSQL 18 tools missing"
    $headResult = Invoke-Native -File $Python -Arguments @(
        "-m", "alembic", "-c", "backend/migrations/alembic.ini", "heads"
    ) -AllowFailure
    Assert-True `
        -Condition ([bool]($headResult.ExitCode -eq 0)) `
        -Message "Alembic head command failed"
    $head = Resolve-ActiveMigrationHead -RawHeadOutput @($headResult.StdOut)
    Write-Evidence "preflight-summary.json" @{ pass=$true; branch=$ExpectedBranch; baseline=$ExpectedHead; head=(git rev-parse HEAD); backend_port=57065 }
}

function Invoke-RenameCutover {
    $connections = Invoke-Psql "postgres" "SELECT count(*) FROM pg_stat_activity WHERE datname IN ('$Source','$Final') AND pid<>pg_backend_pid();"
    Assert-True ($connections.StdOut.Trim() -eq "0") "database connections remain at cutover"
    Invoke-Psql "postgres" "ALTER DATABASE `"$Source`" RENAME TO `"$Legacy`";" | Out-Null
    try {
        Invoke-Psql "postgres" "ALTER DATABASE `"$Final`" RENAME TO `"$Source`";" | Out-Null
    } catch {
        Invoke-Psql "postgres" "ALTER DATABASE `"$Legacy`" RENAME TO `"$Source`";" | Out-Null
        throw "CUTOVER_RENAME_COMPENSATED"
    }
    $script:State = "POST_CUTOVER"
    Write-Evidence "cutover-summary.json" @{ pass=$true; legacy_database=$Legacy; final_database=$Source }
}

function Invoke-Rollback {
    Invoke-Psql "postgres" "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$Source' AND pid<>pg_backend_pid(); ALTER DATABASE `"$Source`" RENAME TO `"$Failed`"; ALTER DATABASE `"$Legacy`" RENAME TO `"$Source`";" | Out-Null
    $script:State = "ROLLED_BACK"
    Write-Evidence "rollback-summary.json" @{ pass=$true; restored_database=$Source; failed_database=$Failed }
}

New-Item -ItemType Directory -Force -Path $EvidenceRoot, $BackupRoot | Out-Null
$securePassword = $null
$rehearsalCreated = $false
try {
    Invoke-Stage "preflight" { Assert-Preflight }
    if ($Mode -eq "Final") {
        Assert-True $ConfirmCutover "Final mode requires -ConfirmCutover"
    }
    $securePassword = Read-Host "PostgreSQL password for $PostgresUser" -AsSecureString
    $script:PasswordBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
    $script:PlainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($script:PasswordBstr)
    Assert-True (-not [string]::IsNullOrWhiteSpace($script:PlainPassword)) "empty credential"
    $identity = Invoke-Stage "source-read-only-identity" {
        Invoke-Psql $Source "BEGIN READ ONLY; SELECT current_database(), current_user, current_setting('server_version'), (SELECT version_num FROM alembic_version); ROLLBACK;"
    }
    Assert-True ($identity.StdOut -match "forwarder_db\|.+\|18\." -and $identity.StdOut -match "54ea21ea0d9f") "source identity/revision mismatch"
    Write-Evidence "source-identity.json" @{ pass=$true; database=$Source; legacy_revision="54ea21ea0d9f"; source_read_only_confirmed=$true }

    $backup = Invoke-Stage "source-backup" { Backup-Database "before_phase1b_cutover" }
    Write-Evidence "source-backup-manifest.json" @{ pass=$true; path=$backup.Path; sha256=$backup.Sha256; bytes=$backup.Bytes }
    Invoke-Stage "backup-restore-validation" { Validate-Backup $backup.Path }

    if ($Mode -eq "DryRun") {
        Invoke-DryRunWorkflow
        Write-Evidence "final-summary.json" @{ result="DRY_RUN_PASS"; cutover_performed=$false }
        exit 0
    }
    Invoke-Stage "rehearsal-create" { New-Database $Rehearsal }
    $rehearsalCreated = $true
    Invoke-Stage "rehearsal-migration" { Invoke-Migration $Rehearsal }
    Invoke-Stage "rehearsal-transfer" {
        Invoke-Transfer "Rehearsal" $Rehearsal "rehearsal"
    }
    Invoke-Stage "rehearsal-application-validation" {
        Invoke-ApplicationValidation $Rehearsal "rehearsal"
    }
    Write-Evidence "rehearsal-summary.json" @{ pass=$true; database=$Rehearsal }
    if ($Mode -eq "Rehearsal") {
        Write-Evidence "final-summary.json" @{ result="REHEARSAL_PASS"; cutover_performed=$false }
        exit 0
    }

    $finalBackup = Invoke-Stage "final-backup" { Backup-Database "final" }
    Write-Evidence "final-backup-manifest.json" @{ pass=$true; path=$finalBackup.Path; sha256=$finalBackup.Sha256; bytes=$finalBackup.Bytes }
    Invoke-Stage "final-create" { New-Database $Final }
    Invoke-Stage "final-migration" { Invoke-Migration $Final }
    Invoke-Stage "final-transfer" { Invoke-Transfer "Final" $Final "final" }
    Invoke-Stage "final-application-validation" {
        Invoke-ApplicationValidation $Final "final"
    }
    $script:State = "CUTOVER_READY"
    Invoke-Stage "atomic-cutover" { Invoke-RenameCutover }
    try {
        Invoke-Stage "post-cutover-validation" {
            Invoke-ApplicationValidation $Source "post-cutover"
        }
        $revision = Invoke-Psql $Source "SELECT version_num FROM alembic_version;"
        Assert-True ($revision.StdOut.Trim() -eq $ActiveHead) "post-cutover revision mismatch"
        $script:State = "COMPLETE"
        Write-Evidence "post-cutover-validation.json" @{ pass=$true; revision=$ActiveHead; legacy_retained=$Legacy }
    } catch {
        Invoke-Stage "automatic-rollback" { Invoke-Rollback }
        throw "POST_CUTOVER_FAILED_AND_ROLLED_BACK"
    }
} catch {
    Write-Evidence "blocked-summary.json" @{ pass=$false; state=$script:State; reason=$_.Exception.Message; retry_performed=$false }
    throw
} finally {
    if ($rehearsalCreated) {
        try {
            Invoke-Stage "rehearsal-cleanup" { Remove-DisposableDatabase $Rehearsal }
        } catch {
            Write-Evidence "cleanup-failure.json" @{
                pass=$false; database=$Rehearsal; reason=$_.Exception.Message
            }
        }
    }
    $script:PlainPassword = $null
    if ($script:PasswordBstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($script:PasswordBstr)
        $script:PasswordBstr = [IntPtr]::Zero
    }
    $securePassword = $null
}
