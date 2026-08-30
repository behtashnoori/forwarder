# ADR-043 production read-only preflight. Run on the Windows production server.
# It performs no deployment, database write, service/IIS/task mutation, or file write.
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
function Section([string]$Name) { Write-Host "`n=== $Name ===" }
function Safe([string]$Name, [scriptblock]$Action) {
    try { & $Action } catch { $script:collectionErrors++; Write-Warning "${Name}: $($_.Exception.Message)" }
}
function EnvValue([hashtable]$Map, [string]$Name) { if ($Map.ContainsKey($Name)) { return $Map[$Name] }; return $null }
function Present([hashtable]$Map, [string]$Name) { if ($Map.ContainsKey($Name) -and $Map[$Name]) { 'PRESENT' } else { 'MISSING' } }

Section 'RUNTIME / RELEASE IDENTITY'
$listener = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
    $summary.BACKEND_PID = $listener.OwningProcess
    $summary.BACKEND_LISTENING_PORT = $BackendPort
    Write-Output "BACKEND_PID=$($listener.OwningProcess)"
    Write-Output "BACKEND_EXECUTABLE=$($proc.ExecutablePath)"
    Write-Output "BACKEND_COMMAND_LINE=$($proc.CommandLine)"
} else { $summary.BACKEND_PID = 'NOT_FOUND'; $summary.BACKEND_LISTENING_PORT = 'NOT_LISTENING' }
Safe 'Scheduled Task' {
    $task = Get-ScheduledTask -TaskName $TaskName
    $info = Get-ScheduledTaskInfo -TaskName $TaskName
    Write-Output "SCHEDULED_TASK_STATE=$($task.State)"
    $task.Actions | ForEach-Object { Write-Output "SCHEDULED_TASK_EXECUTABLE=$($_.Execute)"; Write-Output "SCHEDULED_TASK_ARGUMENTS=$($_.Arguments)"; Write-Output "SCHEDULED_TASK_WORKING_DIRECTORY=$($_.WorkingDirectory)" }
    Write-Output "SCHEDULED_TASK_LAST_RESULT=$($info.LastTaskResult)"
}
$releasePaths = @('C:\1-webapp\forwarder-production', $RuntimePath) | Where-Object { Test-Path $_ }
foreach ($path in $releasePaths) {
    Write-Output "RELEASE_PATH=$path"
    if (Test-Path (Join-Path $path '.git')) { Write-Output "RELEASE_GIT_HEAD=$(& git -C $path rev-parse HEAD)" }
}
Safe 'Python version' { & python --version }
foreach ($uri in @("http://127.0.0.1:$BackendPort/api/health", "http://127.0.0.1:$BackendPort/readiness")) {
    Safe "HTTP $uri" { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 10 -Uri $uri; Write-Output "HTTP_STATUS $uri=$($r.StatusCode)" }
}

Section 'IIS / HOSTNAME / FRONTEND'
Safe 'IIS inspection' {
    Import-Module WebAdministration
    $site = Get-Website -Name 'forwarder'
    Write-Output "IIS_SITE_STATE=$($site.State)"
    Write-Output "IIS_PHYSICAL_PATH=$($site.PhysicalPath)"
    Get-WebBinding -Name 'forwarder' | ForEach-Object { Write-Output "IIS_BINDING=$($_.bindingInformation)|$($_.protocol)" }
    $hosts = @(Get-WebBinding -Name 'forwarder' | ForEach-Object { ($_.bindingInformation -split ':')[-1] })
    $summary.SAMAND_HOSTNAME_BINDING_PRESENT = [string]($hosts -contains 'samand.forwarderet.ir')
    $summary.OLD_HOSTNAME_BINDING_PRESENT = [string]($hosts -contains 'server.logisticmarket.ir')
    $summary.PRIMARY_HOSTNAME_INFERENCE = if ($hosts -contains 'samand.forwarderet.ir') { 'samand.forwarderet.ir' } else { 'NOT_INFERRED' }
    $pool = Get-Item "IIS:\AppPools\$($site.applicationPool)"; Write-Output "IIS_APP_POOL_STATE=$($pool.state)"
}

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
function Sql([string]$Name, [string]$Query) {
    Safe $Name { & $psql -X -v ON_ERROR_STOP=1 -P pager=off -h $dbHost -p $dbPort -U $dbUser -d $dbName -c "BEGIN READ ONLY; $Query COMMIT;" }
}
Sql 'Database identity' "SELECT version() AS server_version, current_database() AS production_db_name, current_user AS db_user; SELECT version_num AS production_alembic_current FROM alembic_version; SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='operational_shipment' AND column_name='primary_responsible_expert_id') AS primary_responsible_column_present;"

