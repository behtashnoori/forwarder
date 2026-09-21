#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$OutputDirectory = $PSScriptRoot,
    [string]$EnvironmentFile = 'C:\1-webapp\forwarder-runtime\production.env',
    [string]$ReleaseRoot = 'C:\1-webapp\forwarder-production',
    [string]$RuntimeRoot = 'C:\1-webapp\forwarder-runtime',
    [string]$ApprovedBackupRoot = 'C:\1-webapp\forwarder-backups',
    [string]$TaskName = 'Forwarder Backend Production',
    [string]$IisSiteName = 'forwarder',
    [int]$BackendPort = 5101,
    [string]$PublicBaseUrl = 'https://samand.forwarderet.ir',
    [string]$PsqlPath = 'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [string]$PgDumpPath = 'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe',
    [string]$PgRestorePath = 'C:\Program Files\PostgreSQL\18\bin\pg_restore.exe'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ExpectedBeforeRevision = '20260921_shipment_evidence_ownership'
$ExpectedTargetRevision = '20260926_fixed_shipment_responsible_expert'
$ExpectedProductVersion = '1.10.0'
$ExpectedApplicationCommit = 'e36ee7cee157657c97dc42a539eaf1909f510a33'
$CollectionErrors = New-Object 'System.Collections.Generic.List[string]'

function Add-CollectionError([string]$Code) {
    if (-not $CollectionErrors.Contains($Code)) { $CollectionErrors.Add($Code) }
}

function Redact-Text([string]$Value) {
    if ([string]::IsNullOrEmpty($Value)) { return $Value }
    $result = $Value
    $result = [regex]::Replace($result, '(?i)(postgres(?:ql)?://[^:/@\s]+:)[^@\s]+(@)', '$1[REDACTED]$2')
    $result = [regex]::Replace($result, '(?i)\b(password|passwd|pwd|secret|secret_key|jwt_secret_key|token|authorization|api_key)\s*[:=]\s*[^\s;,&]+', '$1=[REDACTED]')
    $result = [regex]::Replace($result, '(?i)\b(Bearer)\s+[A-Za-z0-9._~+/-]+=*', '$1 [REDACTED]')
    $result = [regex]::Replace($result, '\b[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b', '[REDACTED_TOKEN]')
    return $result
}

function Get-TextSha256([string]$Value) {
    if ([string]::IsNullOrEmpty($Value)) { return $null }
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}

