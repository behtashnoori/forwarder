#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackagePath,
    [string]$ExpectedSha256,
    [string]$SidecarPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ExpectedVersion = '1.10.0'
$ExpectedSource = 'e36ee7cee157657c97dc42a539eaf1909f510a33'
$ExpectedBefore = '20260921_shipment_evidence_ownership'
$ExpectedTarget = '20260926_fixed_shipment_responsible_expert'
$ExpectedBase = 'a742628293359379cb476b782a2fe27e61a8db1f'
$ExpectedRuntimeId = 'Forwarder-Windows-Runtime-S7-RC-a257669-r4'
$ExpectedRuntimeSha256 = 'f4a8f108aa89a78d7986f01fb8f6aa8af5e2d35e00617a8453eb1f15df945070'

function Stop-Package([string]$Message) { throw "PACKAGE_BLOCKED: $Message" }
function Read-ZipText($Entry) {
    $stream = $Entry.Open()
    try {
        $reader = New-Object IO.StreamReader($stream, [Text.Encoding]::UTF8, $true)
        try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
    } finally { $stream.Dispose() }
}
function Get-ZipEntrySha256($Entry) {
    $stream = $Entry.Open(); $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}

if (-not (Test-Path -LiteralPath $PackagePath -PathType Leaf)) { Stop-Package 'package file missing' }
$PackagePath = (Resolve-Path -LiteralPath $PackagePath).Path
$actualOuter = (Get-FileHash -Algorithm SHA256 -LiteralPath $PackagePath).Hash.ToLowerInvariant()
if ([string]::IsNullOrWhiteSpace($SidecarPath)) { $SidecarPath = $PackagePath + '.sha256' }
if (-not [string]::IsNullOrWhiteSpace($ExpectedSha256)) {
    if ($ExpectedSha256 -notmatch '^[0-9a-fA-F]{64}$' -or $actualOuter -ne $ExpectedSha256.ToLowerInvariant()) { Stop-Package 'outer SHA256 mismatch' }
} else {
    if (-not (Test-Path -LiteralPath $SidecarPath -PathType Leaf)) { Stop-Package 'SHA256 sidecar missing' }
    $sidecar = (Get-Content -Raw -LiteralPath $SidecarPath).Trim()
    if ($sidecar -notmatch '^([0-9a-fA-F]{64})  ([^\\/]+\.zip)$') { Stop-Package 'malformed SHA256 sidecar' }
    if ($Matches[1].ToLowerInvariant() -ne $actualOuter -or $Matches[2] -ne [IO.Path]::GetFileName($PackagePath)) { Stop-Package 'SHA256 sidecar mismatch' }
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($PackagePath)
try {
    $entries = @($archive.Entries | Where-Object { -not [string]::IsNullOrEmpty($_.Name) })
    $entryMap = @{}
    foreach ($entry in $entries) {
        $name = $entry.FullName.Replace('\','/')
        if ($name -match '(^/|^[A-Za-z]:|(^|/)\.\.(/|$)|\\)' -or $entryMap.ContainsKey($name)) { Stop-Package "unsafe or duplicate entry $name" }
        $entryMap[$name] = $entry
    }
    foreach ($required in @('release-manifest.json','PACKAGE-INVENTORY.json','APPLICATION-INVENTORY.json','SHA256SUMS.txt','VERIFY-PRODUCTION-PACKAGE.ps1','PRODUCTION-README.md','runtime/python.exe','dist/index.html','backend/migration_cli.py')) {
        if (-not $entryMap.ContainsKey($required)) { Stop-Package "required entry missing: $required" }
    }
    foreach ($name in $entryMap.Keys) {
        if ($name -match '(?i)(^|/)(\.env|production\.env|[^/]*\.sqlite3?|[^/]*\.db)$' -or
            $name -match '(?i)^(uploads?|documents?)(/|$)' -or
            $name -match '(?i)(id_rsa|id_ed25519|\.pfx$|\.pem$|\.key$)') { Stop-Package "forbidden mutable/secret-bearing path: $name" }
        if ($name -in @('START-UAT.ps1','STOP-UAT.ps1','uat_gateway.py','README-UAT.md')) { Stop-Package "UAT-only entry present: $name" }
    }

    $manifest = (Read-ZipText $entryMap['release-manifest.json']) | ConvertFrom-Json
    if ($manifest.schema -ne 'forwarder-production-release-manifest-v1' -or
        $manifest.product_name -ne 'Forwarder' -or
        $manifest.release_stage -ne 'Production' -or
        $manifest.application_version -ne $ExpectedVersion -or
        $manifest.frontend_version -ne $ExpectedVersion -or
        $manifest.backend_version -ne $ExpectedVersion -or
        $manifest.accepted_product_base_sha -ne $ExpectedBase -or
        $manifest.application_commit -ne $ExpectedSource -or
        $manifest.release_source_sha -ne $ExpectedSource -or
        $manifest.before_database_revision -ne $ExpectedBefore -or
        $manifest.database_revision -ne $ExpectedTarget -or
        [int]$manifest.alembic_head_count -ne 1 -or
        $manifest.runtime_entrypoint -ne 'C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py' -or
        $manifest.runtime_id -ne $ExpectedRuntimeId -or
        $manifest.runtime_sha256 -ne $ExpectedRuntimeSha256 -or
        $manifest.backend_listener_contract -ne '127.0.0.1:5101' -or
        $manifest.external_environment_path -ne 'C:\1-webapp\forwarder-runtime\production.env' -or
        [bool]$manifest.auto_migrate_on_startup -or
        [bool]$manifest.mutable_data_packaged -or
        $manifest.reference_impact -ne 'NONE' -or
        [bool]$manifest.production_accessed) { Stop-Package 'release identity mismatch' }

    $expected = @{}
    foreach ($line in ((Read-ZipText $entryMap['SHA256SUMS.txt']) -split "`r?`n")) {
        if (-not $line) { continue }
        if ($line -notmatch '^([0-9a-f]{64})  ([^\\]+)$') { Stop-Package 'malformed internal checksum line' }
        $relative = $Matches[2]
        if ($relative -match '(^/|^[A-Za-z]:|(^|/)\.\.(/|$))' -or $expected.ContainsKey($relative)) { Stop-Package 'unsafe or duplicate checksum path' }
        $expected[$relative] = $Matches[1]
    }
    foreach ($relative in $expected.Keys) {
        if (-not $entryMap.ContainsKey($relative)) { Stop-Package "checksummed file missing: $relative" }
        if ((Get-ZipEntrySha256 $entryMap[$relative]) -ne $expected[$relative]) { Stop-Package "entry checksum mismatch: $relative" }
    }
    $unchecked = @($entryMap.Keys | Where-Object { $_ -ne 'SHA256SUMS.txt' -and -not $expected.ContainsKey($_) })
    if ($unchecked.Count -gt 0) { Stop-Package ('unexpected unchecked entries: ' + ($unchecked -join ',')) }

    # Windows PowerShell 5.1 can preserve a top-level JSON array as one nested
    # pipeline object when it is wrapped directly in @(...).  Assign first so
    # foreach reliably enumerates every inventory record.
    $inventory = (Read-ZipText $entryMap['PACKAGE-INVENTORY.json']) | ConvertFrom-Json
    $inventoryMap = @{}
    $inventoryPaths = New-Object 'System.Collections.Generic.List[string]'
    foreach($item in $inventory){
        $inventoryPath = [string]$item.path
        if([string]::IsNullOrWhiteSpace($inventoryPath) -or $inventoryMap.ContainsKey($inventoryPath)){Stop-Package 'empty or duplicate inventory path'}
        $inventoryMap[$inventoryPath] = $item
        $inventoryPaths.Add($inventoryPath)
    }
    $requiredInventory = @($expected.Keys | Where-Object {$_ -ne 'PACKAGE-INVENTORY.json'} | Sort-Object)
    if($inventoryMap.Count -ne $requiredInventory.Count){Stop-Package 'inventory entry count mismatch'}
    $sortedInventoryPaths = $inventoryPaths.ToArray()
    [Array]::Sort($sortedInventoryPaths,[StringComparer]::Ordinal)
    if(($inventoryPaths.ToArray() -join "`n") -cne ($sortedInventoryPaths -join "`n")){Stop-Package 'inventory is not sorted'}
    foreach($relative in $requiredInventory){
        if(-not $inventoryMap.ContainsKey($relative)){Stop-Package "inventory entry missing: $relative"}
        if([string]$inventoryMap[$relative].sha256 -ne [string]$expected[$relative]){Stop-Package "inventory checksum mismatch: $relative"}
        if([int64]$inventoryMap[$relative].bytes -ne [int64]$entryMap[$relative].Length){Stop-Package "inventory size mismatch: $relative"}
    }
    $applicationInventory = (Read-ZipText $entryMap['APPLICATION-INVENTORY.json']) | ConvertFrom-Json
    if ($applicationInventory.Count -eq 0 -or @($applicationInventory | Where-Object {$_.source_commit -ne $ExpectedSource}).Count -gt 0) { Stop-Package 'application inventory source mismatch' }
    $applicationPaths = @{}
    foreach($item in $applicationInventory){
        $relative=[string]$item.path
        if([string]::IsNullOrWhiteSpace($relative) -or $applicationPaths.ContainsKey($relative)){Stop-Package 'empty or duplicate application inventory path'}
        if(-not $entryMap.ContainsKey($relative)){Stop-Package "application inventory file missing: $relative"}
        if([int64]$item.bytes -ne [int64]$entryMap[$relative].Length -or [string]$item.sha256 -ne (Get-ZipEntrySha256 $entryMap[$relative])){Stop-Package "application inventory mismatch: $relative"}
        $applicationPaths[$relative]=$true
    }

    Write-Output 'PRODUCTION_PACKAGE_VERIFICATION=PASS'
    Write-Output ('PRODUCTION_PACKAGE_SHA256=' + $actualOuter)
    Write-Output ('PRODUCTION_PACKAGE_SIZE=' + (Get-Item -LiteralPath $PackagePath).Length)
    Write-Output ('PRODUCT_VERSION=' + $ExpectedVersion)
    Write-Output ('APPLICATION_COMMIT=' + $ExpectedSource)
    Write-Output ('DATABASE_REVISION=' + $ExpectedTarget)
} finally { $archive.Dispose() }
