param(
    [string]$ReleasePath = $PSScriptRoot,
    [string]$BaseUrl = "http://server.logisticmarket.ir",
    [string]$SiteName,
    [string]$TaskName,
    [int]$BackendPort = 8000,
    [string]$DatabaseRevisionCommand
)
$ErrorActionPreference = "Stop"
& (Join-Path $ReleasePath "VERIFY-PACKAGE.ps1")
$manifest = Get-Content -Raw -LiteralPath (Join-Path $ReleasePath "release-manifest.json") | ConvertFrom-Json
if ($manifest.git_tag -ne "v1.7.0" -or $manifest.application_version -ne "1.7.0") { throw "Manifest identity mismatch" }
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
$protectedStatus = try { (Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/api/logistics-point-types" -UseBasicParsing).StatusCode } catch { [int]$_.Exception.Response.StatusCode }
if ($protectedStatus -ne 401 -and $protectedStatus -ne 403) { throw "Protected Logistics Network route returned $protectedStatus" }
$root = Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/" -UseBasicParsing
$js = Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/$($manifest.frontend_entry_js)" -UseBasicParsing
$css = Invoke-WebRequest "$($BaseUrl.TrimEnd('/'))/$($manifest.frontend_entry_css)" -UseBasicParsing
if ($root.Headers['Cache-Control'] -ne 'no-cache, no-store, must-revalidate' -or $root.Headers['Pragma'] -ne 'no-cache' -or $root.Headers['Expires'] -ne '0') { throw "Application-shell cache policy mismatch" }
if ($js.Headers['Cache-Control'] -ne 'public, max-age=31536000, immutable' -or $css.Headers['Cache-Control'] -ne 'public, max-age=31536000, immutable') { throw "Asset cache policy mismatch" }
if ($DatabaseRevisionCommand) {
    $revision = & powershell -NoProfile -Command $DatabaseRevisionCommand
    if (($revision | Out-String) -notmatch [regex]::Escape($manifest.database_revision)) { throw "Database revision mismatch" }
}
Write-Output "server=PASS release=$($manifest.application_version) tag=$($manifest.git_tag) seed-auto-run=false"