function Normalize-Path([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
    try { return [IO.Path]::GetFullPath($Value.Trim().Trim('"').Trim("'")).TrimEnd('\') }
    catch { return $null }
}

function Same-Path([string]$Left, [string]$Right) {
    $a = Normalize-Path $Left; $b = Normalize-Path $Right
    return ($null -ne $a -and $null -ne $b -and [string]::Equals($a, $b, [StringComparison]::OrdinalIgnoreCase))
}

function Get-ReleasePathFromText([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
    $match = [regex]::Match($Value, '(?i)[A-Z]:\\(?:[^\\\s"''&|]+\\)*release-[^\\\s"''&|]+')
    if ($match.Success) { return (Normalize-Path $match.Value.TrimEnd(';', '&', '|')) }
    return $null
}

function Invoke-Safe([string]$Code, [scriptblock]$Action) {
    try { return (& $Action) }
    catch { Add-CollectionError $Code; return $null }
}

function Read-EnvironmentMap([string]$Path) {
    $map = @{}
    $duplicates = New-Object 'System.Collections.Generic.List[string]'
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Add-CollectionError 'PRODUCTION_ENV_NOT_FOUND'
        return [pscustomobject]@{ Values = $map; Duplicates = $duplicates.ToArray(); Present = $false }
    }
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        if ($trimmed -notmatch '^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') { continue }
        $name = $Matches[1]; $value = $Matches[2].Trim().Trim('"').Trim("'")
        if ($map.ContainsKey($name)) { $duplicates.Add($name) }
        $map[$name] = $value
    }
    return [pscustomobject]@{ Values = $map; Duplicates = @($duplicates | Select-Object -Unique); Present = $true }
}

function Config-State([hashtable]$Map, [string]$Name, [scriptblock]$Validator, [bool]$AbsentIsSafe = $false) {
    if (-not $Map.ContainsKey($Name) -or [string]::IsNullOrWhiteSpace([string]$Map[$Name])) {
        return [pscustomobject]@{ state = $(if ($AbsentIsSafe) { 'NOT_APPLICABLE' } else { 'ABSENT' }) }
    }
    $isSafe = $false
    try { $isSafe = [bool](& $Validator ([string]$Map[$Name])) } catch { $isSafe = $false }
    return [pscustomobject]@{ state = $(if ($isSafe) { 'SAFE_VALUE_OK' } else { 'SAFE_VALUE_INVALID' }) }
}

function Get-ConnectionInfo([hashtable]$Map) {
    if (-not $Map.ContainsKey('DATABASE_URL') -or [string]::IsNullOrWhiteSpace([string]$Map['DATABASE_URL'])) { return $null }
    try {
        $uri = [Uri]([string]$Map['DATABASE_URL'])
        if ($uri.Scheme -notin @('postgres', 'postgresql')) { return $null }
        $userInfo = $uri.UserInfo.Split(':', 2)
        $user = [Uri]::UnescapeDataString($userInfo[0])
        $password = if ($userInfo.Count -eq 2) { [Uri]::UnescapeDataString($userInfo[1]) } else { '' }
        $database = [Uri]::UnescapeDataString($uri.AbsolutePath.Trim('/'))
        $port = if ($uri.Port -gt 0) { $uri.Port } else { 5432 }
        if ($uri.Host -notmatch '^[A-Za-z0-9_.:-]+$' -or $user -notmatch '^[A-Za-z0-9_.-]+$' -or $database -notmatch '^[A-Za-z0-9_.-]+$') { return $null }
        return [pscustomobject]@{ Host=$uri.Host; Port=$port; User=$user; Password=$password; Database=$database }
    } catch { return $null }
}

function Assert-ReadOnlySql([string]$Sql, [string]$Name) {
    if ($Sql -notmatch '(?is)^\s*BEGIN\s+TRANSACTION\s+READ\s+ONLY\s*;' -or $Sql -notmatch '(?is)COMMIT\s*;\s*$') {
        throw "SQL_READ_ONLY_ENVELOPE_INVALID:$Name"
    }
    $forbidden = '(?im)\b(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|TRUNCATE|GRANT|REVOKE|VACUUM|REINDEX|CALL|DO)\b'
    if ($Sql -match $forbidden) { throw "SQL_MUTATION_KEYWORD_REJECTED:$Name" }
}

function Invoke-ReadOnlySql([string]$Sql, [object]$Connection, [string]$Name) {
    Assert-ReadOnlySql $Sql $Name
    if (-not (Test-Path -LiteralPath $PsqlPath -PathType Leaf)) { throw 'PSQL_NOT_AVAILABLE' }
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $PsqlPath
    $start.Arguments = '-X -w -q -A -t -F "|" -v ON_ERROR_STOP=1 -h "' + $Connection.Host + '" -p ' + $Connection.Port + ' -U "' + $Connection.User + '" -d "' + $Connection.Database + '"'
    $start.WorkingDirectory = $PSScriptRoot
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    if (-not [string]::IsNullOrEmpty([string]$Connection.Password)) { $start.EnvironmentVariables['PGPASSWORD'] = [string]$Connection.Password }
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'PSQL_START_FAILED' }
        $process.StandardInput.Write($Sql)
        $process.StandardInput.Close()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(120000)) { $process.Kill(); throw 'PSQL_TIMEOUT' }
        $output = [string]$stdout.Result
        $errorText = Redact-Text ([string]$stderr.Result)
        if ($process.ExitCode -ne 0) { throw ('PSQL_FAILED_' + $Name + ':' + $errorText.Substring(0, [Math]::Min(160, $errorText.Length))) }
        return @($output -split "`r?`n" | Where-Object { $_ -match '\S' })
    } finally {
        if ($start.EnvironmentVariables.ContainsKey('PGPASSWORD')) { $start.EnvironmentVariables.Remove('PGPASSWORD') }
        $process.Dispose()
    }
}

