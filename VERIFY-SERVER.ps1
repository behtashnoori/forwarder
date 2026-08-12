param(
    [string]$ReleasePath = $PSScriptRoot,
    [string]$BaseUrl = "https://server.logisticmarket.ir",
    [string]$SiteName,
    [string]$TaskName,
    [int]$BackendPort = 5101,
    [string]$DatabaseRevisionCommand
)
$ErrorActionPreference = "Stop"
& (Join-Path $ReleasePath "VERIFY-PACKAGE.ps1")
$manifest = Get-Content -Raw -LiteralPath (Join-Path $ReleasePath "release-manifest.json") | ConvertFrom-Json
if ($manifest.git_tag -ne "v1.9.3" -or $manifest.application_version -ne "1.9.3" -or $manifest.database_revision -ne "20260825_admin_multitenant" -or $manifest.milestone_type_catalog_apply_status -ne "not applied") { throw "Manifest identity mismatch" }
$releasePython = Join-Path $ReleasePath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $releasePython -PathType Leaf)) { throw "Release Python environment missing: $releasePython" }
& $releasePython -c "import importlib.metadata, psycopg2; expected='2.9.11'; actual=importlib.metadata.version('psycopg2-binary'); assert actual == expected, f'psycopg2-binary version mismatch: {actual} != {expected}'"
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL runtime driver verification failed" }
if ($SiteName) {
    Import-Module WebAdministration -ErrorAction Stop
    $physicalPath = (Get-Item "IIS:\Sites\$SiteName").physicalPath
    if ((Resolve-Path $physicalPath).Path -ne (Resolve-Path $ReleasePath).Path) { throw "IIS physical path mismatch" }
}
if ($TaskName) {
    $task = Get-ScheduledTask -TaskName $TaskName
    $actions = @($task.Actions)
    $actionText = ($actions | ForEach-Object { "$($_.WorkingDirectory) $($_.Arguments)" }) -join " "
    if ($actionText -notlike "*$ReleasePath*" -or $actionText -notmatch '(?i)--repo') { throw "Scheduled Task release/repository path mismatch" }
    if ($actionText -notmatch '(?i)PYTHONPATH|--repo') { throw "Scheduled Task PYTHONPATH/repository handling not evident" }
}
if (-not (Get-NetTCPConnection -State Listen -LocalPort $BackendPort -ErrorAction SilentlyContinue)) { throw "Backend listener missing on port $BackendPort" }
$health = Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/api/health" -UseBasicParsing
if ($health.StatusCode -ne 200) { throw "Health check failed" }
$protectedStatus = try { (Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/api/projects/00000000-0000-0000-0000-000000000000/configuration/services" -UseBasicParsing).StatusCode } catch { [int]$_.Exception.Response.StatusCode }
if ($protectedStatus -ne 401) { throw "Protected Project Configuration route returned $protectedStatus" }
$root = Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/" -UseBasicParsing
$js = Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/$($manifest.frontend_entry_js)" -UseBasicParsing
$css = Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/$($manifest.frontend_entry_css)" -UseBasicParsing
if ($root.Headers['Cache-Control'] -ne 'no-cache, no-store, must-revalidate' -or $root.Headers['Pragma'] -ne 'no-cache' -or $root.Headers['Expires'] -ne '0') { throw "Application-shell cache policy mismatch" }
if ($js.Headers['Cache-Control'] -ne 'public, max-age=31536000, immutable' -or $css.Headers['Cache-Control'] -ne 'public, max-age=31536000, immutable') { throw "Asset cache policy mismatch" }
if ($DatabaseRevisionCommand) {
    $revision = & powershell -NoProfile -Command $DatabaseRevisionCommand
    if (($revision | Out-String) -notmatch [regex]::Escape($manifest.database_revision)) { throw "Database revision mismatch" }
}
Write-Output "server=PASS release=$($manifest.application_version) tag=$($manifest.git_tag) catalog-auto-run=false"
