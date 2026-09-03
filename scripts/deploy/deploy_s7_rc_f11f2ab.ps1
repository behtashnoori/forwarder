#requires -Version 5.1
<#
Governed Forwarder S7-R2 deployment entrypoint.  It is inert unless -Execute is
given.  -SimulationRoot is for local orchestration tests only and never contacts
Production.
#>
[CmdletBinding()]
param(
    [switch]$ValidateOnly,
    [switch]$Execute,
    [switch]$ConfirmDeployment,
    [string]$ArtifactPath,
    [string]$ManifestPath,
    [string]$SimulationRoot,
    [string]$QualificationRoot,
    [string]$BaselinePath,
    [string]$PsqlPath = 'C:\Program Files\PostgreSQL\18\bin\psql.exe',
    [switch]$SimulateVerificationFailure,
    [switch]$SimulateStagingFailure
)

$ErrorActionPreference = 'Stop'
$CandidateId = 'S7-RC-f11f2ab'
$SourceCommit = 'f11f2abfbff396f66f261f11c7f4bdb80b2d2007'
$ArtifactName = 'Forwarder-S7-RC-f11f2ab.zip'
$ArtifactHash = 'a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d'
$ManifestHash = '4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f'
$TargetHead = '20260907_direct_shipment_responsibility'
$ExpectedHost = 'SRV8756807400'
$ExpectedDatabase = 'forwarder_prod_20260728_161711'
$TaskName = 'Forwarder Backend Production'
$Port = 5101
$CanonicalOrigin = 'https://samand.forwarderet.ir'
$LegacyOrigin = 'https://server.logisticmarket.ir'
$RuntimeWrapperHash = 'f99238f35468a3bec7d387b62493e5b1af3efa721801f93bbd90a21d5f8ecbc7'
$script:State = 'PRECHECK'
$script:Mutated = $false
$script:PrecheckCount = 0
$script:Evidence = [ordered]@{ candidate_id=$CandidateId; source_commit=$SourceCommit; states=@(); outcome=$null }
$script:ExpectedDatabase = $ExpectedDatabase
$script:ExpectedAlembic = $TargetHead
$script:PassedPrecheckCount = 0
$script:IisInspectionReady = $false
$script:BackendStopped = $false
$script:TargetReleaseOwned = $false