function Read-SqlFile([string]$FileName) {
    $path = Join-Path (Join-Path $PSScriptRoot 'sql') $FileName
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "SQL_SUPPORT_FILE_MISSING:$FileName" }
    return Get-Content -Raw -LiteralPath $path
}

function Convert-CheckRows([string[]]$Rows) {
    $checks = New-Object 'System.Collections.Generic.List[object]'
    foreach ($row in $Rows) {
        $parts = $row.Split('|', 3)
        if ($parts.Count -ne 3) { continue }
        $checks.Add([pscustomobject]@{ code=$parts[0]; state=$parts[1]; detail=$parts[2] })
    }
    return $checks.ToArray()
}

function Get-DirectorySize([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $null }
    try { return [int64](Get-ChildItem -LiteralPath $Path -Recurse -File -Force -ErrorAction Stop | Measure-Object -Property Length -Sum).Sum }
    catch { return $null }
}

function Get-HttpProbe([string]$Uri) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 10 -MaximumRedirection 0 -ErrorAction Stop
        return [pscustomobject]@{ uri=$Uri; status_code=[int]$response.StatusCode; reachable=$true }
    } catch {
        $status = $null
        if ($_.Exception.PSObject.Properties['Response'] -and $_.Exception.Response) {
            try { $status = [int]$_.Exception.Response.StatusCode } catch {}
        }
        return [pscustomobject]@{ uri=$Uri; status_code=$status; reachable=$false }
    }
}

function Get-LogHealth([string[]]$Paths) {
    $counts = [ordered]@{ crash_loop=0; database=0; migration=0; permission_storage=0; proxy=0; critical_5xx=0; files_examined=0; lines_examined=0 }
    foreach ($path in $Paths | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) } | Select-Object -Unique | Select-Object -First 8) {
        try {
            $lines = @(Get-Content -LiteralPath $path -Tail 250 -ErrorAction Stop)
            $counts.files_examined++
            $counts.lines_examined += $lines.Count
            foreach ($line in $lines) {
                $safe = Redact-Text ([string]$line)
                if ($safe -match '(?i)crash|restart loop|exited unexpectedly') { $counts.crash_loop++ }
                if ($safe -match '(?i)database|postgres|connection refused|could not connect') { $counts.database++ }
                if ($safe -match '(?i)alembic|migration|revision') { $counts.migration++ }
                if ($safe -match '(?i)permission denied|access denied|disk full|no space|storage') { $counts.permission_storage++ }
                if ($safe -match '(?i)502|503|504|proxy|upstream') { $counts.proxy++ }
                if ($safe -match '(?i)\s5[0-9][0-9]\s|status.?5[0-9][0-9]') { $counts.critical_5xx++ }
            }
        } catch { Add-CollectionError 'LOG_SUMMARY_FAILED' }
    }
    return [pscustomobject]$counts
}

if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) { throw 'OutputDirectory must already exist.' }
$generatedUtc = [DateTime]::UtcNow
$hostInfo = Invoke-Safe 'HOST_INSPECTION_FAILED' {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    [pscustomobject]@{
        computer_name = [Environment]::MachineName
        windows_caption = [string]$os.Caption
        windows_version = [string]$os.Version
        last_boot_utc = ([DateTime]$os.LastBootUpTime).ToUniversalTime().ToString('o')
        current_user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        elevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        powershell_version = $PSVersionTable.PSVersion.ToString()
        collected_utc = $generatedUtc.ToString('o')
    }
}

