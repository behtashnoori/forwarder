#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$EnvironmentFile = 'C:\1-webapp\forwarder-runtime\production.env',
    [string]$ApprovedBackupRoot = 'C:\1-webapp\forwarder-backups',
    [string]$PsqlPath = 'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [string]$PgDumpPath = 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe',
    [string]$PgRestorePath = 'C:\Program Files\PostgreSQL\18\bin\pg_restore.exe',
    [string]$ExpectedComputerName = 'SRV8756807400',
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$RestoreOwner,
    [ValidateRange(1,3650)][int]$RetentionDays = 30,
    [switch]$ValidateOnly,
    [switch]$CreateBackup,
    [switch]$ConfirmBackup,
    [switch]$ToolingSelfTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ExpectedRevision = '20260921_shipment_evidence_ownership'

function Stop-Backup([string]$Message) { throw "BACKUP_BLOCKED: $Message" }

function Get-TextSha256([string]$Value) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try {
        return ([BitConverter]::ToString($algorithm.ComputeHash([Text.Encoding]::UTF8.GetBytes($Value)))).Replace('-', '').ToLowerInvariant()
    } finally { $algorithm.Dispose() }
}

function Read-EnvironmentMap([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { Stop-Backup 'environment file missing' }
    $map = @{}
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        if ($line -notmatch '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') { continue }
        $name = $Matches[1]
        if ($map.ContainsKey($name)) { Stop-Backup 'duplicate environment key' }
        $map[$name] = $Matches[2].Trim().Trim('"').Trim("'")
    }
    return $map
}

function Get-DatabaseConnection([hashtable]$Map) {
    if (-not $Map.ContainsKey('DATABASE_URL') -or [string]::IsNullOrWhiteSpace([string]$Map['DATABASE_URL'])) {
        Stop-Backup 'DATABASE_URL absent'
    }
    try {
        $raw = [string]$Map['DATABASE_URL']
        $scheme = [regex]::Match($raw, '(?i)^(postgres|postgresql|postgresql\+psycopg2)://')
        if (-not $scheme.Success) { Stop-Backup 'database connection scheme unsupported' }
        $normalized = 'postgresql://' + $raw.Substring($scheme.Length)
        $uri = [Uri]$normalized
        $userInfo = $uri.UserInfo.Split(':', 2)
        $database = [Uri]::UnescapeDataString($uri.AbsolutePath.Trim('/'))
        $user = [Uri]::UnescapeDataString($userInfo[0])
        $password = if ($userInfo.Count -eq 2) { [Uri]::UnescapeDataString($userInfo[1]) } else { '' }
        if ($uri.Host -notmatch '^[A-Za-z0-9_.:-]+$' -or $database -notmatch '^[A-Za-z0-9_.-]+$' -or $user -notmatch '^[A-Za-z0-9_.-]+$') {
            Stop-Backup 'database connection identity invalid'
        }
        $sslMatch = [regex]::Match($uri.Query, '(?i)(?:^|[?&])sslmode=([^&]*)')
        $sslMode = if ($sslMatch.Success) { [Uri]::UnescapeDataString($sslMatch.Groups[1].Value) } else { '' }
        if ($sslMode -and $sslMode -notmatch '^[A-Za-z0-9_-]+$') { Stop-Backup 'database sslmode invalid' }
        return [pscustomobject]@{
            Host=$uri.Host; Port=$(if($uri.Port -gt 0){$uri.Port}else{5432})
            Database=$database; User=$user; Password=$password; SslMode=$sslMode
        }
    } catch {
        if ($_.Exception.Message -like 'BACKUP_BLOCKED:*') { throw }
        Stop-Backup 'database connection identity unavailable'
    }
}

function Invoke-PostgresTool(
    [string]$File,
    [string]$Arguments,
    [object]$Database,
    [int]$TimeoutSeconds,
    [string]$StandardInput = ''
) {
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $File
    $start.Arguments = $Arguments
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.RedirectStandardInput = -not [string]::IsNullOrEmpty($StandardInput)
    if ($Database.Password) { $start.EnvironmentVariables['PGPASSWORD'] = $Database.Password }
    if ($Database.SslMode) { $start.EnvironmentVariables['PGSSLMODE'] = $Database.SslMode }
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { Stop-Backup 'tool start failed' }
        if ($start.RedirectStandardInput) { $process.StandardInput.Write($StandardInput); $process.StandardInput.Close() }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            $process.Kill()
            Stop-Backup 'tool timeout'
        }
        return [pscustomobject]@{ ExitCode=$process.ExitCode; Stdout=[string]$stdout.Result; Stderr=[string]$stderr.Result }
    } finally {
        if ($start.EnvironmentVariables.ContainsKey('PGPASSWORD')) { $start.EnvironmentVariables.Remove('PGPASSWORD') }
        if ($start.EnvironmentVariables.ContainsKey('PGSSLMODE')) { $start.EnvironmentVariables.Remove('PGSSLMODE') }
        $process.Dispose()
    }
}

