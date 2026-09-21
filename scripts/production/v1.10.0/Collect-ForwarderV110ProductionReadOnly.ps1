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
    [string]$PgRestorePath = 'C:\Program Files\PostgreSQL\18\bin\pg_restore.exe',
    [switch]$ToolingSelfTest,
    [string]$SelfTestReleaseRoot,
    [string]$SelfTestWitnessPath,
    [string]$SelfTestProjectionFixturePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ExpectedBeforeRevision = '20260921_shipment_evidence_ownership'
$ExpectedTargetRevision = '20260926_fixed_shipment_responsible_expert'
$ExpectedProductVersion = '1.10.0'
$ExpectedApplicationCommit = 'e36ee7cee157657c97dc42a539eaf1909f510a33'
$ExpectedLegacySourceCommit = 'e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4'
$ExpectedLegacySourceArchiveSha256 = 'e9196ad9cc10dfeef44eba40d98e50520af4c505474211d5c23397bdf7774617'
$ExpectedLegacyInventorySha256 = '58baed2704b1301c749b2b194f203d6ffd68e9c8eb34536fb765c0e32297e1a5'
$ExpectedDatabaseBridgeSha256 = 'a94ce7bee93508a95f8bfff36620f77653c7a7008f5c0080b3f1a20199604c19'
$ExpectedAdr047Sha256 = '16a50c18a4e824ce35564beca18ea11131ed105d3d0d13f51e08ca021c780bae'
$ExpectedCompatibilitySha256 = '2b43889fee11fb78673e3d36e6117684f319b54fb963f4b3cc4cf7f19682c09b'
$CollectionErrors = New-Object 'System.Collections.Generic.List[string]'
$DatabaseBridgePath = Join-Path $PSScriptRoot 'Invoke-ForwarderV110ReadOnlySql.py'
$LegacyWitnessPath = Join-Path $PSScriptRoot 'legacy-production-witness.json'

function Add-CollectionError([string]$Code) {
    if (-not $CollectionErrors.Contains($Code)) { $CollectionErrors.Add($Code) }
}

function Redact-Text([string]$Value) {
    if ([string]::IsNullOrEmpty($Value)) { return $Value }
    $result = $Value
    $result = [regex]::Replace($result, '(?i)(postgres(?:ql)?://[^:/@\s]+:)[^@\s]+(@)', '$1[REDACTED]$2')
    $result = [regex]::Replace($result, '(?i)\b(password|passwd|pwd|secret|secret_key|jwt_secret_key|token|authorization|api_key)\s*[:=]\s*[^\s;,&]+', '$1=[REDACTED]')
    $result = [regex]::Replace($result, '(?i)(--(?:password|passwd|pwd|secret|secret-key|token|authorization|api-key)\s+)("[^"]*"|''[^'']*''|\S+)', '$1[REDACTED]')
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

function Get-BoundedText([string]$Value, [int]$Maximum = 1000) {
    $safe = Redact-Text $Value
    if ($null -eq $safe -or $safe.Length -le $Maximum) { return $safe }
    return $safe.Substring(0, $Maximum) + '[TRUNCATED]'
}

function Get-ObjectPropertyValue([object]$Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($property) { return $property.Value }
    return $null
}

function Get-FileSha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
}