function Set-State([string]$Value) { $script:State=$Value; $script:Evidence.states += $Value; Write-Output "STATE=$Value" }
function Fail([string]$Message) { throw "DEPLOYMENT_GATE: $Message" }
function Require([object]$Condition,[string]$Message) {
    $script:PrecheckCount++
    $label='PRECHECK_{0:D2}' -f $script:PrecheckCount
    $runtimeType=if($null -eq $Condition){'<null>'}else{$Condition.GetType().FullName}
    $caller=(Get-PSCallStack)[1]
    Write-Host "$label`_GATE=$($caller.FunctionName):$($caller.ScriptLineNumber):$Message"
    Write-Host "$label`_RUNTIME_TYPE=$runtimeType"
    if($runtimeType -ne 'System.Boolean'){ Fail "TOOLING_DEFECT: Boolean gate '$Message' produced $runtimeType" }
    if(-not $Condition){ Write-Host "$label=FAIL"; Write-Host "GATE=$Message"; Write-Host 'RESULT=FAIL'; Fail $Message }
    $script:PassedPrecheckCount++
    Write-Host "$label=PASS"
}
function Hash([string]$Path) { $stream=[IO.File]::OpenRead($Path);$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$stream.Dispose();$sha.Dispose()} }
function Atomic-Copy([string]$Source,[string]$Destination) { $tmp="$Destination.$([guid]::NewGuid().ToString('N')).tmp"; Copy-Item -LiteralPath $Source -Destination $tmp -Force; Move-Item -LiteralPath $tmp -Destination $Destination -Force }
function Env-Map([string]$Path) {
    $map=[ordered]@{}
    foreach($line in [IO.File]::ReadAllLines($Path)){
        $normalizedLine=$line.TrimStart([char]0xFEFF)
        if($normalizedLine -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$'){
            $key=$Matches[1]; $value=$Matches[2].Trim()
            if($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))){$value=$value.Substring(1,$value.Length-2).Trim()}
            if($map.Contains($key)){ Fail "duplicate configuration key: $key" }
            $map[$key]=$value
        }
    }
    return $map
}
function Validate-Env([string]$Path) {
    $envMap=Env-Map $Path
    foreach($key in 'DATABASE_URL','JWT_SECRET_KEY'){ Require ($envMap.Contains($key) -and -not [string]::IsNullOrWhiteSpace($envMap[$key])) "required configuration is absent: $key" }
    Require ($envMap['CORS_ALLOW_ALL_ORIGINS'] -eq '0') 'CORS allow-all must be disabled'
    Require ($envMap['CORS_ORIGINS'] -eq $CanonicalOrigin) 'canonical plural CORS origin is required'
    Require (-not (($envMap.Values -join ',') -match [regex]::Escape($LegacyOrigin))) 'legacy CORS origin remains effective'
    if($envMap.Contains('CORS_ORIGIN')){ Require ($envMap['CORS_ORIGIN'] -eq $CanonicalOrigin) 'singular/plural CORS origins disagree' }
}
function Write-Governed-Env([string]$Path) {
    $lines=[Collections.Generic.List[string]]([IO.File]::ReadAllLines($Path)); $wanted=@{ CORS_ALLOW_ALL_ORIGINS='0'; CORS_ORIGINS=$CanonicalOrigin }
    if((Env-Map $Path).Contains('CORS_ORIGIN')){ $wanted['CORS_ORIGIN']=$CanonicalOrigin }
    foreach($key in $wanted.Keys){ $found=$false; for($i=0;$i -lt $lines.Count;$i++){ if($lines[$i] -match "^\s*$key\s*="){ $lines[$i]="$key=$($wanted[$key])"; $found=$true } }; if(-not $found -and $key -ne 'CORS_ORIGIN'){ $lines.Add("$key=$($wanted[$key])") } }
    $tmp="$Path.$([guid]::NewGuid().ToString('N')).tmp"; [IO.File]::WriteAllLines($tmp,$lines,[Text.UTF8Encoding]::new($false)); Move-Item -LiteralPath $tmp -Destination $Path -Force
}
function Assert-TargetConfigCanBePrepared {
    $scratch=Join-Path ([IO.Path]::GetTempPath()) ("forwarder-$CandidateId-config-$([guid]::NewGuid().ToString('N')).env")
    try { Atomic-Copy $script:ProductionEnv $scratch; Write-Governed-Env $scratch; Validate-Env $scratch } finally { Remove-Item -LiteralPath $scratch -Force -ErrorAction SilentlyContinue }
}
function Require-Artifact([string]$Artifact,[string]$Sidecar) {
    Require (Test-Path -LiteralPath $Artifact -PathType Leaf) 'artifact is absent'
    Require ((Split-Path -Leaf $Artifact) -eq $ArtifactName) 'artifact filename differs from governed candidate'
    Require ((Hash $Artifact) -eq $ArtifactHash) 'artifact SHA-256 mismatch'
    Require (Test-Path -LiteralPath $Sidecar -PathType Leaf) 'artifact manifest is absent'
    Require ((Hash $Sidecar) -eq $ManifestHash) 'artifact manifest SHA-256 mismatch'
    $outer=Get-Content -Raw -LiteralPath $Sidecar|ConvertFrom-Json
    Require ($outer.source_commit -eq $SourceCommit) 'manifest source commit mismatch'
    Require ($outer.alembic_head -eq $TargetHead) 'manifest Alembic head mismatch'
    Require ($outer.artifact_sha256 -eq $ArtifactHash -and [int64]$outer.artifact_size -eq (Get-Item -LiteralPath $Artifact).Length) 'sidecar artifact identity mismatch'
}
function Get-GovernedPostgreSqlUrl([string]$RawUrl) {
    Require (-not [string]::IsNullOrWhiteSpace($RawUrl)) 'DATABASE_URL is absent'
    $match=[regex]::Match($RawUrl,'^(?<engine>postgresql)(?:\+(?<driver>psycopg2))?://',[Text.RegularExpressions.RegexOptions]::IgnoreCase)
    Require ($match.Success) 'DATABASE_URL is not a supported PostgreSQL URL'
    $normalized=[regex]::Replace($RawUrl,'^postgresql\+psycopg2://','postgresql://',[Text.RegularExpressions.RegexOptions]::IgnoreCase)
    try { $uri=[uri]$normalized } catch { Fail 'DATABASE_URL is malformed' }
    Require (-not [string]::IsNullOrWhiteSpace($uri.Host)) 'DATABASE_URL is malformed'
    Require (-not [string]::IsNullOrWhiteSpace($uri.AbsolutePath.Trim('/'))) 'DATABASE_URL is malformed'
    [pscustomobject]@{ Uri=$uri; Driver=if($match.Groups['driver'].Success){'psycopg2'}else{'default'} }
}
function Get-IdentityScalar([object[]]$Lines,[string]$Tag) {
    $taggedLines=@($Lines | ForEach-Object { [string]$_ } | Where-Object { $_.StartsWith("$Tag=") })
    Require ($taggedLines.Count -eq 1) "$Tag query must return exactly one tagged scalar"
    $value=$taggedLines[0].Substring($Tag.Length+1).Trim()
    Require (-not [string]::IsNullOrWhiteSpace($value)) "$Tag query returned an empty scalar"
    return [string]$value
}
function Assert-DatabaseIdentity {
    $map=Env-Map $script:ProductionEnv; Require ($map.Contains('DATABASE_URL')) 'DATABASE_URL is absent'
    $connection=Get-GovernedPostgreSqlUrl $map['DATABASE_URL']
    Write-Output 'DATABASE_URL_PRESENT=YES'; Write-Output 'DATABASE_ENGINE=POSTGRESQL'; Write-Output ("DATABASE_DRIVER="+$connection.Driver)
    if($SimulationRoot){
        $parts=(Get-Content -Raw -LiteralPath (Get-Sim 'database.txt')).Trim().Split('|',2)
        Require ($parts.Count -eq 2 -and $parts[0] -eq $ExpectedDatabase) 'simulated database identity mismatch'
        Require ($parts[1] -eq $TargetHead) 'simulated Alembic identity mismatch'
        return
    }
    $uri=$connection.Uri
    $userInfo=$uri.UserInfo.Split(':',2); Require (-not [string]::IsNullOrWhiteSpace($userInfo[0])) 'database user is absent'
    Require (Test-Path -LiteralPath $PsqlPath -PathType Leaf) 'psql executable unavailable'
    $oldPassword=$env:PGPASSWORD
    try {
        if($userInfo.Count -gt 1){ $env:PGPASSWORD=[uri]::UnescapeDataString($userInfo[1]) }
        $result=@(& $PsqlPath -X -q -v ON_ERROR_STOP=1 -h $uri.Host -p $uri.Port -U $userInfo[0] -d $script:ExpectedDatabase -Atc "BEGIN TRANSACTION READ ONLY; SELECT 'DATABASE=' || current_database(); SELECT 'ALEMBIC=' || version_num FROM alembic_version; COMMIT;")
        $psqlExit=$LASTEXITCODE
        Require ($psqlExit -eq 0) 'psql identity query failed'
        $actualDatabase=Get-IdentityScalar $result 'DATABASE'
        $actualAlembic=Get-IdentityScalar $result 'ALEMBIC'
        Write-Output "EXPECTED_DATABASE_VALUE=$($script:ExpectedDatabase)"; Write-Output "EXPECTED_DATABASE_TYPE=$($script:ExpectedDatabase.GetType().FullName)"; Write-Output "EXPECTED_DATABASE_LENGTH=$($script:ExpectedDatabase.Length)"
        Write-Output "ACTUAL_DATABASE_VALUE=$actualDatabase"; Write-Output "ACTUAL_DATABASE_TYPE=$($actualDatabase.GetType().FullName)"; Write-Output "ACTUAL_DATABASE_LENGTH=$($actualDatabase.Length)"
        $databaseEqual=[string]::Equals($actualDatabase,$script:ExpectedDatabase,[StringComparison]::Ordinal); Write-Output "DATABASE_EQUALS_RESULT=$databaseEqual"; Require $databaseEqual 'database identity mismatch'; Write-Output 'DATABASE_IDENTITY=PASS'
        Write-Output "EXPECTED_ALEMBIC_VALUE=$($script:ExpectedAlembic)"; Write-Output "EXPECTED_ALEMBIC_TYPE=$($script:ExpectedAlembic.GetType().FullName)"; Write-Output "EXPECTED_ALEMBIC_LENGTH=$($script:ExpectedAlembic.Length)"
        Write-Output "ACTUAL_ALEMBIC_VALUE=$actualAlembic"; Write-Output "ACTUAL_ALEMBIC_TYPE=$($actualAlembic.GetType().FullName)"; Write-Output "ACTUAL_ALEMBIC_LENGTH=$($actualAlembic.Length)"
        $alembicEqual=[string]::Equals($actualAlembic,$script:ExpectedAlembic,[StringComparison]::Ordinal); Write-Output "ALEMBIC_EQUALS_RESULT=$alembicEqual"; Require $alembicEqual 'Alembic identity mismatch'; Write-Output 'ALEMBIC_IDENTITY=PASS'
    } finally { $env:PGPASSWORD=$oldPassword }
}
function Get-Sim([string]$Name) { Join-Path $(if($QualificationRoot){$QualificationRoot}else{$SimulationRoot}) $Name }
function ConvertTo-GovernedWindowsPath([string]$Value) {
    if([string]::IsNullOrWhiteSpace($Value)){Fail 'IIS physical path is null or empty'}
    if($Value -ne $Value.Trim()){Fail 'IIS physical path contains leading or trailing whitespace'}
    $expanded=[Environment]::ExpandEnvironmentVariables($Value).Replace('/','\')
    if(-not [IO.Path]::IsPathRooted($expanded)){Fail 'IIS physical path is not absolute'}
    try { $full=[IO.Path]::GetFullPath($expanded) } catch { Fail 'IIS physical path is malformed' }
    $root=[IO.Path]::GetPathRoot($full)
    if($full.Length -gt $root.Length){$full=$full.TrimEnd('\')}
    return [string]$full
}
function Get-GovernedIisPhysicalPath {
    if($SimulationRoot){$records=@((Get-Content -Raw -LiteralPath (Get-Sim 'iis.txt')))}
    elseif($QualificationRoot){
        $contract=Get-Content -Raw -LiteralPath (Join-Path $QualificationRoot 'iis-contract.json')|ConvertFrom-Json
        switch($contract.physical_path_shape){
            'PROVIDER_THROWS' { Fail 'IIS physical path unreadable' }
            'PROVIDER_OBJECT' { $records=@([pscustomobject]@{physicalPath=$contract.physical_path_records[0]}) }
            'INTEGER' { $records=@([int]$contract.physical_path_records[0]) }
            'BOOLEAN' { $records=@([bool]$contract.physical_path_records[0]) }
            'STRING_ARRAY' { $records=[object[]]::new(1); $records[0]=[string[]]@($contract.physical_path_records) }
            'ZERO_RECORDS' { $records=@() }
            default { $records=@($contract.physical_path_records) }
        }
    } else {
        Require $script:IisInspectionReady 'IIS inspection prerequisites were not initialized'
        try {$records=@(Get-ItemProperty -LiteralPath 'IIS:\Sites\forwarder' -Name physicalPath -ErrorAction Stop)} catch {Fail 'IIS physical path unreadable'}
    }
    Write-Host "RAW_IIS_PROVIDER_RECORD_COUNT=$($records.Count)"
    $recordType=if($records.Count -eq 1 -and $null -ne $records[0]){$records[0].GetType().FullName}else{'<none>'}
    Write-Host "RAW_IIS_PROVIDER_RECORD_TYPE=$recordType"
    if($records.Count -ne 1){Fail 'IIS physical path must return exactly one scalar'}
    if($null -eq $records[0] -or $records[0].GetType().FullName -ne 'System.String'){Fail 'IIS physical path must be one scalar string'}
    return (ConvertTo-GovernedWindowsPath ([string]$records[0]))
}
function Assert-IisReference([string]$ExpectedPath,[string]$FailureMessage) {
    $expected=ConvertTo-GovernedWindowsPath $ExpectedPath
    $actual=Get-GovernedIisPhysicalPath
    Write-Host "EXPECTED_IIS_DIST_VALUE=$expected"; Write-Host "EXPECTED_IIS_DIST_TYPE=$($expected.GetType().FullName)"; Write-Host "EXPECTED_IIS_DIST_LENGTH=$($expected.Length)"
    Write-Host "ACTUAL_IIS_DIST_VALUE=$actual"; Write-Host "ACTUAL_IIS_DIST_TYPE=$($actual.GetType().FullName)"; Write-Host "ACTUAL_IIS_DIST_LENGTH=$($actual.Length)"
    $equal=[string]::Equals($actual,$expected,[StringComparison]::OrdinalIgnoreCase)
    Write-Host "IIS_DIST_EQUALS_RESULT=$equal"
    Require $equal $FailureMessage
}
function Initialize-IisInspection {
    if($SimulationRoot){ Write-Output 'IIS_INSPECTION_MODE=SIMULATED'; return }
    if($QualificationRoot){
        Require ($env:FORWARDER_REQ4A_HARNESS -eq 'REQ-4A-CONTROLLED-HARNESS') 'controlled harness authorization is absent'
        $contractPath=Join-Path $QualificationRoot 'iis-contract.json'
        Require (Test-Path -LiteralPath $contractPath -PathType Leaf) 'controlled IIS contract is absent'
        $contract=Get-Content -Raw -LiteralPath $contractPath|ConvertFrom-Json
        Require ($contract.schema -eq 'forwarder-req4a-iis-contract-v1') 'controlled IIS contract schema mismatch'
        Write-Output "WEBADMINISTRATION_MODULE_AVAILABLE=$($contract.module_available)"
        Require ($contract.module_available -eq 'YES') 'required IIS PowerShell module unavailable'
        Write-Output "WEBADMINISTRATION_IMPORT_RESULT=$($contract.import_result)"
        Require ($contract.import_result -eq 'PASS') 'IIS PowerShell module import failed'
        Write-Output "IIS_PROVIDER_AVAILABLE=$($contract.provider_available)"
        Require ($contract.provider_available -eq 'YES') 'IIS PowerShell provider unavailable'
        Write-Output "IIS_DRIVE_AVAILABLE=$($contract.drive_available)"
        Require ($contract.drive_available -eq 'YES') 'IIS PowerShell drive unavailable'
        Write-Output "IIS_TARGET_SITE_AVAILABLE=$($contract.site_available)"
        Require ($contract.site_available -eq 'YES') 'governed IIS site unavailable'
        Require ($contract.physical_path_read -eq 'PASS') 'IIS physical path unreadable'
        Require ($contract.binding_read -eq 'PASS') 'IIS bindings unreadable'
        Require ($contract.result_shape -eq 'VALID') 'malformed IIS inspection result'
        $script:IisInspectionReady=$true
        Write-Output 'HARNESS_IIS_CONTRACT_PATH=PASS'
        return
    }
    $available=@(Get-Module -ListAvailable -Name WebAdministration)
    Write-Output "WEBADMINISTRATION_MODULE_AVAILABLE=$(if($available.Count -gt 0){'YES'}else{'NO'})"
    Require ($available.Count -gt 0) 'required IIS PowerShell module unavailable'
    try { Import-Module WebAdministration -ErrorAction Stop } catch { Fail 'IIS PowerShell module import failed' }
    Write-Output 'WEBADMINISTRATION_IMPORT_RESULT=PASS'
    $provider=@(Get-PSProvider -PSProvider WebAdministration -ErrorAction SilentlyContinue)
    Write-Output "IIS_PROVIDER_AVAILABLE=$(if($provider.Count -gt 0){'YES'}else{'NO'})"
    Require ($provider.Count -gt 0) 'IIS PowerShell provider unavailable'
    $drive=@(Get-PSDrive -Name IIS -PSProvider WebAdministration -ErrorAction SilentlyContinue)
    Write-Output "IIS_DRIVE_AVAILABLE=$(if($drive.Count -gt 0){'YES'}else{'NO'})"
    Require ($drive.Count -gt 0) 'IIS PowerShell drive unavailable'
    Require (Test-Path -LiteralPath 'IIS:\Sites\forwarder' -PathType Container) 'governed IIS site unavailable'
    $script:IisInspectionReady=$true
}
function Initialize-ScheduledTaskInspection {
    if($SimulationRoot){ Write-Output 'SCHEDULED_TASK_INSPECTION_MODE=SIMULATED'; return }
    if($QualificationRoot){
        $contract=Get-Content -Raw -LiteralPath (Join-Path $QualificationRoot 'iis-contract.json')|ConvertFrom-Json
        Require ($contract.scheduled_tasks_available -eq 'YES') 'ScheduledTasks module unavailable'
        Require ($contract.scheduled_task_available -eq 'YES') 'governed Scheduled Task unavailable'
        Write-Output 'SCHEDULED_TASK_CONTRACT=PASS'
        return
    }
    $available=@(Get-Module -ListAvailable -Name ScheduledTasks)
    Require ($available.Count -gt 0) 'ScheduledTasks module unavailable'
    try { Import-Module ScheduledTasks -ErrorAction Stop } catch { Fail 'ScheduledTasks module import failed' }
    try { $task=Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop } catch { Fail 'governed Scheduled Task unavailable' }
    Require ($null -ne $task) 'governed Scheduled Task unavailable'
    Write-Output 'SCHEDULED_TASK_CONTRACT=PASS'
}
function Get-TaskReference { if($SimulationRoot -or $QualificationRoot){ return (Get-Content -Raw -LiteralPath (Get-Sim 'task.txt')).Trim() }; return ((Export-ScheduledTask -TaskName $TaskName) -replace '\r|\n',' ') }
function Capture-TaskState { if($SimulationRoot -or $QualificationRoot){ Atomic-Copy (Get-Sim 'task.txt') $script:TaskBackup; return }; Export-ScheduledTask -TaskName $TaskName | Set-Content -LiteralPath $script:TaskBackup -Encoding UTF8 }
function Restore-TaskState { if($SimulationRoot -or $QualificationRoot){ Atomic-Copy $script:TaskBackup (Get-Sim 'task.txt'); return }; Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -Raw -LiteralPath $script:TaskBackup) -Force | Out-Null }
function Set-TaskReference([string]$Reference) { if($SimulationRoot -or $QualificationRoot){ Set-Content -LiteralPath (Get-Sim 'task.txt') -Value $Reference -NoNewline; return }; $xml=Export-ScheduledTask -TaskName $TaskName; Require ($xml.Contains($script:PreviousRelease)) 'Scheduled Task does not contain governed previous release'; Register-ScheduledTask -TaskName $TaskName -Xml $xml.Replace($script:PreviousRelease,$Reference) -Force | Out-Null }
function Get-GovernedListenerCount {
    if($SimulationRoot -or $QualificationRoot){ return $(if((Get-Content -Raw -LiteralPath (Get-Sim 'listener.txt')).Trim() -eq '127.0.0.1:5101'){1}else{0}) }
    return @((Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)).Count
}
function Get-GovernedBackendListener([string]$ExpectedRelease,[switch]$AllowAbsent) {
    if($SimulationRoot -or $QualificationRoot){
        if((Get-GovernedListenerCount) -eq 0){if($AllowAbsent){return $null};Fail 'governed backend listener is absent'}
        return [pscustomobject]@{ProcessId=5101;ExecutablePath=(Join-Path $ExpectedRelease '.venv\Scripts\python.exe');CommandLine="$(Join-Path $ExpectedRelease '.venv\Scripts\python.exe') -m waitress --listen=127.0.0.1:5101 backend.wsgi:app"}
    }
    $connections=@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if($connections.Count -eq 0){if($AllowAbsent){return $null};Fail 'governed backend listener is absent'}
    if($connections.Count -ne 1){Fail 'backend listener identity is ambiguous'}
    $listenerPid=[int]$connections[0].OwningProcess
    $processes=@(Get-CimInstance Win32_Process -Filter "ProcessId = $listenerPid" -ErrorAction SilentlyContinue)
    if($processes.Count -ne 1){Fail 'backend listener process identity is unavailable'}
    $process=$processes[0]
    $commandLine=[string]$process.CommandLine
    $expectedPython=Join-Path $ExpectedRelease '.venv\Scripts\python.exe'
    if([string]::IsNullOrWhiteSpace($commandLine)){Fail 'backend listener command line is unavailable'}
    if(-not [string]::Equals((Split-Path -Leaf ([string]$process.ExecutablePath)),'python.exe',[StringComparison]::OrdinalIgnoreCase)){Fail 'backend listener executable is not Python'}
    if($commandLine.IndexOf($expectedPython,[StringComparison]::OrdinalIgnoreCase) -lt 0){Fail 'backend listener does not belong to expected release Python'}
    if($commandLine -notmatch '(?i)(^|\s)-m\s+waitress(\s|$)'){Fail 'backend listener is not Waitress'}
    if($commandLine.IndexOf('backend.wsgi:app',[StringComparison]::OrdinalIgnoreCase) -lt 0){Fail 'backend listener is not Forwarder WSGI'}
    Write-Host "GOVERNED_BACKEND_LISTENER_PID=$listenerPid"
    Write-Host "GOVERNED_BACKEND_RELEASE=$ExpectedRelease"
    Write-Host 'GOVERNED_BACKEND_PROCESS_IDENTITY=PASS'
    return $process
}
function Wait-GovernedListenerCount([int]$Expected,[string]$Message) {
    for($attempt=0;$attempt -lt 60;$attempt++){
        if((Get-GovernedListenerCount) -eq $Expected){ return }
        Start-Sleep -Milliseconds 500
    }
    Fail $Message
}
function Stop-GovernedBackend([string]$ExpectedRelease) {
    if($SimulationRoot -or $QualificationRoot){ Set-Content -LiteralPath (Get-Sim 'listener.txt') -Value 'STOPPED' -NoNewline }
    else {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        $listener=Get-GovernedBackendListener $ExpectedRelease -AllowAbsent
        if($null -ne $listener){
            try { Stop-Process -Id ([int]$listener.ProcessId) -Force -ErrorAction Stop } catch { Fail 'verified governed backend termination failed' }
            Write-Output "GOVERNED_BACKEND_TERMINATED_PID=$([int]$listener.ProcessId)"
        }
    }
    Wait-GovernedListenerCount 0 'previous backend listener did not stop'
    $script:BackendStopped=$true
    Write-Output 'PREVIOUS_BACKEND_STOPPED=YES'
}
function Start-GovernedBackend([string]$ExpectedRelease) {
    if($SimulationRoot -or $QualificationRoot){ Set-Content -LiteralPath (Get-Sim 'listener.txt') -Value '127.0.0.1:5101' -NoNewline }
    else {
        try { Enable-ScheduledTask -TaskName $TaskName -ErrorAction Stop | Out-Null; Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop } catch { Fail 'governed backend start failed' }
    }
    Wait-GovernedListenerCount 1 'new backend listener did not start'
    Get-GovernedBackendListener $ExpectedRelease | Out-Null
    Write-Output 'NEW_BACKEND_LISTENER_ACQUIRED=YES'
}
function Get-IisReference { return (Get-GovernedIisPhysicalPath) }
function Set-IisReference([string]$Reference) { if($SimulationRoot -or $QualificationRoot){ Set-Content -LiteralPath (Get-Sim 'iis.txt') -Value $Reference -NoNewline; return }; Set-ItemProperty -LiteralPath 'IIS:\Sites\forwarder' -Name physicalPath -Value $Reference }
function Verify-Release([string]$Release,[switch]$Runtime) {
    Require (Test-Path -LiteralPath (Join-Path $Release 'dist\index.html') -PathType Leaf) 'release frontend structure missing'
    Require (Test-Path -LiteralPath (Join-Path $Release 'backend\migrations\versions\20260907_direct_shipment_responsibility.py') -PathType Leaf) 'release migration identity missing'
    $innerPath=Join-Path $Release 'release-manifest.json'; Require (Test-Path -LiteralPath $innerPath -PathType Leaf) 'release content manifest is missing'
    $inner=Get-Content -Raw -LiteralPath $innerPath|ConvertFrom-Json
    Require ($inner.source_commit -eq $SourceCommit) 'extracted release source identity mismatch'
    Require ($inner.alembic_head -eq $TargetHead) 'extracted release Alembic identity mismatch'
    if(-not $Runtime){ return }
    if($SimulationRoot -or $QualificationRoot){
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'health.txt')).Trim() -eq '200') 'simulated health failed'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'cors.txt')).Trim() -eq $CanonicalOrigin) 'simulated canonical CORS failed'
        Require (-not (Test-Path -LiteralPath (Get-Sim 'legacy-cors-allowed.txt'))) 'simulated legacy CORS remains allowed'
        Require (-not (Test-Path -LiteralPath (Get-Sim 'unknown-cors-allowed.txt'))) 'simulated unknown CORS is allowed'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'preflight.txt')).Trim() -eq $CanonicalOrigin) 'simulated canonical preflight failed'
        if($SimulateVerificationFailure){ Fail 'forced simulated verification failure' }; return
    }
    Require (@(Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count -eq 1) 'backend listener is not singular'
    Require ((Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5101/api/health').StatusCode -eq 200) 'local health failed'
    Require ((Invoke-WebRequest -UseBasicParsing "$CanonicalOrigin/api/health").StatusCode -eq 200) 'canonical API health failed'
    $cors=Invoke-WebRequest -UseBasicParsing "$CanonicalOrigin/api/health" -Headers @{Origin=$CanonicalOrigin}; Require ($cors.Headers['Access-Control-Allow-Origin'] -eq $CanonicalOrigin) 'canonical CORS GET failed'
    $preflight=Invoke-WebRequest -UseBasicParsing "$CanonicalOrigin/api/health" -Method Options -Headers @{Origin=$CanonicalOrigin;'Access-Control-Request-Method'='GET'}; Require ($preflight.Headers['Access-Control-Allow-Origin'] -eq $CanonicalOrigin) 'canonical CORS preflight failed'
    $unknown=Invoke-WebRequest -UseBasicParsing "$CanonicalOrigin/api/health" -Headers @{Origin='https://unknown.forwarderet.ir'}; Require ($unknown.Headers['Access-Control-Allow-Origin'] -ne 'https://unknown.forwarderet.ir') 'unknown CORS is allowed'
    $legacy=Invoke-WebRequest -UseBasicParsing "$CanonicalOrigin/api/health" -Headers @{Origin=$LegacyOrigin}; Require ($legacy.Headers['Access-Control-Allow-Origin'] -ne $LegacyOrigin) 'legacy CORS remains allowed'
}
function Rollback {
    Set-State 'ROLLBACK_RUNNING'
    try {
        if($script:BackendStopped){
            Stop-GovernedBackend $script:TargetRelease
        }
        Atomic-Copy $script:EnvBackup $script:ProductionEnv
        Restore-TaskState
        Set-IisReference (Join-Path $script:PreviousRelease 'dist')
        if($script:TargetReleaseOwned -and (Test-Path -LiteralPath $script:TargetRelease)){ Remove-Item -LiteralPath $script:TargetRelease -Recurse -Force }
        if($script:BackendStopped){ Start-GovernedBackend $script:PreviousRelease }
        Require ((Hash $script:ProductionEnv) -eq $script:PreviousEnvHash) 'rollback configuration hash mismatch'
        Require ((Get-TaskReference) -match [regex]::Escape($script:PreviousRelease)) 'rollback task reference mismatch'
        Assert-IisReference (Join-Path $script:PreviousRelease 'dist') 'rollback IIS path mismatch'
        Set-State 'FAILED_AND_RECOVERED'; $script:Evidence.outcome='FAILED_AND_RECOVERED'
    } catch { Set-State 'FAILED_AND_NOT_RECOVERED'; $script:Evidence.outcome='FAILED_AND_NOT_RECOVERED'; throw }
}

try {
    Require (-not ($ValidateOnly -and $Execute)) 'choose only one execution mode'
    if(-not $ValidateOnly -and -not $Execute){ $ValidateOnly=$true }
    if($Execute){ Require ($ConfirmDeployment.IsPresent -eq $true) '-Execute requires -ConfirmDeployment' }
    if($SimulationRoot -or $QualificationRoot){ $fixtureRoot=if($QualificationRoot){$QualificationRoot}else{$SimulationRoot}; Require (Test-Path -LiteralPath $fixtureRoot -PathType Container) 'fixture root is absent'; $script:ProductionRoot=Join-Path $fixtureRoot 'production'; $script:RuntimeRoot=Join-Path $fixtureRoot 'runtime'; $script:StagingRoot=Join-Path $fixtureRoot 'staging'; $script:PreviousRelease=Join-Path $script:ProductionRoot 'release-adcc5da-adr043'; $script:TargetRelease=Join-Path $script:ProductionRoot 'release-f11f2ab-s7'; $script:ProductionEnv=Join-Path $script:RuntimeRoot 'production.env'; $ArtifactPath=Join-Path $script:StagingRoot $ArtifactName; $ManifestPath="$ArtifactPath.manifest.json" }
    else { Require ([Environment]::MachineName -eq $ExpectedHost) 'wrong host'; Require (([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'Administrator is required'; $script:ProductionRoot='C:\1-webapp\forwarder-production'; $script:RuntimeRoot='C:\1-webapp\forwarder-runtime'; $script:PreviousRelease=Join-Path $script:ProductionRoot 'release-adcc5da-adr043'; $script:TargetRelease=Join-Path $script:ProductionRoot 'release-f11f2ab-s7'; $script:ProductionEnv=Join-Path $script:RuntimeRoot 'production.env' }
    if(-not $BaselinePath){$BaselinePath=Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'expected-production-baseline.json'}
    if(-not (Test-Path -LiteralPath $BaselinePath -PathType Leaf)){Fail 'expected Production baseline is absent'}
    $baseline=Get-Content -Raw -LiteralPath $BaselinePath|ConvertFrom-Json
    if(-not ($baseline.database -is [string]) -or [string]::IsNullOrWhiteSpace($baseline.database)){Fail 'baseline database must be one scalar string'}
    if(-not ($baseline.alembic_head -is [string]) -or [string]::IsNullOrWhiteSpace($baseline.alembic_head)){Fail 'baseline Alembic must be one scalar string'}
    $script:ExpectedDatabase=$baseline.database; $script:ExpectedAlembic=$baseline.alembic_head
    Require-Artifact $ArtifactPath $ManifestPath
    if($SimulationRoot -or $QualificationRoot){ Require ((Get-Content -Raw -LiteralPath (Get-Sim 'host.txt')).Trim() -eq $ExpectedHost) 'wrong host'; Require ((Get-Content -Raw -LiteralPath (Get-Sim 'admin.txt')).Trim() -eq 'yes') 'Administrator is required' }
    Require (Test-Path -LiteralPath $script:PreviousRelease -PathType Container) 'current release is absent'
    Require (Test-Path -LiteralPath $script:ProductionEnv -PathType Leaf) 'production.env is absent'
    $script:RuntimeWrapper=Join-Path $script:RuntimeRoot 'phase1b_production_cutover_runtime.py'
    Require (Test-Path -LiteralPath $script:RuntimeWrapper -PathType Leaf) 'runtime wrapper is absent'
    if(-not $SimulationRoot -and -not $QualificationRoot){ Require ((Hash $script:RuntimeWrapper) -eq $RuntimeWrapperHash) 'runtime wrapper SHA-256 mismatch' }
    Assert-DatabaseIdentity
    $hasSingularCors=(Env-Map $script:ProductionEnv).Contains('CORS_ORIGIN')
    Assert-TargetConfigCanBePrepared
    Initialize-ScheduledTaskInspection
    Initialize-IisInspection
    if(-not $SimulationRoot -and -not $QualificationRoot){ Get-GovernedBackendListener $script:PreviousRelease | Out-Null }
    Require ((Get-TaskReference) -match [regex]::Escape($script:PreviousRelease)) 'Scheduled Task does not reference governed previous release'
    Assert-IisReference (Join-Path $script:PreviousRelease 'dist') 'IIS does not reference governed previous release dist'
    Require (-not (Test-Path -LiteralPath $script:TargetRelease)) 'target release already exists; refusing reuse'
    if($SimulationRoot -or $QualificationRoot){
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'task-metadata.txt')).Trim() -eq $TaskName) 'Scheduled Task metadata mismatch'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'iis-state.txt')).Trim() -eq 'Started') 'IIS site is not Started'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'iis-bindings.txt')).Trim() -eq 'http,https') 'canonical IIS bindings mismatch'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'listener.txt')).Trim() -eq '127.0.0.1:5101') 'backend listener mismatch'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'current-health.txt')).Trim() -eq '200') 'current backend health failed'
        $freeGb=[double](Get-Content -Raw -LiteralPath (Get-Sim 'disk-gb.txt'))
        Require ($freeGb -ge 5) 'insufficient disk capacity'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'current-cors.txt')).Trim() -eq 'LEGACY_TRANSITION_EXPECTED') 'current CORS state cannot transition'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'target-cors.txt')).Trim() -eq $CanonicalOrigin) 'invalid canonical CORS target'
        Require ((Get-Content -Raw -LiteralPath (Get-Sim 'unknown-origin.txt')).Trim() -eq 'REJECTED') 'unknown origin behavior mismatch'
        Write-Output 'CURRENT_STATE_CAN_TRANSITION=YES'
        Write-Output 'TARGET_CONFIGURATION_VALID=YES'
    } else {
        $task=Get-ScheduledTask -TaskName $TaskName; Require ($null -ne $task) 'Scheduled Task is absent'
        try { $site=Get-Website -Name 'forwarder' -ErrorAction Stop } catch { Fail 'IIS site inspection failed' }; Require ($site.State -eq 'Started') 'IIS site is not Started'
        try { $bindings=Get-WebBinding -Name 'forwarder' -ErrorAction Stop } catch { Fail 'IIS binding inspection failed' }; Require (@($bindings|Where-Object {$_.bindingInformation -eq '*:80:samand.forwarderet.ir'}).Count -eq 1) 'canonical HTTP binding is absent'; Require (@($bindings|Where-Object {$_.bindingInformation -eq '*:443:samand.forwarderet.ir'}).Count -eq 1) 'canonical HTTPS binding is absent'
        Require ((Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5101/api/health').StatusCode -eq 200) 'current backend health failed'
        Require (((Get-PSDrive -Name C).Free/1GB) -ge 5) 'insufficient disk capacity'
    }
    $script:PreviousEnvHash=Hash $script:ProductionEnv; $script:EnvBackup=Join-Path $script:RuntimeRoot ("production.env.$CandidateId.rollback"); $script:TaskBackup=Join-Path $script:RuntimeRoot ("$TaskName.$CandidateId.rollback.xml")
    Set-State 'STAGED_VERIFIED'
    if($ValidateOnly){
        $expectedBase=if($QualificationRoot){59}elseif($SimulationRoot){39}else{50}
        $expectedPrecheckCount=$expectedBase+$(if($hasSingularCors){1}else{0})
        Write-Output "PRECHECK_CONDITIONAL_CORS_ORIGIN=$(if($hasSingularCors){'EXECUTED'}else{'NOT_APPLICABLE'})"
        Write-Output "EXPECTED_PRECHECK_COUNT=$expectedPrecheckCount"
        Write-Output "EXECUTED_PRECHECK_COUNT=$($script:PrecheckCount)"
        Write-Output "PASSED_PRECHECK_COUNT=$($script:PassedPrecheckCount)"
        if($expectedPrecheckCount -ne $script:PrecheckCount -or $script:PrecheckCount -ne $script:PassedPrecheckCount){Fail 'precheck manifest incomplete'}
        Write-Output 'PRECHECK_MANIFEST=PASS'; Set-State 'ABORTED_BEFORE_MUTATION'; $script:Evidence.outcome='ABORTED_BEFORE_MUTATION'; $script:Evidence|ConvertTo-Json -Depth 4; exit 0
    }
    Write-Output 'MUTATION_BOUNDARY_REACHED'
    $script:Mutated=$true; Set-State 'ROLLBACK_STATE_CAPTURED'; Atomic-Copy $script:ProductionEnv $script:EnvBackup; Capture-TaskState
    Set-State 'STAGED'; if($SimulateStagingFailure){ Fail 'forced simulated staging failure' }; $script:TargetReleaseOwned=$true; Expand-Archive -LiteralPath $ArtifactPath -DestinationPath $script:TargetRelease -ErrorAction Stop
    Verify-Release $script:TargetRelease
    Set-State 'CONFIG_PREPARED'; Write-Governed-Env $script:ProductionEnv; Validate-Env $script:ProductionEnv
    Set-State 'SWITCHING'; Stop-GovernedBackend $script:PreviousRelease; Set-TaskReference $script:TargetRelease; Set-IisReference (Join-Path $script:TargetRelease 'dist')
    $updatedTaskReference=Get-TaskReference
    Require ($updatedTaskReference -match [regex]::Escape($script:TargetRelease)) 'Scheduled Task target reference was not installed'
    Require (-not ($updatedTaskReference -match [regex]::Escape($script:PreviousRelease))) 'Scheduled Task retains previous release reference'
    Set-State 'STARTING'; Start-GovernedBackend $script:TargetRelease
    Set-State 'VERIFYING'; Verify-Release $script:TargetRelease -Runtime
    Require ((Get-TaskReference) -match [regex]::Escape($script:TargetRelease)) 'Scheduled Task target verification failed'; Assert-IisReference (Join-Path $script:TargetRelease 'dist') 'IIS target verification failed'
    Set-State 'DEPLOYED_AND_VERIFIED'; $script:Evidence.outcome='DEPLOYED_AND_VERIFIED'; $script:Evidence|ConvertTo-Json -Depth 4
} catch {
    $message=$_.Exception.Message
    if($script:Mutated){
        switch($script:State){
            'STAGED' { Set-State 'STAGING_FAILED' }
            'SWITCHING' { Set-State 'SWITCH_FAILED' }
            'STARTING' { Set-State 'START_FAILED' }
            default { Set-State 'VERIFY_FAILED' }
        }
        try { Rollback } catch {}
    } else { Set-State 'PRECHECK_FAILED'; Set-State 'ABORTED_BEFORE_MUTATION'; $script:Evidence.outcome='ABORTED_BEFORE_MUTATION' }
    $script:Evidence.error=$message; $script:Evidence|ConvertTo-Json -Depth 4; exit 1
}