$environment = Read-EnvironmentMap $EnvironmentFile
$envMap = $environment.Values
$config = [ordered]@{}
$config['ENVIRONMENT_FILE'] = [pscustomobject]@{ state=$(if ($environment.Present) {'PRESENT'} else {'ABSENT'}); path=(Normalize-Path $EnvironmentFile) }
$config['DATABASE_URL'] = [pscustomobject]@{ state=$(if ($envMap.ContainsKey('DATABASE_URL') -and $envMap['DATABASE_URL']) {'PRESENT'} else {'ABSENT'}) }
$config['SECRET_KEY'] = [pscustomobject]@{ state=$(if ($envMap.ContainsKey('SECRET_KEY') -and $envMap['SECRET_KEY']) {'PRESENT'} else {'ABSENT'}) }
$config['JWT_SECRET_KEY'] = [pscustomobject]@{ state=$(if ($envMap.ContainsKey('JWT_SECRET_KEY') -and $envMap['JWT_SECRET_KEY']) {'PRESENT'} else {'ABSENT'}) }
$config['APP_ENV'] = Config-State $envMap 'APP_ENV' { param($v) $v.ToLowerInvariant() -in @('production','prod') }
$config['ENV'] = Config-State $envMap 'ENV' { param($v) $v.ToLowerInvariant() -in @('production','prod') } $true
$config['FLASK_ENV'] = Config-State $envMap 'FLASK_ENV' { param($v) $v.ToLowerInvariant() -in @('production','prod') } $true
$config['AUTO_MIGRATE_ON_STARTUP'] = Config-State $envMap 'AUTO_MIGRATE_ON_STARTUP' { param($v) $v.ToLowerInvariant() -in @('false','0','no','off') } $true
$config['CORS_ALLOW_ALL_ORIGINS'] = Config-State $envMap 'CORS_ALLOW_ALL_ORIGINS' { param($v) $v.ToLowerInvariant() -in @('false','0','no','off') } $true
$config['CORS_ORIGINS'] = Config-State $envMap 'CORS_ORIGINS' { param($v) $v -notmatch '(?i)(^|,)\s*\*\s*(,|$)' }
$config['DB_CONNECT_TIMEOUT_SECONDS'] = Config-State $envMap 'DB_CONNECT_TIMEOUT_SECONDS' { param($v) $n=0; [int]::TryParse($v,[ref]$n) -and $n -ge 1 -and $n -le 60 } $true
$documentRoot = if ($envMap.ContainsKey('DOCUMENT_STORAGE_ROOT')) { Normalize-Path ([string]$envMap['DOCUMENT_STORAGE_ROOT']) } else { $null }
$config['DOCUMENT_STORAGE_ROOT'] = [pscustomobject]@{
    state=$(if ($documentRoot) {'PRESENT'} else {'ABSENT'})
    path=$documentRoot
    exists=$(if ($documentRoot) { Test-Path -LiteralPath $documentRoot -PathType Container } else { $false })
    outside_release_root=$(if ($documentRoot) { -not $documentRoot.StartsWith((Normalize-Path $ReleaseRoot), [StringComparison]::OrdinalIgnoreCase) } else { $false })
}
$config['RELEASE_IDENTITY_PATH'] = [pscustomobject]@{ state=$(if ($envMap.ContainsKey('RELEASE_IDENTITY_PATH') -and $envMap['RELEASE_IDENTITY_PATH']) {'PRESENT'} else {'ABSENT'}) }
$invalidConfig = @($config.GetEnumerator() | Where-Object { $_.Value.state -in @('ABSENT','SAFE_VALUE_INVALID') -and $_.Key -in @('DATABASE_URL','SECRET_KEY','JWT_SECRET_KEY','APP_ENV','CORS_ORIGINS','DOCUMENT_STORAGE_ROOT') }).Count
if ($environment.Duplicates.Count -gt 0) { Add-CollectionError 'DUPLICATE_CONFIG_KEYS' }

$taskResult = Invoke-Safe 'SCHEDULED_TASK_INSPECTION_FAILED' {
    $tasks = @(Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop)
    if ($tasks.Count -ne 1) { throw 'task missing or ambiguous' }
    $task = $tasks[0]; $info = Get-ScheduledTaskInfo -InputObject $task -ErrorAction Stop
    $xmlText = Export-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    [xml]$xml = $xmlText
    $actionNodes = @($xml.SelectNodes("/*[local-name()='Task']/*[local-name()='Actions']/*[local-name()='Exec']"))
    if ($actionNodes.Count -ne 1) { throw 'task action missing or ambiguous' }
    $action = $actionNodes[0]
    $arguments = Redact-Text ([string]$action.Arguments)
    $release = Get-ReleasePathFromText (([string]$action.Command) + ' ' + $arguments + ' ' + ([string]$action.WorkingDirectory))
    [pscustomobject]@{
        name=$TaskName; state=[string]$task.State; enabled=[bool]$task.Settings.Enabled
        last_result=[int64]$info.LastTaskResult; last_run_utc=$(if($info.LastRunTime){$info.LastRunTime.ToUniversalTime().ToString('o')}else{$null})
        next_run_utc=$(if($info.NextRunTime){$info.NextRunTime.ToUniversalTime().ToString('o')}else{$null})
        principal=[pscustomobject]@{ user_id=(Redact-Text ([string]$xml.Task.Principals.Principal.UserId)); logon_type=[string]$xml.Task.Principals.Principal.LogonType; run_level=[string]$xml.Task.Principals.Principal.RunLevel }
        action_executable=Normalize-Path ([string]$action.Command); sanitized_arguments=$arguments
        working_directory=Normalize-Path ([string]$action.WorkingDirectory); release_path=$release
        trigger_count=@($xml.Task.Triggers.ChildNodes).Count
        restart_count=[string]$xml.Task.Settings.RestartOnFailure.Count
        restart_interval=[string]$xml.Task.Settings.RestartOnFailure.Interval
        multiple_instances_policy=[string]$xml.Task.Settings.MultipleInstancesPolicy
    }
}