Section 'AUTHORITY / MEMBERSHIP AUDIT'
Sql 'Authority counts' "WITH m AS (SELECT user_id, count(*) FILTER (WHERE is_active) n FROM operational_membership GROUP BY user_id) SELECT 'PLATFORM_ADMIN_WITH_MEMBERSHIP_COUNT' k,count(*) v FROM expert_user u JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='PLATFORM_ADMIN' AND m.n>0 UNION ALL SELECT 'ORGANIZATION_ADMIN_INVALID_MEMBERSHIP_COUNT',count(*) FROM expert_user u LEFT JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='ORGANIZATION_ADMIN' AND coalesce(m.n,0)<>1 UNION ALL SELECT 'EXPERT_NO_MEMBERSHIP_COUNT',count(*) FROM expert_user u LEFT JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='EXPERT' AND coalesce(m.n,0)=0 UNION ALL SELECT 'EXPERT_MULTI_MEMBERSHIP_COUNT',count(*) FROM expert_user u JOIN m ON m.user_id=u.id WHERE u.is_active AND u.authority='EXPERT' AND m.n>1 UNION ALL SELECT 'ROLE_ADMIN_AUTHORITY_EXPERT_COUNT',count(*) FROM expert_user WHERE is_active AND role='admin' AND authority='EXPERT'; SELECT u.id user_id,u.username,u.is_active active,u.role legacy_role,u.authority canonical_authority,count(m.id) FILTER (WHERE m.is_active) active_membership_count,coalesce(string_agg(DISTINCT m.permissions::text,','),'[]') permissions FROM expert_user u LEFT JOIN operational_membership m ON m.user_id=u.id AND m.organization_id=$SamandOrganizationId GROUP BY u.id,u.username,u.is_active,u.role,u.authority ORDER BY u.id;"

Section 'REQUEST / DIRECT ROOT READINESS'
Sql 'Request roots' "SELECT count(*) TOTAL_SHIPMENT_REQUEST_ROOTS, count(*) FILTER (WHERE r.assigned_to IS NOT NULL AND u.is_active AND m.organization_id=r.operational_organization_id AND m.is_active) REQUEST_ROOTS_WITH_VALID_CURRENT_ASSIGNMENT, count(*) FILTER (WHERE r.assigned_to IS NULL OR u.id IS NULL OR NOT u.is_active OR m.id IS NULL) REQUEST_ROOTS_WITHOUT_VALID_CURRENT_ASSIGNMENT, count(*) FILTER (WHERE r.assigned_to IS NOT NULL AND (u.id IS NULL OR NOT u.is_active)) REQUEST_ROOTS_WITH_INACTIVE_ASSIGNEE, count(*) FILTER (WHERE r.assigned_to IS NOT NULL AND m.id IS NULL) REQUEST_ROOTS_WITH_CROSS_TENANT_ASSIGNEE, 0 REQUEST_ROOTS_WITH_AMBIGUOUS_ASSIGNMENT FROM shipment_request r LEFT JOIN expert_user u ON u.id=r.assigned_to LEFT JOIN operational_membership m ON m.user_id=r.assigned_to AND m.organization_id=r.operational_organization_id AND m.is_active WHERE r.ownership_scope='TENANT';"
Sql 'Direct roots (schema branch)' "SELECT CASE WHEN EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='operational_shipment' AND column_name='primary_responsible_expert_id') THEN 'COLUMN_PRESENT=YES' ELSE 'COLUMN_PRESENT=NO; canonical direct metrics NOT_COMPUTABLE' END;"
Sql 'Direct roots if column exists' "SELECT count(*) FILTER (WHERE s.source_type='direct') TOTAL_DIRECT_OPERATIONAL_SHIPMENTS,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL) DIRECT_SHIPMENTS_WITH_PRIMARY_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NULL) DIRECT_SHIPMENTS_WITHOUT_PRIMARY_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND (u.id IS NULL OR NOT u.is_active)) DIRECT_SHIPMENTS_WITH_INVALID_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL AND m.id IS NULL) DIRECT_SHIPMENTS_WITH_CROSS_TENANT_RESPONSIBLE_EXPERT,count(*) FILTER (WHERE s.source_type='direct' AND s.primary_responsible_expert_id IS NOT NULL AND (u.id IS NULL OR NOT u.is_active)) DIRECT_SHIPMENTS_WITH_INACTIVE_RESPONSIBLE_EXPERT FROM operational_shipment s LEFT JOIN expert_user u ON u.id=s.primary_responsible_expert_id LEFT JOIN operational_membership m ON m.user_id=s.primary_responsible_expert_id AND m.organization_id=s.organization_id AND m.is_active;"

