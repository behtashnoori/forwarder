# ADR-043 production read-only preflight. Run manually on the Windows production server.
# This script performs inspection only: it makes no deployment, database write, service/IIS/task mutation, or file write.
[CmdletBinding()]
param(
    [string]$RuntimePath = 'C:\1-webapp\forwarder-runtime',
    [string]$TaskName = 'Forwarder Backend Production',
    [int]$BackendPort = 5101,
    [int]$SamandOrganizationId = 1
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$collectionErrors = 0
$summary = [ordered]@{}

# psql on Windows otherwise inherits a legacy console code page and can fail while
# rendering valid Persian/UTF-8 rows. These settings affect this process and psql only.
try {
    [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
    $env:PGCLIENTENCODING = 'UTF8'
    $summary.UTF8_HANDLING = 'UTF8_ENFORCED_FOR_POWERSHELL_AND_PSQL'
} catch {
    $summary.UTF8_HANDLING = 'NOT_CERTIFIED'
    $collectionErrors++
    Write-Warning "UTF-8 setup: $($_.Exception.Message)"
}

function Section([string]$Name) { Write-Host "`n=== $Name ===" }
function Safe([string]$Name, [scriptblock]$Action) {
    try { & $Action } catch { $script:collectionErrors++; Write-Warning "${Name}: $($_.Exception.Message)" }
}
function EnvValue([hashtable]$Map, [string]$Name) { if ($Map.ContainsKey($Name)) { return $Map[$Name] }; return $null }
function Present([hashtable]$Map, [string]$Name) { if ($Map.ContainsKey($Name) -and $Map[$Name]) { 'PRESENT' } else { 'MISSING' } }
function ReleasePathFromText([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return 'NOT_FOUND' }
    $match = [regex]::Match($Text, '(?i)[A-Z]:\\[^\r\n"'']*?\\release-[^\\\s"'']+')
    if ($match.Success) { return $match.Value }
    return 'NOT_INFERRED'
}
function Write-ReleaseGitEvidence([string]$Label, [string]$Path) {
    if ($Path -notin @('NOT_FOUND', 'NOT_INFERRED') -and (Test-Path (Join-Path $Path '.git'))) {
        Safe "$Label git identity" { Write-Output "${Label}_GIT_HEAD=$(& git -C $Path rev-parse HEAD)" }
    } else { Write-Output "${Label}_GIT_HEAD=NOT_VERIFIED" }
}

Section 'RUNTIME / RELEASE TOPOLOGY'
$backendRelease = 'NOT_FOUND'; $scheduledRelease = 'NOT_FOUND'; $frontendRelease = 'NOT_FOUND'
$listener = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    $summary.BACKEND_PID = $listener.OwningProcess
    $summary.BACKEND_LISTENING_PORT = $BackendPort
    Write-Output "BACKEND_PID=$($listener.OwningProcess)"
    Write-Output "BACKEND_EXECUTABLE=$($proc.ExecutablePath)"
    $backendRelease = ReleasePathFromText "$($proc.ExecutablePath) $($proc.CommandLine)"
} else { $summary.BACKEND_PID = 'NOT_FOUND'; $summary.BACKEND_LISTENING_PORT = 'NOT_LISTENING' }
Write-Output "RUNNING_BACKEND_RELEASE=$backendRelease"; Write-ReleaseGitEvidence 'RUNNING_BACKEND_RELEASE' $backendRelease
Safe 'Scheduled Task' {
    $task = Get-ScheduledTask -TaskName $TaskName
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Output "SCHEDULED_TASK_STATE=$($task.State)"
    $task.Actions | ForEach-Object {
        Write-Output "SCHEDULED_TASK_EXECUTABLE=$($_.Execute)"
        Write-Output "SCHEDULED_TASK_WORKING_DIRECTORY=$($_.WorkingDirectory)"
        $candidate = ReleasePathFromText "$($_.Execute) $($_.Arguments) $($_.WorkingDirectory)"
        if ($candidate -ne 'NOT_INFERRED') { $script:scheduledRelease = $candidate }
    }
    Write-Output "SCHEDULED_TASK_LAST_RESULT=$($info.LastTaskResult)"
}
Write-Output "SCHEDULED_TASK_RELEASE=$scheduledRelease"; Write-ReleaseGitEvidence 'SCHEDULED_TASK_RELEASE' $scheduledRelease
Safe 'Python version' { & python --version }
foreach ($uri in @("http://127.0.0.1:$BackendPort/api/health", "http://127.0.0.1:$BackendPort/readiness")) {
    Safe "HTTP $uri" { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri $uri; Write-Output "HTTP_STATUS $uri=$($r.StatusCode)" }
}

Section 'IIS / HOSTNAME / FRONTEND TOPOLOGY'
$iisReverseProxy = $false
Safe 'IIS inspection' {
    Import-Module WebAdministration
    $site = Get-Website -Name 'forwarder'
    $script:frontendRelease = ReleasePathFromText $site.PhysicalPath
    Write-Output "IIS_SITE_STATE=$($site.State)"
    Write-Output "IIS_FRONTEND_PHYSICAL_PATH=$($site.PhysicalPath)"
    Get-WebBinding -Name 'forwarder' | ForEach-Object { Write-Output "IIS_BINDING=$($_.bindingInformation)|$($_.protocol)" }
    $hosts = @(Get-WebBinding -Name 'forwarder' | ForEach-Object { ($_.bindingInformation -split ':')[-1] } | Where-Object { $_ })
    $summary.SAMAND_HOSTNAME_BINDING_PRESENT = [string]($hosts -contains 'samand.forwarderet.ir')
    $summary.OLD_HOSTNAME_BINDING_PRESENT = [string]($hosts -contains 'server.logisticmarket.ir')
    $summary.BOUND_HOSTNAMES = if ($hosts.Count) { $hosts -join ',' } else { 'NONE' }
    $webConfig = Join-Path $site.PhysicalPath 'web.config'
    if (Test-Path $webConfig) {
        $webConfigText = Get-Content -Raw $webConfig
        $script:iisReverseProxy = $webConfigText -match ("127\\.0\\.0\\.1:$BackendPort/api/")
        Write-Output "IIS_WEB_CONFIG_PRESENT=YES"
        Write-Output "IIS_API_REVERSE_PROXY_TO_LOCAL_BACKEND=$iisReverseProxy"
    } else { Write-Output 'IIS_WEB_CONFIG_PRESENT=NO' }
    $pool = Get-Item "IIS:\AppPools\$($site.applicationPool)"; Write-Output "IIS_APP_POOL_STATE=$($pool.state)"
}
Write-Output "IIS_FRONTEND_RELEASE=$frontendRelease"; Write-ReleaseGitEvidence 'IIS_FRONTEND_RELEASE' $frontendRelease
$knownReleases = @($backendRelease, $scheduledRelease, $frontendRelease) | Where-Object { $_ -notin @('NOT_FOUND', 'NOT_INFERRED') }
$summary.RELEASE_IDENTITY_CONFIDENT = if ($knownReleases.Count -eq 3) { 'YES' } else { 'NO' }
$summary.RELEASE_IDENTITY_MATCH = if ($knownReleases.Count -eq 3 -and (@($knownReleases | Select-Object -Unique).Count -eq 1)) { 'YES' } elseif ($knownReleases.Count -ge 2) { 'NO' } else { 'NOT_VERIFIED' }

Section 'REDACTED ENVIRONMENT'
$envFile = Join-Path $RuntimePath 'production.env'
$envMap = @{}
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and -not $_.TrimStart().StartsWith('#')) { $envMap[$matches[1]] = $matches[2].Trim('"', "'") }
    }
    $dbUrl = EnvValue $envMap 'DATABASE_URL'
    if ($dbUrl) {
        try { $dbUri = [uri]$dbUrl; $dbHost=$dbUri.Host; $dbPort=if($dbUri.Port -gt 0){$dbUri.Port}else{5432}; $dbName=$dbUri.AbsolutePath.Trim('/'); $dbUser=$dbUri.UserInfo.Split(':')[0] } catch { throw 'DATABASE_URL present but identity cannot be parsed safely.' }
    }
    foreach ($key in @('DATABASE_URL','SECRET_KEY','JWT_SECRET_KEY')) { Write-Output "$key=$(Present $envMap $key)" }
    foreach ($key in @('APP_ENV','FLASK_ENV','PORT','BACKEND_PORT','CORS_ORIGINS','CORS_ORIGIN')) { if ($envMap.ContainsKey($key)) { Write-Output "$key=$($envMap[$key])" } }
    Write-Output "DB_HOST=$dbHost"; Write-Output "DB_PORT=$dbPort"; Write-Output "DB_NAME=$dbName"; Write-Output "DB_USER=$dbUser"
} else { Write-Warning 'production.env not found'; $collectionErrors++ }