$listeners = New-Object 'System.Collections.Generic.List[object]'
$listenerRows = @(Invoke-Safe 'LISTENER_INSPECTION_FAILED' { Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction Stop })
foreach ($row in $listenerRows) {
    $proc = Invoke-Safe 'LISTENER_PROCESS_INSPECTION_FAILED' { Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$row.OwningProcess) -ErrorAction Stop }
    if ($null -eq $proc) { continue }
    $command = Redact-Text ([string]$proc.CommandLine)
    $release = Get-ReleasePathFromText (([string]$proc.ExecutablePath) + ' ' + $command)
    $listeners.Add([pscustomobject]@{
        local_address=[string]$row.LocalAddress; local_port=[int]$row.LocalPort; pid=[int]$row.OwningProcess
        executable=Normalize-Path ([string]$proc.ExecutablePath); sanitized_command_line=$command
        release_path=$release
        waitress_contract=($command -match '(?i)-m\s+waitress' -and $command -match '(?i)backend\.wsgi:app')
        task_release_match=($taskResult -and $release -and (Same-Path $release $taskResult.release_path))
    })
}
$listenerOwnership = ($listeners.Count -eq 1 -and $listeners[0].local_address -eq '127.0.0.1' -and $listeners[0].waitress_contract -and $listeners[0].task_release_match)

$iisResult = Invoke-Safe 'IIS_INSPECTION_FAILED' {
    Import-Module WebAdministration -ErrorAction Stop
    $site = Get-Website -Name $IisSiteName -ErrorAction Stop
    $bindings = @(Get-WebBinding -Name $IisSiteName -ErrorAction Stop | ForEach-Object {
        [pscustomobject]@{ protocol=[string]$_.protocol; binding_information=[string]$_.bindingInformation; has_https=([string]$_.protocol -eq 'https') }
    })
    $rules = New-Object 'System.Collections.Generic.List[object]'
    $webConfigPath = Join-Path ([string]$site.PhysicalPath) 'web.config'
    if (Test-Path -LiteralPath $webConfigPath -PathType Leaf) {
        [xml]$web = Get-Content -Raw -LiteralPath $webConfigPath
        foreach ($rule in @($web.configuration.'system.webServer'.rewrite.rules.rule)) {
            $rules.Add([pscustomobject]@{
                name=[string]$rule.name; match_url=[string]$rule.match.url
                action_type=[string]$rule.action.type; action_url=(Redact-Text ([string]$rule.action.url)
                )
            })
        }
    }
    [pscustomobject]@{
        site_name=$IisSiteName; state=[string]$site.State; application_pool=[string]$site.ApplicationPool
        physical_path=Normalize-Path ([string]$site.PhysicalPath); bindings=$bindings; https_present=(@($bindings | Where-Object {$_.has_https}).Count -gt 0)
        rewrite_rules=$rules.ToArray(); api_proxy_present=(@($rules | Where-Object {$_.action_url -match '(?i)127\.0\.0\.1:[0-9]+/api'}).Count -gt 0)
        spa_fallback_present=(@($rules | Where-Object {$_.action_url -match '(?i)index\.html'}).Count -gt 0)
        web_config_present=(Test-Path -LiteralPath $webConfigPath -PathType Leaf)
    }
}