function Test-PathWithin([string]$Child, [string]$Parent) {
    $childPath = Normalize-Path $Child; $parentPath = Normalize-Path $Parent
    if (-not $childPath -or -not $parentPath) { return $false }
    return ($childPath -eq $parentPath -or $childPath.StartsWith($parentPath + '\', [StringComparison]::OrdinalIgnoreCase))
}

function Get-TaskCandidateFromXml(
    [string]$CandidateName,
    [string]$CandidatePath,
    [string]$XmlText,
    [string]$ListenerRelease,
    [string]$ListenerExecutable,
    [int]$Port
) {
    [xml]$xml = $XmlText
    $actionNodes = @($xml.SelectNodes("/*[local-name()='Task']/*[local-name()='Actions']/*[local-name()='Exec']"))
    if ($actionNodes.Count -ne 1) {
        return [pscustomobject]@{
            name=$CandidateName; task_path=$CandidatePath; exact_listener_relationship=$false
            plausible=$true; reason='EXEC_ACTION_COUNT_UNEXPECTED'; release_path=$null
            action_executable=$null; action_runtime=$null; sanitized_arguments=$null; working_directory=$null
            evidence=[pscustomobject]@{ action_count=$actionNodes.Count; release_match=$false; runtime_match=$false; port_match=$false; waitress_match=$false; forwarder_name_match=($CandidateName -match '(?i)forwarder') }
        }
    }
    $action = $actionNodes[0]
    $command = Normalize-Path ([string]$action.Command)
    $arguments = Get-BoundedText ([string]$action.Arguments)
    $workingDirectory = Normalize-Path ([string]$action.WorkingDirectory)
    $combined = (([string]$action.Command) + ' ' + ([string]$action.Arguments) + ' ' + ([string]$action.WorkingDirectory))
    $runtimeMatches = @([regex]::Matches($combined, '(?i)[A-Z]:[\\/][^"''<>&|]*?[\\/]runtime[\\/]python\.exe') | ForEach-Object { Normalize-Path $_.Value } | Select-Object -Unique)
    if ($command -and [IO.Path]::GetFileName($command) -ieq 'python.exe' -and [IO.Path]::GetFileName((Split-Path -Parent $command)) -ieq 'runtime') {
        $runtimeMatches = @($runtimeMatches + $command | Select-Object -Unique)
    }
    $runtime = if ($runtimeMatches.Count -eq 1) { $runtimeMatches[0] } else { $null }
    $release = Get-ReleasePathFromText $combined
    if (-not $release -and $runtime) { $release = Normalize-Path (Split-Path -Parent (Split-Path -Parent $runtime)) }
    $releaseMatch = [bool]($ListenerRelease -and $release -and (Same-Path $ListenerRelease $release))
    $runtimeMatch = [bool]($ListenerExecutable -and $runtime -and (Same-Path $ListenerExecutable $runtime))
    $portMatch = [bool]($combined -match ("(?i)(--listen(?:=|\s+)127\.0\.0\.1:" + $Port + "\b|--port(?:=|\s+)" + $Port + "\b|127\.0\.0\.1:" + $Port + "\b)"))
    $waitressMatch = [bool]($combined -match '(?i)(waitress|backend\.wsgi:app|phase1b_production_cutover_runtime\.py)')
    $nameMatch = [bool](($CandidateName + ' ' + $CandidatePath) -match '(?i)forwarder')
    $exact = ($releaseMatch -and $runtimeMatch -and ($portMatch -or $waitressMatch))
    return [pscustomobject]@{
        name=$CandidateName; task_path=$CandidatePath; exact_listener_relationship=[bool]$exact
        plausible=[bool]($nameMatch -or $releaseMatch -or $runtimeMatch -or ($portMatch -and $waitressMatch))
        reason=$(if($exact){'EXACT_LISTENER_ACTION_MATCH'}elseif($runtimeMatches.Count -gt 1){'MULTIPLE_RUNTIME_PATHS'}else{'BOUNDED_EVIDENCE_INSUFFICIENT'})
        release_path=$release; action_executable=$command; action_runtime=$runtime
        sanitized_arguments=$arguments; working_directory=$workingDirectory
        evidence=[pscustomobject]@{
            action_count=1; release_match=$releaseMatch; runtime_match=$runtimeMatch; port_match=$portMatch
            waitress_match=$waitressMatch; forwarder_name_match=$nameMatch
        }
    }
}

function Select-ProvenTaskCandidate([object[]]$Candidates) {
    $plausible = @($Candidates | Where-Object {$_.plausible} | Select-Object -First 32)
    $exact = @($plausible | Where-Object {$_.exact_listener_relationship})
    if ($exact.Count -eq 1) { return [pscustomobject]@{ status='PROVEN'; selected=$exact[0]; candidates=$plausible } }
    if ($exact.Count -gt 1) { return [pscustomobject]@{ status='AMBIGUOUS'; selected=$null; candidates=$plausible } }
    return [pscustomobject]@{ status='UNPROVEN'; selected=$null; candidates=$plausible }
}

function Get-XmlChildText([System.Xml.XmlNode]$Node, [string]$LocalName) {
    if ($null -eq $Node) { return $null }
    $child = $Node.SelectSingleNode("./*[local-name()='$LocalName']")
    if ($null -eq $child) { return $null }
    return [string]$child.InnerText
}

function Get-UtcTimestamp([object]$Value) {
    if ($null -eq $Value -or [string]::IsNullOrWhiteSpace([string]$Value)) { return $null }
    try { return ([DateTime]$Value).ToUniversalTime().ToString('o') }
    catch { return $null }
}

function Get-NullableBoolean([object]$Value) {
    if ($null -eq $Value) { return $null }
    if ($Value -is [bool]) { return [bool]$Value }
    $text = ([string]$Value).Trim().ToLowerInvariant()
    if ($text -in @('true','1','yes','on')) { return $true }
    if ($text -in @('false','0','no','off')) { return $false }
    return $null
}

function New-SelectedTaskProjection(
    [object]$Selection,
    [object]$Task,
    [object]$Info,
    [string]$XmlText,
    [string]$PreferredNameHint
) {
    if ($null -eq $Selection -or $Selection.status -ne 'PROVEN' -or $null -eq $Selection.selected) {
        throw 'SELECTED_TASK_PROJECTION_REQUIRES_PROVEN_SELECTION'
    }
    $selected = $Selection.selected

    # These fields are the output of the bounded authority decision. Populate them
    # before reading optional Task Scheduler metadata so a missing optional XML node
    # can never erase the already-proven action/runtime/release relationship.
    $result = [pscustomobject]@{
        status='PROVEN'; metadata_status='PARTIAL'; preferred_name_hint=$PreferredNameHint
        name=[string]$selected.name; task_path=[string]$selected.task_path
        selection_reason=[string]$selected.reason
        exact_listener_relationship=[bool]$selected.exact_listener_relationship
        state=$null; enabled=$null; last_result=$null; last_run_utc=$null; next_run_utc=$null; principal=$null
        action_executable=$selected.action_executable; action_runtime=$selected.action_runtime
        sanitized_arguments=$selected.sanitized_arguments; working_directory=$selected.working_directory
        release_path=$selected.release_path
        trigger_count=$null; restart_count=$null; restart_interval=$null; multiple_instances_policy=$null
        candidate_count=@($Selection.candidates).Count; candidates=@($Selection.candidates)
    }

    $stateValue = Get-ObjectPropertyValue $Task 'State'
    if ($null -ne $stateValue) { $result.state = [string]$stateValue }
    $settings = Get-ObjectPropertyValue $Task 'Settings'
    $result.enabled = Get-NullableBoolean (Get-ObjectPropertyValue $settings 'Enabled')

    $lastResultValue = Get-ObjectPropertyValue $Info 'LastTaskResult'
    if ($null -ne $lastResultValue) {
        try { $result.last_result = [int64]$lastResultValue } catch { $result.last_result = $null }
    }
    $result.last_run_utc = Get-UtcTimestamp (Get-ObjectPropertyValue $Info 'LastRunTime')
    $result.next_run_utc = Get-UtcTimestamp (Get-ObjectPropertyValue $Info 'NextRunTime')

    if (-not [string]::IsNullOrWhiteSpace($XmlText)) {
        [xml]$selectedXml = $XmlText
        $principalNode = $selectedXml.SelectSingleNode("/*[local-name()='Task']/*[local-name()='Principals']/*[local-name()='Principal']")
        if ($null -ne $principalNode) {
            $userId = Get-BoundedText (Get-XmlChildText $principalNode 'UserId') 256
            $groupId = Get-BoundedText (Get-XmlChildText $principalNode 'GroupId') 256
            $result.principal = [pscustomobject]@{
                identity_type=$(if($userId){'USER'}elseif($groupId){'GROUP'}else{'UNAVAILABLE'})
                user_id=$userId; group_id=$groupId
                logon_type=(Get-XmlChildText $principalNode 'LogonType')
                run_level=(Get-XmlChildText $principalNode 'RunLevel')
            }
        }
        $triggerNodes = $selectedXml.SelectNodes("/*[local-name()='Task']/*[local-name()='Triggers']/*")
        $result.trigger_count = @($triggerNodes).Count
        $settingsNode = $selectedXml.SelectSingleNode("/*[local-name()='Task']/*[local-name()='Settings']")
        $restartNode = if ($null -ne $settingsNode) { $settingsNode.SelectSingleNode("./*[local-name()='RestartOnFailure']") } else { $null }
        $result.restart_count = Get-XmlChildText $restartNode 'Count'
        $result.restart_interval = Get-XmlChildText $restartNode 'Interval'
        $result.multiple_instances_policy = Get-XmlChildText $settingsNode 'MultipleInstancesPolicy'
        if ($null -eq $result.enabled) { $result.enabled = Get-NullableBoolean (Get-XmlChildText $settingsNode 'Enabled') }
    }

    if ($null -ne $result.state -and $null -ne $result.enabled -and $null -ne $result.last_result) {
        $result.metadata_status = 'AVAILABLE'
    }
    return $result
}

function Test-ListenerTaskOwnership([object[]]$Listeners, [object]$TaskResult, [string]$ActiveRelease) {
    if (@($Listeners).Count -ne 1 -or $null -eq $TaskResult -or $TaskResult.status -ne 'PROVEN') { return $false }
    $listener = @($Listeners)[0]
    return [bool](
        $listener.local_address -eq '127.0.0.1' -and
        [bool]$listener.waitress_contract -and
        [bool]$TaskResult.exact_listener_relationship -and
        (Same-Path ([string]$listener.executable) ([string]$TaskResult.action_runtime)) -and
        (Same-Path ([string]$listener.release_path) ([string]$TaskResult.release_path)) -and
        (Same-Path $ActiveRelease ([string]$TaskResult.release_path))
    )
}

function Get-FirstJsonValue([object]$Object, [string[]]$Names) {
    foreach ($name in $Names) {
        $property = $Object.PSObject.Properties[$name]
        if ($property -and -not [string]::IsNullOrWhiteSpace([string]$property.Value)) { return [string]$property.Value }
    }
    return $null
}

function Get-GovernedReleaseManifest([string]$ReleasePath, [hashtable]$EnvironmentMap) {
    $paths = New-Object 'System.Collections.Generic.List[string]'
    foreach ($candidate in @(
        (Join-Path $ReleasePath 'release-manifest.json'),
        (Join-Path $ReleasePath 'RELEASE-METADATA.json'),
        (Join-Path $ReleasePath 'artifact\release-manifest.json')
    )) {
        $normalized = Normalize-Path $candidate
        if ($normalized -and -not $paths.Contains($normalized)) { $paths.Add($normalized) }
    }
    if ($EnvironmentMap.ContainsKey('RELEASE_IDENTITY_PATH') -and $EnvironmentMap['RELEASE_IDENTITY_PATH']) {
        $configured = Normalize-Path ([string]$EnvironmentMap['RELEASE_IDENTITY_PATH'])
        if ($configured -and (Test-PathWithin $configured $ReleasePath) -and -not $paths.Contains($configured)) { $paths.Add($configured) }
    }
    $found = New-Object 'System.Collections.Generic.List[object]'
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
        $value = Get-Content -Raw -LiteralPath $path -ErrorAction Stop | ConvertFrom-Json
        $commit = Get-FirstJsonValue $value @('application_commit','application_source_commit','source_commit','git_commit')
        if ($commit -and $commit -notmatch '^[0-9a-fA-F]{40}$') { $commit = $null }
        $found.Add([pscustomobject]@{
            path=$path; sha256=Get-FileSha256 $path; schema=(Get-FirstJsonValue $value @('schema'))
            candidate=(Get-FirstJsonValue $value @('candidate','product_name'))
            application_version=(Get-FirstJsonValue $value @('application_version','product_version','version'))
            application_commit=$(if($commit){$commit.ToLowerInvariant()}else{$null})
            database_revision=(Get-FirstJsonValue $value @('database_revision','required_db_revision','alembic_head','migration_head'))
            runtime_sha256=(Get-FirstJsonValue $value @('runtime_sha256'))
        })
    }
    if ($found.Count -eq 0) { return [pscustomobject]@{ status='ABSENT'; governed_locations=$paths.ToArray(); records=@(); identity=$null } }
    $commits = @($found | Where-Object {$_.application_commit} | Select-Object -ExpandProperty application_commit -Unique)
    if ($commits.Count -gt 1) { return [pscustomobject]@{ status='CONFLICT'; governed_locations=$paths.ToArray(); records=$found.ToArray(); identity=$null } }
    $selected = @($found | Where-Object {$_.application_commit} | Select-Object -First 1)
    if ($selected.Count -ne 1) { return [pscustomobject]@{ status='IDENTITY_INCOMPLETE'; governed_locations=$paths.ToArray(); records=$found.ToArray(); identity=$null } }
    return [pscustomobject]@{ status='IDENTITY_PROVEN'; governed_locations=$paths.ToArray(); records=$found.ToArray(); identity=$selected[0] }
}

function Get-LegacyWitnessEvidence([string]$ReleasePath, [string]$WitnessPath) {
    if (-not (Test-Path -LiteralPath $WitnessPath -PathType Leaf)) {
        return [pscustomobject]@{ status='WITNESS_UNAVAILABLE'; witness_path=(Normalize-Path $WitnessPath); identity=$null }
    }
    $witness = Get-Content -Raw -LiteralPath $WitnessPath -ErrorAction Stop | ConvertFrom-Json
    if ($witness.schema -ne 'forwarder-v1.10.0-legacy-production-witness-v1' -or $witness.application_source_commit -notmatch '^[0-9a-f]{40}$') {
        return [pscustomobject]@{ status='WITNESS_INVALID'; witness_path=(Normalize-Path $WitnessPath); identity=$null }
    }
    $canonical = New-Object Text.StringBuilder
    $missing = New-Object 'System.Collections.Generic.List[string]'
    $mismatched = New-Object 'System.Collections.Generic.List[string]'
    $matched = 0; $frontendMatched = 0; $backendMatched = 0
    foreach ($record in @($witness.files)) {
        $relative = ([string]$record.path).Replace('\','/')
        if (-not $relative -or $relative.StartsWith('/') -or $relative -match '(^|/)\.\.(/|$)' -or $relative -match ':') {
            return [pscustomobject]@{ status='WITNESS_INVALID'; witness_path=(Normalize-Path $WitnessPath); identity=$null }
        }
        [void]$canonical.Append($relative).Append([char]0).Append(([string]$record.sha256).ToLowerInvariant()).Append("`n")
        $path = Join-Path $ReleasePath $relative.Replace('/','\')
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { if($missing.Count -lt 12){$missing.Add($relative)}; continue }
        $item = Get-Item -LiteralPath $path -ErrorAction Stop
        if ($item.Length -ne [int64]$record.bytes -or (Get-FileSha256 $path) -ne ([string]$record.sha256).ToLowerInvariant()) {
            if($mismatched.Count -lt 12){$mismatched.Add($relative)}; continue
        }
        $matched++
        if ($relative.StartsWith('dist/')) { $frontendMatched++ }
        if ($relative.StartsWith('backend/')) { $backendMatched++ }
    }
    $canonicalHash = Get-TextSha256 $canonical.ToString()
    if ($canonicalHash -ne [string]$witness.inventory_sha256 -or @($witness.files).Count -ne [int]$witness.file_count) {
        return [pscustomobject]@{ status='WITNESS_INVALID'; witness_path=(Normalize-Path $WitnessPath); identity=$null }
    }
    $status = if ($matched -eq [int]$witness.file_count) { 'MATCH' } else { 'MISMATCH' }
    return [pscustomobject]@{
        status=$status; witness_path=(Normalize-Path $WitnessPath); witness_sha256=(Get-FileSha256 $WitnessPath)
        source_archive_sha256=[string]$witness.source_archive_sha256; inventory_sha256=$canonicalHash
        expected_file_count=[int]$witness.file_count; matched_file_count=$matched
        expected_frontend_file_count=[int]$witness.frontend_file_count; matched_frontend_file_count=$frontendMatched
        expected_backend_file_count=[int]$witness.backend_file_count; matched_backend_file_count=$backendMatched
        missing_paths=$missing.ToArray(); mismatched_paths=$mismatched.ToArray()
        identity=[pscustomobject]@{
            source='LEGACY_PRODUCTION_WITNESS'; candidate=[string]$witness.candidate
            application_commit=[string]$witness.application_source_commit; application_version=$witness.application_version
            database_revision=[string]$witness.required_database_revision
        }
    }
}

function Invoke-ToolingSelfTest {
    $release = 'C:\1-webapp\forwarder-production\release-legacy-live'
    $runtime = $release + '\runtime\python.exe'
    $wrongNameXml = '<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c "' + $runtime + '" -m waitress --listen=127.0.0.1:5101 backend.wsgi:app</Arguments><WorkingDirectory>' + $release + '</WorkingDirectory></Exec></Actions></Task>'
    $unrelatedXml = '<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c echo maintenance</Arguments><WorkingDirectory>C:\Windows</WorkingDirectory></Exec></Actions></Task>'
    $good = Get-TaskCandidateFromXml 'Established Runtime Task' '\Operations\' $wrongNameXml $release $runtime 5101
    $unrelated = Get-TaskCandidateFromXml 'Forwarder Cleanup' '\' $unrelatedXml $release $runtime 5101
    $selection = Select-ProvenTaskCandidate @($unrelated,$good)
    if ($selection.status -ne 'PROVEN' -or $selection.selected.name -ne 'Established Runtime Task') { throw 'TASK_DISCOVERY_SELF_TEST_FAILED' }
    $ambiguous = Select-ProvenTaskCandidate @($good,$good)
    if ($ambiguous.status -ne 'AMBIGUOUS') { throw 'TASK_AMBIGUITY_SELF_TEST_FAILED' }
    Write-Output 'TASK_NAME_MISMATCH_WITH_EXACT_ACTION=PASS'
    Write-Output 'TASK_AMBIGUITY=FAIL_CLOSED'
    if ($SelfTestProjectionFixturePath) {
        $fixture = Get-Content -Raw -LiteralPath $SelfTestProjectionFixturePath -ErrorAction Stop | ConvertFrom-Json
        $fixtureCandidates = @($fixture.scheduled_task.candidates)
        $fixtureSelection = Select-ProvenTaskCandidate $fixtureCandidates
        if ($fixtureSelection.status -ne 'PROVEN') { throw 'R2_PROJECTION_FIXTURE_SELECTION_FAILED' }
        $metadata = $fixture.task_scheduler_metadata
        $fixtureTask = [pscustomobject]@{
            TaskName=[string]$metadata.task.task_name; TaskPath=[string]$metadata.task.task_path
            State=[string]$metadata.task.state
            Settings=[pscustomobject]@{ Enabled=[bool]$metadata.task.enabled }
        }
        $fixtureInfo = [pscustomobject]@{
            LastTaskResult=[int64]$metadata.info.last_result
            LastRunTime=[DateTime]$metadata.info.last_run_utc
            NextRunTime=[DateTime]$metadata.info.next_run_utc
        }
        $projection = New-SelectedTaskProjection $fixtureSelection $fixtureTask $fixtureInfo ([string]$metadata.xml) $TaskName
        $candidate = $fixtureSelection.selected
        $criticalMatches = (
            $projection.status -eq 'PROVEN' -and $projection.metadata_status -eq 'AVAILABLE' -and
            $projection.name -eq $candidate.name -and $projection.task_path -eq $candidate.task_path -and
            (Same-Path $projection.action_executable $candidate.action_executable) -and
            (Same-Path $projection.action_runtime $candidate.action_runtime) -and
            $projection.sanitized_arguments -eq $candidate.sanitized_arguments -and
            (Same-Path $projection.working_directory $candidate.working_directory) -and
            (Same-Path $projection.release_path $candidate.release_path)
        )
        if (-not $criticalMatches) { throw 'R2_SELECTED_TASK_PROJECTION_SELF_TEST_FAILED' }
        $fixtureListener = [pscustomobject]@{
            local_address=[string]$fixture.listeners[0].local_address
            executable=[string]$fixture.listeners[0].executable
            release_path=[string]$fixture.listeners[0].release_path
            waitress_contract=[bool]$fixture.listeners[0].waitress_contract
        }
        if (-not (Test-ListenerTaskOwnership @($fixtureListener) $projection ([string]$fixture.active_release_path))) {
            throw 'R2_LISTENER_OWNERSHIP_SELF_TEST_FAILED'
        }
        $mismatchedProjection = $projection.PSObject.Copy()
        $mismatchedProjection.action_runtime = 'C:\unrelated\runtime\python.exe'
        if (Test-ListenerTaskOwnership @($fixtureListener) $mismatchedProjection ([string]$fixture.active_release_path)) {
            throw 'R2_LISTENER_OWNERSHIP_MISMATCH_NOT_CLOSED'
        }
        Write-Output 'R2_SELECTED_TASK_PROJECTION=PASS'
        Write-Output 'R2_LISTENER_OWNERSHIP=TRUE'
        Write-Output 'R2_LISTENER_OWNERSHIP_MISMATCH=FAIL_CLOSED'
    }
    if ($SelfTestReleaseRoot -or $SelfTestWitnessPath) {
        if (-not $SelfTestReleaseRoot -or -not $SelfTestWitnessPath) { throw 'SELF_TEST_WITNESS_ARGUMENTS_INCOMPLETE' }
        $evidence = Get-LegacyWitnessEvidence $SelfTestReleaseRoot $SelfTestWitnessPath
        if ($evidence.status -ne 'MATCH') { throw 'LEGACY_WITNESS_SELF_TEST_FAILED' }
        Write-Output 'LEGACY_RELEASE_WITHOUT_MANIFEST=IDENTITY_PROVEN_BY_WITNESS'
    }
    Write-Output 'PRODUCTION_MUTATION_PERFORMED=NO'
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

function Assert-ReadOnlySql([string]$Sql, [string]$Name) {
    if ($Sql -notmatch '(?is)^\s*BEGIN\s+TRANSACTION\s+READ\s+ONLY\s*;' -or $Sql -notmatch '(?is)COMMIT\s*;\s*$') {
        throw "SQL_READ_ONLY_ENVELOPE_INVALID:$Name"
    }
    $forbidden = '(?im)\b(INSERT|UPDATE|DELETE|MERGE|ALTER|CREATE|DROP|TRUNCATE|GRANT|REVOKE|VACUUM|REINDEX|CALL|DO)\b'
    if ($Sql -match $forbidden) { throw "SQL_MUTATION_KEYWORD_REJECTED:$Name" }
}

function ConvertTo-ProcessArgument([string]$Value) {
    if ($Value -match '["\r\n]') { throw 'PROCESS_ARGUMENT_UNSAFE' }
    return '"' + $Value + '"'
}

function Invoke-ReadOnlySql([string]$Sql, [string]$DatabasePython, [string]$Name) {
    Assert-ReadOnlySql $Sql $Name
    if (-not (Test-Path -LiteralPath $DatabasePython -PathType Leaf)) { throw 'DATABASE_RUNTIME_PYTHON_NOT_AVAILABLE' }
    if (-not (Test-Path -LiteralPath $DatabaseBridgePath -PathType Leaf)) { throw 'DATABASE_READ_ONLY_BRIDGE_NOT_AVAILABLE' }
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = $DatabasePython
    $start.Arguments = '-B ' + (ConvertTo-ProcessArgument $DatabaseBridgePath) + ' --environment-file ' + (ConvertTo-ProcessArgument $EnvironmentFile) + ' --psql ' + (ConvertTo-ProcessArgument $PsqlPath)
    $start.WorkingDirectory = $PSScriptRoot
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.EnvironmentVariables['PYTHONDONTWRITEBYTECODE'] = '1'
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start
    try {
        if (-not $process.Start()) { throw 'DATABASE_READ_ONLY_BRIDGE_START_FAILED' }
        $process.StandardInput.Write($Sql)
        $process.StandardInput.Close()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(120000)) { $process.Kill(); throw 'DATABASE_READ_ONLY_BRIDGE_TIMEOUT' }
        $output = [string]$stdout.Result
        $errorText = Redact-Text ([string]$stderr.Result)
        if ($process.ExitCode -ne 0) { throw ('DATABASE_READ_ONLY_BRIDGE_FAILED_' + $Name + ':' + $errorText.Substring(0, [Math]::Min(160, $errorText.Length))) }
        return @($output -split "`r?`n" | Where-Object { $_ -match '\S' })
    } finally {
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

if ($ToolingSelfTest) { Invoke-ToolingSelfTest; exit 0 }

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
        task_release_match=$false
    })
}
$activeRelease = $null
if ($listeners.Count -eq 1 -and $listeners[0].release_path) { $activeRelease = $listeners[0].release_path }
$listenerExecutable = if ($listeners.Count -eq 1) { [string]$listeners[0].executable } else { $null }

$taskCandidates = New-Object 'System.Collections.Generic.List[object]'
$taskCandidateRecords = New-Object 'System.Collections.Generic.List[object]'
$taskObjects = @(Invoke-Safe 'SCHEDULED_TASK_ENUMERATION_FAILED' { Get-ScheduledTask -ErrorAction Stop })
foreach ($task in $taskObjects) {
    $actionHint = @($task.Actions | ForEach-Object {
        ([string](Get-ObjectPropertyValue $_ 'Execute')) + ' ' + ([string](Get-ObjectPropertyValue $_ 'Arguments')) + ' ' + ([string](Get-ObjectPropertyValue $_ 'WorkingDirectory'))
    }) -join ' '
    $hint = ([string]$task.TaskName) + ' ' + ([string]$task.TaskPath) + ' ' + $actionHint
    $plausibleHint = ($hint -match '(?i)forwarder|runtime[\\/]python\.exe|waitress|backend\.wsgi:app') -or ($hint -match ("(?i)127\.0\.0\.1:" + $BackendPort + "\b"))
    if (-not $plausibleHint -and $activeRelease) { $plausibleHint = ($hint.IndexOf($activeRelease, [StringComparison]::OrdinalIgnoreCase) -ge 0) }
    if (-not $plausibleHint) { continue }
    if ($taskCandidates.Count -ge 32) { Add-CollectionError 'SCHEDULED_TASK_CANDIDATE_LIMIT_EXCEEDED'; break }
    try {
        $xmlText = Export-ScheduledTask -TaskName ([string]$task.TaskName) -TaskPath ([string]$task.TaskPath) -ErrorAction Stop
        $candidate = Get-TaskCandidateFromXml ([string]$task.TaskName) ([string]$task.TaskPath) $xmlText $activeRelease $listenerExecutable $BackendPort
        if ($candidate.plausible) {
            $taskCandidates.Add($candidate)
            $taskCandidateRecords.Add([pscustomobject]@{ task=$task; xml_text=$xmlText; candidate=$candidate })
        }
    } catch { Add-CollectionError 'SCHEDULED_TASK_CANDIDATE_INSPECTION_FAILED' }
}

$taskSelection = Select-ProvenTaskCandidate $taskCandidates.ToArray()
$taskResult = [pscustomobject]@{
    status=$taskSelection.status; metadata_status='UNAVAILABLE'; preferred_name_hint=$TaskName; name=$null; task_path=$null
    selection_reason=$null; exact_listener_relationship=$false; state=$null; enabled=$null
    last_result=$null; last_run_utc=$null; next_run_utc=$null; principal=$null
    action_executable=$null; action_runtime=$null; sanitized_arguments=$null; working_directory=$null; release_path=$null
    trigger_count=$null; restart_count=$null; restart_interval=$null; multiple_instances_policy=$null
    candidate_count=@($taskSelection.candidates).Count; candidates=@($taskSelection.candidates)
}
if ($taskSelection.status -eq 'PROVEN') {
    $selected = $taskSelection.selected
    $taskResult = New-SelectedTaskProjection $taskSelection $null $null $null $TaskName
    try {
        $records = @($taskCandidateRecords | Where-Object {
            $_.candidate.name -eq $selected.name -and $_.candidate.task_path -eq $selected.task_path
        })
        if ($records.Count -ne 1) { throw 'SELECTED_TASK_CACHED_RECORD_NOT_UNIQUE' }
        $record = $records[0]
        $info = Get-ScheduledTaskInfo -InputObject $record.task -ErrorAction Stop
        $taskResult = New-SelectedTaskProjection $taskSelection $record.task $info ([string]$record.xml_text) $TaskName
    } catch {
        Add-CollectionError 'SCHEDULED_TASK_SELECTED_METADATA_FAILED'
        $taskResult.status='UNPROVEN'; $taskResult.metadata_status='FAILED'
    }
} elseif ($taskSelection.status -eq 'AMBIGUOUS') {
    Add-CollectionError 'SCHEDULED_TASK_IDENTITY_AMBIGUOUS'
} else {
    Add-CollectionError 'SCHEDULED_TASK_IDENTITY_UNPROVEN'
}
if (-not $activeRelease -and $taskResult.release_path) { $activeRelease = $taskResult.release_path }
foreach ($listener in $listeners) {
    $listener.task_release_match=[bool]($taskResult.status -eq 'PROVEN' -and $listener.release_path -and (Same-Path $listener.release_path $taskResult.release_path))
    $listener | Add-Member -NotePropertyName task_runtime_match -NotePropertyValue ([bool]($taskResult.status -eq 'PROVEN' -and $listener.executable -and (Same-Path $listener.executable $taskResult.action_runtime))) -Force
}
$listenerOwnership = Test-ListenerTaskOwnership $listeners.ToArray() $taskResult $activeRelease

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

$manifestResult = $null
$legacyWitnessResult = $null
$releaseIdentity = $null
if ($activeRelease) {
    $manifestResult = Invoke-Safe 'RELEASE_IDENTITY_INSPECTION_FAILED' { Get-GovernedReleaseManifest $activeRelease $envMap }
    if ($manifestResult -and $manifestResult.status -eq 'CONFLICT') { Add-CollectionError 'RELEASE_IDENTITY_CONFLICT' }
    if ($manifestResult -and $manifestResult.status -eq 'IDENTITY_PROVEN') {
        $releaseIdentity = [pscustomobject]@{
            status='PROVEN'; source='GOVERNED_RELEASE_MANIFEST'; candidate=$manifestResult.identity.candidate
            application_commit=$manifestResult.identity.application_commit; application_version=$manifestResult.identity.application_version
            database_revision=$manifestResult.identity.database_revision
        }
    } else {
        $legacyWitnessResult = Invoke-Safe 'LEGACY_RELEASE_WITNESS_INSPECTION_FAILED' { Get-LegacyWitnessEvidence $activeRelease $LegacyWitnessPath }
        $legacyWitnessAuthorityValid = (
            $legacyWitnessResult -and $legacyWitnessResult.status -eq 'MATCH' -and
            $legacyWitnessResult.identity.application_commit -eq $ExpectedLegacySourceCommit -and
            $legacyWitnessResult.source_archive_sha256 -eq $ExpectedLegacySourceArchiveSha256 -and
            $legacyWitnessResult.inventory_sha256 -eq $ExpectedLegacyInventorySha256 -and
            $legacyWitnessResult.identity.database_revision -eq $ExpectedBeforeRevision
        )
        if ($legacyWitnessAuthorityValid) {
            $releaseIdentity = [pscustomobject]@{
                status='PROVEN'; source='LEGACY_PRODUCTION_WITNESS'; candidate=$legacyWitnessResult.identity.candidate
                application_commit=$legacyWitnessResult.identity.application_commit; application_version=$legacyWitnessResult.identity.application_version
                database_revision=$legacyWitnessResult.identity.database_revision
            }
        } elseif ($legacyWitnessResult -and $legacyWitnessResult.status -eq 'MATCH') {
            $legacyWitnessResult.status='WITNESS_AUTHORITY_MISMATCH'
            Add-CollectionError 'LEGACY_RELEASE_WITNESS_AUTHORITY_MISMATCH'
        }
    }
}
if (-not $releaseIdentity) {
    Add-CollectionError 'ACTIVE_RELEASE_SOURCE_IDENTITY_UNPROVEN'
    $releaseIdentity = [pscustomobject]@{ status='UNKNOWN'; source=$null; candidate=$null; application_commit=$null; application_version=$null; database_revision=$null }
}
$releaseIdentityVerified = ($releaseIdentity.status -eq 'PROVEN' -and $releaseIdentity.application_commit -match '^[0-9a-f]{40}$')

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

$database = [ordered]@{
    collection='UNAVAILABLE'; connection_model='ACTIVE_RUNTIME_PYTHON_DOTENV_SQLALCHEMY_TO_PSQL'
    bridge_sha256=$null; bridge_identity_verified=$false; sql_payload_identity_verified=$false
    failure_reason=$null; identity=$null; adr047=$null; compatibility=@(); schema_drift_blocker_count=$null
}
$databasePython = if ($listeners.Count -eq 1) { [string]$listeners[0].executable } else { $null }
$databaseBridgeVerified = $false
if (Test-Path -LiteralPath $DatabaseBridgePath -PathType Leaf) {
    $database.bridge_sha256 = Get-FileSha256 $DatabaseBridgePath
    $databaseBridgeVerified = ($database.bridge_sha256 -eq $ExpectedDatabaseBridgeSha256)
    $database.bridge_identity_verified = [bool]$databaseBridgeVerified
    if (-not $databaseBridgeVerified) { Add-CollectionError 'DATABASE_READ_ONLY_BRIDGE_IDENTITY_MISMATCH' }
}
$adr047Path = Join-Path (Join-Path $PSScriptRoot 'sql') 'adr047-production-classifier.sql'
$compatibilityPath = Join-Path (Join-Path $PSScriptRoot 'sql') 'migration-compatibility-readonly.sql'
$sqlPayloadsVerified = (
    (Test-Path -LiteralPath $adr047Path -PathType Leaf) -and (Get-FileSha256 $adr047Path) -eq $ExpectedAdr047Sha256 -and
    (Test-Path -LiteralPath $compatibilityPath -PathType Leaf) -and (Get-FileSha256 $compatibilityPath) -eq $ExpectedCompatibilitySha256
)
$database.sql_payload_identity_verified = [bool]$sqlPayloadsVerified
if (-not $sqlPayloadsVerified) { Add-CollectionError 'DATABASE_READ_ONLY_SQL_IDENTITY_MISMATCH' }
$databasePrerequisites = ($environment.Present -and $envMap.ContainsKey('DATABASE_URL') -and $envMap['DATABASE_URL'] -and $databasePython -and (Test-Path -LiteralPath $databasePython -PathType Leaf) -and $databaseBridgeVerified -and $sqlPayloadsVerified)
if ($databasePrerequisites) {
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
        $identityRows = @(Invoke-ReadOnlySql $identitySql $databasePython 'database_identity')
        $identityMap = @{}
        foreach($row in $identityRows){$parts=$row.Split('|',2);if($parts.Count -eq 2){$identityMap[$parts[0]]=$parts[1]}}
        foreach($requiredIdentity in @('POSTGRESQL_VERSION','DATABASE_NAME','DATABASE_ROLE','PRIMARY_STATE','DATABASE_SIZE_BYTES','DATABASE_UTC','ALEMBIC_REVISION_COUNT','ALEMBIC_REVISION')) {
            if (-not $identityMap.ContainsKey($requiredIdentity)) { throw ('DATABASE_IDENTITY_RESULT_MISSING_' + $requiredIdentity) }
        }
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
        $adrRows = @(Invoke-ReadOnlySql (Read-SqlFile 'adr047-production-classifier.sql') $databasePython 'adr047_classifier')
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
        $database.compatibility = @(Convert-CheckRows (Invoke-ReadOnlySql (Read-SqlFile 'migration-compatibility-readonly.sql') $databasePython 'migration_compatibility'))
        $database.schema_drift_blocker_count = @($database.compatibility | Where-Object {$_.state -ne 'PASS'}).Count
        $database.collection = 'AVAILABLE'
    } catch {
        Add-CollectionError 'DATABASE_READ_ONLY_COLLECTION_FAILED'
        $database.collection = 'UNAVAILABLE'
        $database.failure_reason = Get-BoundedText ([string]$_.Exception.Message) 240
    }
} else {
    Add-CollectionError 'DATABASE_CONNECTION_MODEL_UNAVAILABLE'
    $missingDatabasePrerequisites = New-Object 'System.Collections.Generic.List[string]'
    if (-not $environment.Present) { $missingDatabasePrerequisites.Add('ENVIRONMENT_FILE') }
    if (-not $envMap.ContainsKey('DATABASE_URL') -or -not $envMap['DATABASE_URL']) { $missingDatabasePrerequisites.Add('DATABASE_URL') }
    if (-not $databasePython -or -not (Test-Path -LiteralPath $databasePython -PathType Leaf)) { $missingDatabasePrerequisites.Add('ACTIVE_RUNTIME_PYTHON') }
    if (-not $databaseBridgeVerified) { $missingDatabasePrerequisites.Add('VERIFIED_READ_ONLY_DATABASE_BRIDGE') }
    if (-not $sqlPayloadsVerified) { $missingDatabasePrerequisites.Add('VERIFIED_READ_ONLY_SQL_PAYLOADS') }
    $database.failure_reason = 'MISSING_' + ($missingDatabasePrerequisites -join '_')
}

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
    latest_dump=$null; catalog_validation_available=$false; restore_evidence_available=$false; restore_evidence=$null
    fresh_deployment_window_backup_present=$false; fresh_deployment_window_backup_required=$true
    deployment_prerequisite_status='PENDING_FRESH_BACKUP_AND_RESTORE_PROOF'; capacity_status='UNKNOWN'
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
            restore_evidence_sidecar_present=(Test-Path -LiteralPath ($latest.FullName+'.restore-evidence.json') -PathType Leaf)
        }
        $backup.catalog_validation_available=[bool]$backup.latest_dump.catalog_sidecar_present
        if ($backup.latest_dump.restore_evidence_sidecar_present) {
            try {
                $restoreEvidence = Get-Content -Raw -LiteralPath ($latest.FullName+'.restore-evidence.json') -ErrorAction Stop | ConvertFrom-Json
                $restoreValid = (
                    $restoreEvidence.schema -eq 'forwarder-production-restore-evidence-v1' -and
                    $restoreEvidence.restore_test_status -eq 'PASS' -and
                    $restoreEvidence.source_dump_sha256 -match '^[0-9a-fA-F]{64}$' -and
                    $restoreEvidence.restored_database_disposable -eq $true -and
                    -not [string]::IsNullOrWhiteSpace([string]$restoreEvidence.tested_utc)
                )
                $backup.restore_evidence=[pscustomobject]@{
                    state=$(if($restoreValid){'VERIFIED_METADATA'}else{'INVALID_METADATA'})
                    tested_utc=$(if($restoreValid){[string]$restoreEvidence.tested_utc}else{$null})
                    source_dump_sha256=$(if($restoreValid){([string]$restoreEvidence.source_dump_sha256).ToLowerInvariant()}else{$null})
                    restored_database_disposable=$(if($restoreValid){$true}else{$false})
                }
                $backup.restore_evidence_available=[bool]$restoreValid
            } catch {
                $backup.restore_evidence=[pscustomobject]@{ state='UNREADABLE_METADATA'; tested_utc=$null; source_dump_sha256=$null; restored_database_disposable=$false }
            }
        }
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