Section 'DATABASE READ-ONLY INSPECTION'
$psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
if (-not (Test-Path $psql)) { $psql = 'psql.exe' }
function Invoke-ReadonlySql([string]$Query, [switch]$Scalar) {
    if ([string]::IsNullOrWhiteSpace($dbHost) -or [string]::IsNullOrWhiteSpace($dbName) -or [string]::IsNullOrWhiteSpace($dbUser)) { throw 'Database identity is unavailable; no database query was attempted.' }
    $wrapped = "BEGIN TRANSACTION READ ONLY; SET LOCAL client_encoding TO 'UTF8'; $Query COMMIT;"
    $args = @('-X', '-v', 'ON_ERROR_STOP=1', '-P', 'pager=off', '-h', $dbHost, '-p', $dbPort, '-U', $dbUser, '-d', $dbName)
    if ($Scalar) { $args += @('-A', '-t', '-q') }
    $args += @('-c', $wrapped)
    $result = & $psql @args
    if ($LASTEXITCODE -ne 0) { throw "psql exited with code $LASTEXITCODE" }
    return @($result)
}
function Sql([string]$Name, [string]$Query) { Safe $Name { Invoke-ReadonlySql $Query | Write-Output } }
function DbScalar([string]$Name, [string]$Query) {
    try { return ((Invoke-ReadonlySql $Query -Scalar | Where-Object { $_ -match '\S' } | Select-Object -Last 1).Trim()) }
    catch { $script:collectionErrors++; Write-Warning "${Name}: $($_.Exception.Message)"; return $null }
}
function DbRelationState([string]$Table) {
    $value = DbScalar "Relation check $Table" "SELECT to_regclass('public.$Table') IS NOT NULL;"
    if ($value -eq 't') { return 'PRESENT' }; if ($value -eq 'f') { return 'ABSENT' }; return 'UNKNOWN'
}
function DbColumnState([string]$Table, [string]$Column) {
    $value = DbScalar "Column check $Table.$Column" "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='$Table' AND column_name='$Column');"
    if ($value -eq 't') { return 'PRESENT' }; if ($value -eq 'f') { return 'ABSENT' }; return 'UNKNOWN'
}
Sql 'Database identity' "SELECT version() AS server_version, current_database() AS production_db_name, current_user AS db_user; SELECT version_num AS production_alembic_current FROM alembic_version;"