$activeRelease = $null
if ($listeners.Count -eq 1 -and $listeners[0].release_path) { $activeRelease = $listeners[0].release_path }
elseif ($taskResult -and $taskResult.release_path) { $activeRelease = $taskResult.release_path }
$manifestResult = $null
if ($activeRelease) {
    $manifestResult = Invoke-Safe 'RELEASE_MANIFEST_INSPECTION_FAILED' {
        $manifestPath = Join-Path $activeRelease 'release-manifest.json'
        if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw 'manifest missing' }
        $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        [pscustomobject]@{
            path=Normalize-Path $manifestPath; product_name=[string]$manifest.product_name
            release_stage=[string]$manifest.release_stage; application_version=[string]$manifest.application_version
            application_commit=[string]$manifest.application_commit; database_revision=[string]$manifest.database_revision
            package_sha256=[string]$manifest.package_sha256
        }
    }
}

$releaseDirectories = @()
if (Test-Path -LiteralPath $ReleaseRoot -PathType Container) {
    $releaseDirectories = @(Get-ChildItem -LiteralPath $ReleaseRoot -Directory -ErrorAction SilentlyContinue | Where-Object {$_.Name -like 'release-*'} | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 10 | ForEach-Object {
        [pscustomobject]@{ name=$_.Name; last_write_utc=$_.LastWriteTimeUtc.ToString('o'); bytes=$(if($activeRelease -and (Same-Path $_.FullName $activeRelease)){Get-DirectorySize $_.FullName}else{$null}); active=($activeRelease -and (Same-Path $_.FullName $activeRelease)) }
    })
}

$health = [ordered]@{
    local_health = Get-HttpProbe "http://127.0.0.1:$BackendPort/api/health"
    local_readiness = Get-HttpProbe "http://127.0.0.1:$BackendPort/api/health/ready"
}