$runtimeAgreement = ($activeRelease -and $taskResult.status -eq 'PROVEN' -and (Same-Path $activeRelease $taskResult.release_path) -and $iisResult -and (Same-Path $iisResult.physical_path (Join-Path $activeRelease 'dist')) -and $listenerOwnership)
$databaseGate = ($database.collection -eq 'AVAILABLE' -and $database.identity.alembic_revision_count -eq 1 -and $database.identity.alembic_revision -eq $ExpectedBeforeRevision -and $database.identity.primary_state -eq 'PRIMARY' -and $database.schema_drift_blocker_count -eq 0 -and $database.adr047.fixed_owner_ambiguous_count -eq 0 -and $database.adr047.fixed_owner_contradiction_count -eq 0 -and $database.adr047.fixed_owner_other_unresolved_count -eq 0)
$configGate = ($invalidConfig -eq 0 -and $config['AUTO_MIGRATE_ON_STARTUP'].state -notin @('SAFE_VALUE_INVALID') -and $config['CORS_ALLOW_ALL_ORIGINS'].state -notin @('SAFE_VALUE_INVALID'))
$collectorStatus = if ($CollectionErrors.Count -eq 0 -and $runtimeAgreement -and $releaseIdentityVerified -and $databaseGate -and $configGate -and $backup.mechanism_identified -and $backup.tooling_available) { 'PASS' } else { 'BLOCKED' }
$deploymentPrerequisiteStatus = if ($collectorStatus -ne 'PASS') { 'BLOCKED_COLLECTOR' } elseif (-not $backup.restore_evidence_available -or -not $backup.fresh_deployment_window_backup_present) { 'BLOCKED_FRESH_BACKUP_AND_RESTORE_PROOF_REQUIRED' } else { 'READY_FOR_SEPARATE_GO_REVIEW' }

$result = [ordered]@{
    schema='forwarder-v1.10.0-production-readonly-preflight-v1'
    generated_utc=$generatedUtc.ToString('o')
    collector_status=$collectorStatus
    product_contract=[ordered]@{ target_product_version=$ExpectedProductVersion; target_application_commit=$ExpectedApplicationCommit; before_database_revision=$ExpectedBeforeRevision; target_database_revision=$ExpectedTargetRevision }
    host=$hostInfo
    active_release=[ordered]@{
        release_root=(Normalize-Path $ReleaseRoot); active_release_path=$activeRelease; directories=$releaseDirectories
        manifest=$manifestResult; legacy_witness=$legacyWitnessResult; identity=$releaseIdentity
        source_identity_verified=[bool]$releaseIdentityVerified; runtime_agreement=[bool]$runtimeAgreement
    }
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
    deployment_prerequisite_status=$deploymentPrerequisiteStatus
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