function Get-DatabaseIdentity([object]$Database) {
    $sql = @"
BEGIN TRANSACTION READ ONLY;
SELECT current_setting('server_version'),
       CASE WHEN pg_is_in_recovery() THEN 'RECOVERY' ELSE 'PRIMARY' END,
       (SELECT count(*) FROM alembic_version),
       (SELECT min(version_num) FROM alembic_version),
       pg_database_size(current_database());
COMMIT;
"@
    $arguments = '-X -w -q -A -t -F "|" -v ON_ERROR_STOP=1 -h "' + $Database.Host + '" -p ' + $Database.Port + ' -U "' + $Database.User + '" -d "' + $Database.Database + '"'
    $query = Invoke-PostgresTool $PsqlPath $arguments $Database 120 $sql
    if ($query.ExitCode -ne 0) { Stop-Backup 'database identity query failed' }
    $rows = @($query.Stdout -split "`r?`n" | Where-Object { $_ -match '\S' })
    if ($rows.Count -ne 1) { Stop-Backup 'database identity result invalid' }
    $parts = $rows[0].Split('|')
    $revisionCount = 0; $databaseSize = 0L
    if ($parts.Count -ne 5 -or -not [int]::TryParse($parts[2], [ref]$revisionCount) -or -not [int64]::TryParse($parts[4], [ref]$databaseSize)) {
        Stop-Backup 'database identity result invalid'
    }
    if ($parts[0] -notmatch '^18(?:\.|$)' -or $parts[1] -ne 'PRIMARY' -or $revisionCount -ne 1 -or $parts[3] -ne $ExpectedRevision) {
        Stop-Backup 'database identity or baseline revision mismatch'
    }
    return [pscustomobject]@{
        PostgreSqlVersion=$parts[0]; PrimaryState=$parts[1]
        AlembicRevisionCount=$revisionCount; AlembicRevision=$parts[3]
        DatabaseSizeBytes=$databaseSize
    }
}

function Invoke-ToolingSelfTest {
    $map = @{ DATABASE_URL='postgresql+psycopg2://forwarder_user:test-only-p%40ss%3Aword@127.0.0.1:5432/forwarder?sslmode=require' }
    $connection = Get-DatabaseConnection $map
    if ($connection.Host -ne '127.0.0.1' -or $connection.Port -ne 5432 -or $connection.Database -ne 'forwarder' -or
        $connection.User -ne 'forwarder_user' -or $connection.Password -ne 'test-only-p@ss:word' -or $connection.SslMode -ne 'require') {
        Stop-Backup 'tooling self-test failed'
    }
    $connection.Password = $null
    Write-Output 'SQLALCHEMY_DATABASE_URL=SUPPORTED'
    Write-Output 'BACKUP_EVIDENCE_CONTRACT=PASS'
    Write-Output 'PRODUCTION_MUTATION_PERFORMED=NO'
}

if ($ToolingSelfTest) { Invoke-ToolingSelfTest; exit 0 }
if ($ValidateOnly -and $CreateBackup) { Stop-Backup 'choose one mode' }
if (-not $ValidateOnly -and -not $CreateBackup) { $ValidateOnly = $true }
if ($CreateBackup -and -not $ConfirmBackup) { Stop-Backup 'explicit backup confirmation required' }
if ([Environment]::MachineName -ine $ExpectedComputerName) { Stop-Backup 'unexpected computer identity' }
foreach ($path in @($ApprovedBackupRoot,$PsqlPath,$PgDumpPath,$PgRestorePath,$EnvironmentFile)) {
    if (-not (Test-Path -LiteralPath $path)) { Stop-Backup 'required path unavailable' }
}

$database = Get-DatabaseConnection (Read-EnvironmentMap $EnvironmentFile)
$drive = Get-PSDrive -PSProvider FileSystem | Where-Object {
    $ApprovedBackupRoot.StartsWith($_.Root, [StringComparison]::OrdinalIgnoreCase)
} | Select-Object -First 1
if (-not $drive -or $drive.Free -le 0) { Stop-Backup 'backup destination capacity unavailable' }
$emptyDatabase = [pscustomobject]@{ Password=''; SslMode='' }
$dumpVersion = Invoke-PostgresTool $PgDumpPath '--version' $emptyDatabase 30
$restoreVersion = Invoke-PostgresTool $PgRestorePath '--version' $emptyDatabase 30
if ($dumpVersion.ExitCode -ne 0 -or $restoreVersion.ExitCode -ne 0 -or
    $dumpVersion.Stdout -notmatch '(?i)PostgreSQL\)\s+18(?:\.|\s|$)' -or $restoreVersion.Stdout -notmatch '(?i)PostgreSQL\)\s+18(?:\.|\s|$)') {
    Stop-Backup 'PostgreSQL 18 backup tooling unavailable'
}
$identity = Get-DatabaseIdentity $database
if ($ValidateOnly) {
    $database.Password = $null
    Write-Output 'BACKUP_VALIDATE_ONLY=PASS'
    Write-Output ('DATABASE_REVISION=' + $identity.AlembicRevision)
    Write-Output ('BACKUP_DESTINATION_FREE_BYTES=' + [int64]$drive.Free)
    Write-Output 'PRODUCTION_MUTATION_PERFORMED=NO'
    exit 0
}