Section 'CHILD LINEAGE / LEGACY / SELECTOR / CRM'
Sql 'Child lineage' "SELECT 'ORPHAN_WORK_ITEM' k,count(*) v FROM operational_work_item w LEFT JOIN operational_shipment s ON s.id=w.operational_shipment_id WHERE s.id IS NULL UNION ALL SELECT 'CROSS_TENANT_WORK_ITEM',count(*) FROM operational_work_item w JOIN operational_shipment s ON s.id=w.operational_shipment_id WHERE w.organization_id<>s.organization_id UNION ALL SELECT 'ORPHAN_ROUTE_PLAN',count(*) FROM route_plan p LEFT JOIN operational_shipment s ON s.id=p.operational_shipment_id WHERE s.id IS NULL UNION ALL SELECT 'ORPHAN_MILESTONE',count(*) FROM milestone x LEFT JOIN operational_shipment s ON s.id=x.operational_shipment_id WHERE s.id IS NULL;"
Sql 'Legacy and selector' "SELECT role,count(*) active_users FROM expert_user WHERE is_active GROUP BY role ORDER BY role; SELECT count(*) EXPERT_COUNT,count(*) FILTER (WHERE permissions ? 'logistics_point.read') EXPERT_WITH_LOGISTICS_POINT_READ,count(*) FILTER (WHERE NOT permissions ? 'logistics_point.read') EXPERT_WITHOUT_LOGISTICS_POINT_READ FROM expert_user u JOIN operational_membership m ON m.user_id=u.id WHERE u.is_active AND u.authority='EXPERT' AND m.is_active; SELECT role,count(*) CRM_LEGACY_ROLE_USERS FROM expert_user WHERE is_active AND role IN ('crm_manager','business_expert') GROUP BY role;"

Section 'CORS / BACKUP TOPOLOGY'
if ($envMap.ContainsKey('CORS_ORIGINS')) { $summary.PRODUCTION_CORS_ORIGINS=$envMap['CORS_ORIGINS']; $summary.SAMAND_FORWARDERET_CORS_READY=[string]($envMap['CORS_ORIGINS'] -match 'samand\.forwarderet\.ir') }
foreach ($path in @('C:\1-webapp\forwarder-backups',(Join-Path $RuntimePath 'server-state'),'C:\1-webapp\forwarder-production')) { Write-Output "PATH_EXISTS $path=$(Test-Path $path)"; if(Test-Path $path){Get-ChildItem $path -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name,LastWriteTime,Length} }

Section 'ADR043_PRODUCTION_READONLY_PREFLIGHT'
$summary.PREFLIGHT_COLLECTION_COMPLETE = if($collectionErrors -eq 0){'YES'}else{'NO'}; $summary.COLLECTION_ERRORS=$collectionErrors
$summary.GetEnumerator() | ForEach-Object { Write-Output "$($_.Key)=$($_.Value)" }