$database = [ordered]@{ collection='UNAVAILABLE'; identity=$null; adr047=$null; compatibility=@(); schema_drift_blocker_count=$null }
$connection = Get-ConnectionInfo $envMap
if ($connection) {
    try {
        $identitySql = @"
BEGIN TRANSACTION READ ONLY;
SELECT 'POSTGRESQL_VERSION', current_setting('server_version')
UNION ALL SELECT 'DATABASE_NAME', current_database()
UNION ALL SELECT 'DATABASE_ROLE', current_user
UNION ALL SELECT 'PRIMARY_STATE', CASE WHEN pg_is_in_recovery() THEN 'RECOVERY' ELSE 'PRIMARY' END
UNION ALL SELECT 'DATABASE_SIZE_BYTES', pg_database_size(current_database())::text
UNION ALL SELECT 'DATABASE_UTC', (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::text
UNION ALL SELECT 'ALEMBIC_REVISION_COUNT', count(*)::text FROM alembic_version
UNION ALL SELECT 'ALEMBIC_REVISION', coalesce(min(version_num),'') FROM alembic_version;
COMMIT;
"@
        $identityRows = @(Invoke-ReadOnlySql $identitySql $connection 'database_identity')
        $identityMap = @{}
        foreach($row in $identityRows){$parts=$row.Split('|',2);if($parts.Count -eq 2){$identityMap[$parts[0]]=$parts[1]}}
        $database.identity = [pscustomobject]@{
            postgresql_version=[string]$identityMap['POSTGRESQL_VERSION']
            database_name_sha256=(Get-TextSha256 ([string]$identityMap['DATABASE_NAME']))
            database_role_sha256=(Get-TextSha256 ([string]$identityMap['DATABASE_ROLE']))
            primary_state=[string]$identityMap['PRIMARY_STATE']
            database_size_bytes=[int64]$identityMap['DATABASE_SIZE_BYTES']
            database_utc=[string]$identityMap['DATABASE_UTC']
            alembic_revision_count=[int]$identityMap['ALEMBIC_REVISION_COUNT']
            alembic_revision=[string]$identityMap['ALEMBIC_REVISION']
        }
        $adrRows = @(Invoke-ReadOnlySql (Read-SqlFile 'adr047-production-classifier.sql') $connection 'adr047_classifier')
        if ($adrRows.Count -ne 1) { throw 'ADR047_RESULT_SHAPE_INVALID' }
        $adr = $adrRows[0].Split('|')
        if ($adr.Count -ne 5) { throw 'ADR047_RESULT_SHAPE_INVALID' }
        $database.adr047 = [pscustomobject]@{
            fixed_owner_already_valid_count=[int64]$adr[0]
            fixed_owner_deterministic_repair_count=[int64]$adr[1]
            fixed_owner_ambiguous_count=[int64]$adr[2]
            fixed_owner_contradiction_count=[int64]$adr[3]
            fixed_owner_other_unresolved_count=[int64]$adr[4]
        }
        $database.compatibility = @(Convert-CheckRows (Invoke-ReadOnlySql (Read-SqlFile 'migration-compatibility-readonly.sql') $connection 'migration_compatibility'))
        $database.schema_drift_blocker_count = @($database.compatibility | Where-Object {$_.state -ne 'PASS'}).Count
        $database.collection = 'AVAILABLE'
    } catch {
        Add-CollectionError 'DATABASE_READ_ONLY_COLLECTION_FAILED'
        $database.collection = 'UNAVAILABLE'
    } finally {
        $connection.Password = $null
    }
} else { Add-CollectionError 'DATABASE_CONNECTION_MODEL_UNAVAILABLE' }

$driveNames = New-Object 'System.Collections.Generic.List[string]'
foreach ($path in @($env:SystemRoot,$ReleaseRoot,$RuntimeRoot,$ApprovedBackupRoot,$documentRoot)) {
    if ([string]::IsNullOrWhiteSpace($path)) { continue }
    try { $root = [IO.Path]::GetPathRoot((Normalize-Path $path)); if($root -and -not $driveNames.Contains($root)){$driveNames.Add($root)} } catch {}
}
$drives = @($driveNames | ForEach-Object {
    $root=$_; $drive=Get-PSDrive -PSProvider FileSystem | Where-Object {$_.Root -eq $root} | Select-Object -First 1
    [pscustomobject]@{ root=$root; free_bytes=$(if($drive){[int64]$drive.Free}else{$null}); used_bytes=$(if($drive){[int64]$drive.Used}else{$null}) }
})

$backup = [ordered]@{
    root=Normalize-Path $ApprovedBackupRoot; mechanism_identified=$false; destination_ready=$false
    tooling_available=((Test-Path -LiteralPath $PgDumpPath -PathType Leaf) -and (Test-Path -LiteralPath $PgRestorePath -PathType Leaf))
    latest_dump=$null; restore_evidence_available=$false; capacity_status='UNKNOWN'
}
if (Test-Path -LiteralPath $ApprovedBackupRoot -PathType Container) {
    $backup.mechanism_identified=$true; $backup.destination_ready=$true
    $latest = Get-ChildItem -LiteralPath $ApprovedBackupRoot -File -Filter '*.dump' -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
    if ($latest) {
        $backup.latest_dump=[pscustomobject]@{
            size_bytes=[int64]$latest.Length; timestamp_utc=$latest.LastWriteTimeUtc.ToString('o')
            age_hours=[Math]::Round(($generatedUtc-$latest.LastWriteTimeUtc).TotalHours,2)
            sha_sidecar_present=(Test-Path -LiteralPath ($latest.FullName+'.sha256.txt') -PathType Leaf)
            catalog_sidecar_present=(Test-Path -LiteralPath ($latest.FullName+'.list.txt') -PathType Leaf)
        }
        $backup.restore_evidence_available=[bool]$backup.latest_dump.catalog_sidecar_present
    }
    $backupDrive = @($drives | Where-Object {$backup.root.StartsWith($_.root,[StringComparison]::OrdinalIgnoreCase)} | Select-Object -First 1)
    if ($backupDrive.Count -eq 1 -and $backupDrive[0].free_bytes -gt 0) { $backup.capacity_status='MEASURED' }
}

$logPaths = New-Object 'System.Collections.Generic.List[string]'
if ($envMap.ContainsKey('LOG_FILE') -and $envMap['LOG_FILE']) { $logPaths.Add((Normalize-Path ([string]$envMap['LOG_FILE']))) }
if (Test-Path -LiteralPath (Join-Path $RuntimeRoot 'logs') -PathType Container) {
    foreach($file in Get-ChildItem -LiteralPath (Join-Path $RuntimeRoot 'logs') -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 4){$logPaths.Add($file.FullName)}
}
$logHealth = Get-LogHealth @($logPaths)

$runtimeAgreement = ($activeRelease -and $taskResult -and (Same-Path $activeRelease $taskResult.release_path) -and $iisResult -and (Same-Path $iisResult.physical_path (Join-Path $activeRelease 'dist')) -and $listenerOwnership)
$databaseGate = ($database.collection -eq 'AVAILABLE' -and $database.identity.alembic_revision_count -eq 1 -and $database.identity.alembic_revision -eq $ExpectedBeforeRevision -and $database.identity.primary_state -eq 'PRIMARY' -and $database.schema_drift_blocker_count -eq 0 -and $database.adr047.fixed_owner_ambiguous_count -eq 0 -and $database.adr047.fixed_owner_contradiction_count -eq 0 -and $database.adr047.fixed_owner_other_unresolved_count -eq 0)
$configGate = ($invalidConfig -eq 0 -and $config['AUTO_MIGRATE_ON_STARTUP'].state -notin @('SAFE_VALUE_INVALID') -and $config['CORS_ALLOW_ALL_ORIGINS'].state -notin @('SAFE_VALUE_INVALID'))
$collectorStatus = if ($CollectionErrors.Count -eq 0 -and $runtimeAgreement -and $databaseGate -and $configGate -and $backup.mechanism_identified -and $backup.tooling_available) { 'PASS' } else { 'BLOCKED' }

$result = [ordered]@{
    schema='forwarder-v1.10.0-production-readonly-preflight-v1'
    generated_utc=$generatedUtc.ToString('o')
    collector_status=$collectorStatus
    product_contract=[ordered]@{ target_product_version=$ExpectedProductVersion; target_application_commit=$ExpectedApplicationCommit; before_database_revision=$ExpectedBeforeRevision; target_database_revision=$ExpectedTargetRevision }
    host=$hostInfo
    active_release=[ordered]@{ release_root=(Normalize-Path $ReleaseRoot); active_release_path=$activeRelease; directories=$releaseDirectories; manifest=$manifestResult; runtime_agreement=[bool]$runtimeAgreement }
    scheduled_task=$taskResult
    listeners=$listeners.ToArray()
    listener_ownership_verified=[bool]$listenerOwnership
    iis=$iisResult
    http=$health
    config=[pscustomobject]$config
    mandatory_config_missing_or_invalid_count=$invalidConfig
    database=[pscustomobject]$database
    storage=[ordered]@{ document_root=$config['DOCUMENT_STORAGE_ROOT']; runtime_root=(Normalize-Path $RuntimeRoot); release_root=(Normalize-Path $ReleaseRoot); drives=$drives }
    log_health=$logHealth
    backup_readiness=[pscustomobject]$backup
    collection_errors=$CollectionErrors.Count
    collection_error_codes=$CollectionErrors.ToArray()
    secret_values_emitted=$false
    production_mutation_performed=$false
}

$stamp = $generatedUtc.ToString('yyyyMMddTHHmmssZ')
$outputPath = Join-Path (Normalize-Path $OutputDirectory) "Forwarder-v1.10.0-Production-ReadOnly-Preflight-$stamp.json"
$json = $result | ConvertTo-Json -Depth 14
$utf8 = New-Object Text.UTF8Encoding($false)
$stream = [IO.File]::Open($outputPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try {
    $writer = New-Object IO.StreamWriter($stream, $utf8)
    try { $writer.Write($json); $writer.Write("`n") } finally { $writer.Dispose() }
} finally { $stream.Dispose() }

Write-Output ('PRODUCTION_READ_ONLY_COLLECTOR=' + $collectorStatus)
Write-Output ('COLLECTION_ERRORS=' + $CollectionErrors.Count)
Write-Output ('SANITIZED_RESULT=' + $outputPath)
Write-Output 'PRODUCTION_MUTATION_PERFORMED=NO'