Section 'AUTHORITY / MEMBERSHIP AUDIT'
Sql 'Authority counts' "WITH m AS (SELECT user_id, count(*) FILTER (WHERE is_active) n FROM operational_membership GROUP BY user_id) SELECT 'PLATFORM_ADMIN_WITH_MEMBERSHIP_COUNT' k,count(*) v FROM expert_user u JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='PLATFORM_ADMIN' AND m.n>0 UNION ALL SELECT 'ORGANIZATION_ADMIN_INVALID_MEMBERSHIP_COUNT',count(*) FROM expert_user u LEFT JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='ORGANIZATION_ADMIN' AND coalesce(m.n,0)<>1 UNION ALL SELECT 'EXPERT_NO_MEMBERSHIP_COUNT',count(*) FROM expert_user u LEFT JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='EXPERT' AND coalesce(m.n,0)=0 UNION ALL SELECT 'EXPERT_MULTI_MEMBERSHIP_COUNT',count(*) FROM expert_user u JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='EXPERT' AND m.n>1 UNION ALL SELECT 'ROLE_ADMIN_AUTHORITY_EXPERT_COUNT',count(*) FROM expert_user WHERE is_active AND role='admin' AND authority='EXPERT';"

Section 'REQUEST / DIRECT ROOT READINESS'
Sql 'Request roots' "SELECT count(*) TOTAL_SHIPMENT_REQUEST_ROOTS, count(*) FILTER (WHERE r.assigned_to IS NOT NULL AND u.is_active AND m.organization_id=r.operational_organization_id AND m.is_active) REQUEST_ROOTS_WITH_VALID_CURRENT_ASSIGNMENT, count(*) FILTER (WHERE r.assigned_to IS NULL OR u.id IS NULL OR NOT u.is_active OR m.id IS NULL) REQUEST_ROOTS_WITHOUT_VALID_CURRENT_ASSIGNMENT, count(*) FILTER (WHERE r.assigned_to IS NOT NULL AND (u.id IS NULL OR NOT u.is_active)) REQUEST_ROOTS_WITH_INACTIVE_ASSIGNEE, count(*) FILTER (WHERE r.assigned_to IS NOT NULL AND m.id IS NULL) REQUEST_ROOTS_WITH_CROSS_TENANT_ASSIGNEE, 0 REQUEST_ROOTS_WITH_AMBIGUOUS_ASSIGNMENT FROM shipment_request r LEFT JOIN expert_user u ON u.id=r.assigned_to LEFT JOIN operational_membership m ON m.user_id=r.assigned_to AND m.organization_id=r.operational_organization_id AND m.is_active WHERE r.ownership_scope='TENANT';"
$directColumnState = DbColumnState 'operational_shipment' 'primary_responsible_expert_id'
if ($directColumnState -eq 'PRESENT') {
    Write-Output 'DIRECT_SHIPMENT_READINESS=COMPUTABLE_ON_TARGET_SCHEMA'
    Sql 'Direct roots' "SELECT count(*) FILTER (WHERE s.source_type='direct') TOTAL_DIRECT_OPERATIONAL_SHIPMENTS,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL) DIRECT_SHIPMENTS_WITH_PRIMARY_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NULL) DIRECT_SHIPMENTS_WITHOUT_PRIMARY_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND (u.id IS NULL OR NOT u.is_active)) DIRECT_SHIPMENTS_WITH_INVALID_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL AND m.id IS NULL) DIRECT_SHIPMENTS_WITH_CROSS_TENANT_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL AND (u.id IS NULL OR NOT u.is_active)) DIRECT_SHIPMENTS_WITH_INACTIVE_RESPONSIBLE_EXPERT FROM operational_shipment s LEFT JOIN expert_user u ON u.id=s.primary_responsible_expert_id LEFT JOIN operational_membership m ON m.user_id=s.primary_responsible_expert_id AND m.organization_id=s.organization_id AND m.is_active;"
} elseif ($directColumnState -eq 'ABSENT') {
    Write-Output 'DIRECT_SHIPMENT_READINESS=NOT_COMPUTABLE_BEFORE_TARGET_SCHEMA'
    Write-Output 'SCHEMA_PREREQUISITE=20260907_direct_shipment_responsibility'
    Write-Output 'DIRECT_SHIPMENT_SCHEMA_STATE=SCHEMA_PREREQUISITE_PENDING'
} else {
    Write-Output 'DIRECT_SHIPMENT_READINESS=NOT_COMPUTABLE_SCHEMA_INSPECTION_NOT_VERIFIED'
}