$createdUtc = [DateTime]::UtcNow
$stamp = $createdUtc.ToString('yyyyMMddTHHmmssZ')
$dump = Join-Path $ApprovedBackupRoot "forwarder-v1.10.0-predeploy-$stamp.dump"
$catalog = $dump + '.list.txt'
$hashFile = $dump + '.sha256.txt'
$evidence = Join-Path $ApprovedBackupRoot "Forwarder-v1.10.0-PreDeploymentBackup-$stamp.json"
foreach ($path in @($dump,$catalog,$hashFile,$evidence)) {
    if (Test-Path -LiteralPath $path) { Stop-Backup 'backup output collision' }
}

$dumpArguments = '-Fc -w -h "' + $database.Host + '" -p ' + $database.Port + ' -U "' + $database.User + '" -d "' + $database.Database + '" -f "' + $dump + '"'
$created = Invoke-PostgresTool $PgDumpPath $dumpArguments $database 3600
if ($created.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $dump -PathType Leaf) -or (Get-Item -LiteralPath $dump).Length -le 0) {
    Stop-Backup 'pg_dump failed or produced an empty dump'
}
$listed = Invoke-PostgresTool $PgRestorePath ('--list "' + $dump + '"') $emptyDatabase 300
if ($listed.ExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($listed.Stdout)) { Stop-Backup 'pg_restore catalog verification failed' }

$utf8 = New-Object Text.UTF8Encoding($false)
[IO.File]::WriteAllText($catalog, $listed.Stdout, $utf8)
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dump).Hash.ToLowerInvariant()
[IO.File]::WriteAllText($hashFile, "$hash  $([IO.Path]::GetFileName($dump))`n", [Text.Encoding]::ASCII)
$record = [ordered]@{
    schema='forwarder-v1.10.0-predeployment-backup-evidence-v2'
    status='PASS'; created_utc=$createdUtc.ToString('o'); production_host=[Environment]::MachineName
    purpose='fresh_predeployment_backup_and_isolated_restore_input'
    product_version='1.10.0'; current_application_commit='e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4'
    target_application_commit='e36ee7cee157657c97dc42a539eaf1909f510a33'
    database_name_sha256=(Get-TextSha256 $database.Database)
    database_role_sha256=(Get-TextSha256 $database.User)
    database_host_sha256=(Get-TextSha256 $database.Host)
    postgresql_version=$identity.PostgreSqlVersion; database_state=$identity.PrimaryState
    alembic_revision_count=$identity.AlembicRevisionCount; database_revision=$identity.AlembicRevision
    database_size_bytes=$identity.DatabaseSizeBytes
    backup_path=$dump; dump_format='custom'; dump_size_bytes=(Get-Item -LiteralPath $dump).Length; dump_sha256=$hash
    pg_dump_exit_code=$created.ExitCode; pg_restore_list_exit_code=$listed.ExitCode; catalog_verification='PASS'
    catalog_path=$catalog; sha256_sidecar_path=$hashFile
    approved_backup_root=(Resolve-Path -LiteralPath $ApprovedBackupRoot).Path
    destination_free_bytes_before=[int64]$drive.Free; retention_days=$RetentionDays; restore_owner=$RestoreOwner
    restore_proof_status='PENDING_ISOLATED_RESTORE'; verified=$true
    production_database_mutated=$false; production_deployment_performed=$false
    secret_values_emitted=$false; reference_impact='NONE'
}
[IO.File]::WriteAllText($evidence, (($record | ConvertTo-Json -Depth 6) + "`n"), $utf8)
$database.Password = $null
Write-Output 'PREDEPLOYMENT_BACKUP=PASS'
Write-Output ('BACKUP_EVIDENCE=' + $evidence)
Write-Output ('BACKUP_SHA256=' + $hash)
Write-Output ('DATABASE_REVISION=' + $identity.AlembicRevision)
Write-Output 'PRODUCTION_DATABASE_MUTATED=NO'
Write-Output 'PRODUCTION_DEPLOYMENT_PERFORMED=NO'