Section 'CHILD LINEAGE AUDIT'
$childResources = @('operational_work_item', 'route_plan', 'operational_milestone')
$childResourceStates = @{}; foreach ($resource in $childResources) { $childResourceStates[$resource] = DbRelationState $resource }
$missingResources = @($childResources | Where-Object { $childResourceStates[$_] -eq 'ABSENT' })
$unknownResources = @($childResources | Where-Object { $childResourceStates[$_] -eq 'UNKNOWN' })
foreach ($resource in $missingResources) { Write-Output "RESOURCE_NOT_PRESENT_IN_SCHEMA=$resource" }
foreach ($resource in $unknownResources) { Write-Output "RESOURCE_SCHEMA_INSPECTION_NOT_VERIFIED=$resource" }
if ($missingResources.Count -eq 0 -and $unknownResources.Count -eq 0) {
    $requiredColumns = @(@('operational_work_item','operational_shipment_id'), @('operational_work_item','organization_id'), @('route_plan','operational_shipment_id'), @('operational_milestone','operational_shipment_id'), @('operational_milestone','organization_id'))
    $columnMismatch = @($requiredColumns | Where-Object { (DbColumnState $_[0] $_[1]) -eq 'ABSENT' })
    $unknownColumns = @($requiredColumns | Where-Object { (DbColumnState $_[0] $_[1]) -eq 'UNKNOWN' })
    if ($columnMismatch.Count -eq 0 -and $unknownColumns.Count -eq 0) {
        Sql 'Child lineage' "SELECT 'ORPHAN_WORK_ITEM' k,count(*) v FROM operational_work_item w LEFT JOIN operational_shipment s ON s.id=w.operational_shipment_id WHERE s.id IS NULL UNION ALL SELECT 'CROSS_TENANT_WORK_ITEM',count(*) FROM operational_work_item w JOIN operational_shipment s ON s.id=w.operational_shipment_id WHERE w.organization_id<>s.organization_id UNION ALL SELECT 'ORPHAN_ROUTE_PLAN',count(*) FROM route_plan p LEFT JOIN operational_shipment s ON s.id=p.operational_shipment_id WHERE s.id IS NULL UNION ALL SELECT 'ORPHAN_OPERATIONAL_MILESTONE',count(*) FROM operational_milestone x LEFT JOIN operational_shipment s ON s.id=x.operational_shipment_id WHERE s.id IS NULL UNION ALL SELECT 'CROSS_TENANT_OPERATIONAL_MILESTONE',count(*) FROM operational_milestone x JOIN operational_shipment s ON s.id=x.operational_shipment_id WHERE x.organization_id<>s.organization_id;"
    } elseif ($columnMismatch.Count -gt 0) { Write-Output 'CHILD_LINEAGE_INSPECTION=RESOURCE_SCHEMA_MISMATCH' }
    else { Write-Output 'CHILD_LINEAGE_INSPECTION=SCHEMA_INSPECTION_NOT_VERIFIED' }
} elseif ($missingResources.Count -gt 0) { Write-Output 'CHILD_LINEAGE_INSPECTION=NOT_COMPUTABLE_FOR_CURRENT_SCHEMA' }
else { Write-Output 'CHILD_LINEAGE_INSPECTION=SCHEMA_INSPECTION_NOT_VERIFIED' }

Section 'LEGACY ROLE / LOGISTICS SELECTOR AUDIT'
Sql 'Legacy role inventory' "SELECT role AS LEGACY_ROLE_LABEL, authority AS CANONICAL_AUTHORITY, count(*) AS ACTIVE_USER_COUNT FROM expert_user WHERE is_active GROUP BY role,authority ORDER BY role,authority; SELECT 'LEGACY_ROLE_LABEL_PRESENT' AS CLASSIFICATION, count(*) AS ACTIVE_LEGACY_LABEL_COUNT FROM expert_user WHERE is_active AND role IN ('admin','crm_manager','supervisor','business_expert'); SELECT 'LEGACY_ROLE_USED_AS_ACTIVE_AUTHORITY' AS CLASSIFICATION, count(*) AS ACTIVE_ROLE_ADMIN_WITH_EXPERT_AUTHORITY FROM expert_user WHERE is_active AND role='admin' AND authority='EXPERT';"
$permissionsColumnState = DbColumnState 'operational_membership' 'permissions'
if ($permissionsColumnState -eq 'PRESENT') {
    Sql 'Logistics selector permissions' "SELECT count(*) EXPERT_MEMBERSHIP_COUNT,count(*) FILTER (WHERE m.permissions::jsonb ? 'logistics_point.read') EXPERT_WITH_LOGISTICS_POINT_READ,count(*) FILTER (WHERE NOT (m.permissions::jsonb ? 'logistics_point.read')) EXPERT_WITHOUT_LOGISTICS_POINT_READ FROM expert_user u JOIN operational_membership m ON m.user_id=u.id WHERE u.is_active AND u.authority='EXPERT' AND m.is_active;"
} elseif ($permissionsColumnState -eq 'ABSENT') { Write-Output 'LOGISTICS_SELECTOR_AUDIT=RESOURCE_SCHEMA_MISMATCH' }
else { Write-Output 'LOGISTICS_SELECTOR_AUDIT=SCHEMA_INSPECTION_NOT_VERIFIED' }

Section 'CORS / BACKUP TOPOLOGY'
if ($iisReverseProxy) {
    $summary.CORS_ARCHITECTURE_CLASSIFICATION = 'SAME_ORIGIN_REVERSE_PROXY_CONFIGURED'
    $summary.CORS_CONFIGURATION_COVERAGE = 'NOT_REQUIRED_FOR_BROWSER_TO_API_SAME_ORIGIN_PATH'
} else {
    $summary.CORS_ARCHITECTURE_CLASSIFICATION = 'CORS_ARCHITECTURE_NOT_VERIFIED'
    $summary.CORS_CONFIGURATION_COVERAGE = 'NOT_VERIFIED'
}
if ($envMap.ContainsKey('CORS_ORIGINS')) { $summary.PRODUCTION_CORS_ORIGINS=$envMap['CORS_ORIGINS'] }
foreach ($path in @('C:\1-webapp\forwarder-backups',(Join-Path $RuntimePath 'server-state'),'C:\1-webapp\forwarder-production')) { Write-Output "PATH_EXISTS $path=$(Test-Path $path)"; if(Test-Path $path){Get-ChildItem $path -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,LastWriteTime,Length} }

Section 'ADR043_PRODUCTION_READONLY_PREFLIGHT'
$summary.PREFLIGHT_COLLECTION_COMPLETE = if($collectionErrors -eq 0){'YES'}else{'NO'}
$summary.COLLECTION_ERRORS=$collectionErrors
$summary.GetEnumerator() | ForEach-Object { Write-Output "$($_.Key)=$($_.Value)" }
