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
$script:State = 'PRECHECK'
$script:Mutated = $false
$script:Evidence = [ordered]@{ candidate_id=$CandidateId; source_commit=$SourceCommit; states=@(); outcome=$null }

function Set-State([string]$Value) { $script:State=$Value; $script:Evidence.states += $Value; Write-Output "STATE=$Value" }
function Fail([string]$Message) { throw "DEPLOYMENT_GATE: $Message" }
function Require([bool]$Condition,[string]$Message) { if(-not $Condition){ Fail $Message } }
function Hash([string]$Path) { $stream=[IO.File]::OpenRead($Path);$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$stream.Dispose();$sha.Dispose()} }
function Atomic-Copy([string]$Source,[string]$Destination) { $tmp="$Destination.$([guid]::NewGuid().ToString('N')).tmp"; Copy-Item -LiteralPath $Source -Destination $tmp -Force; Move-Item -LiteralPath $tmp -Destination $Destination -Force }
function Env-Map([string]$Path) { $map=[ordered]@{}; foreach($line in [IO.File]::ReadAllLines($Path)){ if($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$'){ $map[$Matches[1]]=$Matches[2] } }; return $map }
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
    Require $match.Success 'DATABASE_URL is not a supported PostgreSQL URL'
    $normalized=[regex]::Replace($RawUrl,'^postgresql\+psycopg2://','postgresql://',[Text.RegularExpressions.RegexOptions]::IgnoreCase)
    try { $uri=[uri]$normalized } catch { Fail 'DATABASE_URL is malformed' }
    Require (-not [string]::IsNullOrWhiteSpace($uri.Host)) 'DATABASE_URL is malformed'
    Require (-not [string]::IsNullOrWhiteSpace($uri.AbsolutePath.Trim('/'))) 'DATABASE_URL is malformed'
    [pscustomobject]@{ Uri=$uri; Driver=if($match.Groups['driver'].Success){'psycopg2'}else{'default'} }
}
function Assert-DatabaseIdentity {
    $map=Env-Map $script:ProductionEnv; Require $map.Contains('DATABASE_URL') 'DATABASE_URL is absent'
    $connection=Get-GovernedPostgreSqlUrl $map['DATABASE_URL']
    Write-Output 'DATABASE_URL_PRESENT=YES'; Write-Output 'DATABASE_ENGINE=POSTGRESQL'; Write-Output ("DATABASE_DRIVER="+$connection.Driver)
    if($SimulationRoot){
        $parts=(Get-Content -Raw -LiteralPath (Get-Sim 'database.txt')).Trim().Split('|',2)
        Require ($parts.Count -eq 2 -and $parts[0] -eq $ExpectedDatabase) 'simulated database identity mismatch'
        Require ($parts[1] -eq $TargetHead) 'simulated Alembic identity mismatch'
        return
    }
    $uri=$connection.Uri
    $userInfo=$uri.UserInfo.Split(':',2); Require ($userInfo[0]) 'database user is absent'
    $oldPassword=$env:PGPASSWORD
    try {
        if($userInfo.Count -gt 1){ $env:PGPASSWORD=[uri]::UnescapeDataString($userInfo[1]) }
        $result=& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -X -v ON_ERROR_STOP=1 -h $uri.Host -p $uri.Port -U $userInfo[0] -d $ExpectedDatabase -Atc "BEGIN TRANSACTION READ ONLY; SELECT current_database() || '|' || version_num FROM alembic_version; COMMIT;"
        Require (($result | Select-Object -First 1).Trim() -eq "$ExpectedDatabase|$TargetHead") 'database or Alembic identity mismatch'
    } finally { $env:PGPASSWORD=$oldPassword }
}
function Get-Sim([string]$Name) { Join-Path $SimulationRoot $Name }
function Get-TaskReference { if($SimulationRoot){ return (Get-Content -Raw -LiteralPath (Get-Sim 'task.txt')).Trim() }; return ((Export-ScheduledTask -TaskName $TaskName) -replace '\r|\n',' ') }
function Capture-TaskState { if($SimulationRoot){ Atomic-Copy (Get-Sim 'task.txt') $script:TaskBackup; return }; Export-ScheduledTask -TaskName $TaskName | Set-Content -LiteralPath $script:TaskBackup -Encoding UTF8 }
function Restore-TaskState { if($SimulationRoot){ Atomic-Copy $script:TaskBackup (Get-Sim 'task.txt'); return }; Register-ScheduledTask -TaskName $TaskName -Xml (Get-Content -Raw -LiteralPath $script:TaskBackup) -Force | Out-Null }
function Set-TaskReference([string]$Reference) { if($SimulationRoot){ Set-Content -LiteralPath (Get-Sim 'task.txt') -Value $Reference -NoNewline; return }; $xml=Export-ScheduledTask -TaskName $TaskName; Require ($xml.Contains($script:PreviousRelease)) 'Scheduled Task does not contain governed previous release'; Register-ScheduledTask -TaskName $TaskName -Xml $xml.Replace($script:PreviousRelease,$Reference) -Force | Out-Null }
function Get-IisReference { if($SimulationRoot){ return (Get-Content -Raw -LiteralPath (Get-Sim 'iis.txt')).Trim() }; return (Get-ItemProperty -LiteralPath 'IIS:\Sites\forwarder' -Name physicalPath).physicalPath }
function Set-IisReference([string]$Reference) { if($SimulationRoot){ Set-Content -LiteralPath (Get-Sim 'iis.txt') -Value $Reference -NoNewline; return }; Set-ItemProperty -LiteralPath 'IIS:\Sites\forwarder' -Name physicalPath -Value $Reference }
function Verify-Release([string]$Release,[switch]$Runtime) {
    Require (Test-Path -LiteralPath (Join-Path $Release 'dist\index.html') -PathType Leaf) 'release frontend structure missing'
    Require (Test-Path -LiteralPath (Join-Path $Release 'backend\migrations\versions\20260907_direct_shipment_responsibility.py') -PathType Leaf) 'release migration identity missing'
    $innerPath=Join-Path $Release 'release-manifest.json'; Require (Test-Path -LiteralPath $innerPath -PathType Leaf) 'release content manifest is missing'
    $inner=Get-Content -Raw -LiteralPath $innerPath|ConvertFrom-Json
    Require ($inner.source_commit -eq $SourceCommit) 'extracted release source identity mismatch'
    Require ($inner.alembic_head -eq $TargetHead) 'extracted release Alembic identity mismatch'
    if(-not $Runtime){ return }
    if($SimulationRoot){
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
        Atomic-Copy $script:EnvBackup $script:ProductionEnv
        Restore-TaskState
        Set-IisReference (Join-Path $script:PreviousRelease 'dist')
        Require ((Hash $script:ProductionEnv) -eq $script:PreviousEnvHash) 'rollback configuration hash mismatch'
        Require ((Get-TaskReference) -match [regex]::Escape($script:PreviousRelease)) 'rollback task reference mismatch'
        Require ((Get-IisReference) -eq (Join-Path $script:PreviousRelease 'dist')) 'rollback IIS path mismatch'
        Set-State 'FAILED_AND_RECOVERED'; $script:Evidence.outcome='FAILED_AND_RECOVERED'
    } catch { Set-State 'FAILED_AND_NOT_RECOVERED'; $script:Evidence.outcome='FAILED_AND_NOT_RECOVERED'; throw }
}

try {
    Require (-not ($ValidateOnly -and $Execute)) 'choose only one execution mode'
    if(-not $ValidateOnly -and -not $Execute){ $ValidateOnly=$true }
    if($Execute){ Require $ConfirmDeployment '-Execute requires -ConfirmDeployment' }
    if($SimulationRoot){ Require (Test-Path -LiteralPath $SimulationRoot -PathType Container) 'simulation root is absent'; $script:ProductionRoot=Get-Sim 'production'; $script:RuntimeRoot=Get-Sim 'runtime'; $script:StagingRoot=Get-Sim 'staging'; $script:PreviousRelease=Join-Path $script:ProductionRoot 'release-adcc5da-adr043'; $script:TargetRelease=Join-Path $script:ProductionRoot 'release-f11f2ab-s7'; $script:ProductionEnv=Join-Path $script:RuntimeRoot 'production.env'; $ArtifactPath=Join-Path $script:StagingRoot $ArtifactName; $ManifestPath="$ArtifactPath.manifest.json" }
    else { Require ([Environment]::MachineName -eq $ExpectedHost) 'wrong host'; Require (([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) 'Administrator is required'; $script:ProductionRoot='C:\1-webapp\forwarder-production'; $script:RuntimeRoot='C:\1-webapp\forwarder-runtime'; $script:PreviousRelease=Join-Path $script:ProductionRoot 'release-adcc5da-adr043'; $script:TargetRelease=Join-Path $script:ProductionRoot 'release-f11f2ab-s7'; $script:ProductionEnv=Join-Path $script:RuntimeRoot 'production.env' }
    Require-Artifact $ArtifactPath $ManifestPath
    if($SimulationRoot){ Require ((Get-Content -Raw -LiteralPath (Get-Sim 'host.txt')).Trim() -eq $ExpectedHost) 'wrong host'; Require ((Get-Content -Raw -LiteralPath (Get-Sim 'admin.txt')).Trim() -eq 'yes') 'Administrator is required' }
    Require (Test-Path -LiteralPath $script:PreviousRelease -PathType Container) 'current release is absent'
    Require (Test-Path -LiteralPath $script:ProductionEnv -PathType Leaf) 'production.env is absent'
    Require (Test-Path -LiteralPath (Join-Path $script:RuntimeRoot 'phase1b_production_cutover_runtime.py') -PathType Leaf) 'runtime wrapper is absent'
    Assert-DatabaseIdentity
    Assert-TargetConfigCanBePrepared
    Require ((Get-TaskReference) -match [regex]::Escape($script:PreviousRelease)) 'Scheduled Task does not reference governed previous release'
    Require ((Get-IisReference) -eq (Join-Path $script:PreviousRelease 'dist')) 'IIS does not reference governed previous release dist'
    Require (-not (Test-Path -LiteralPath $script:TargetRelease)) 'target release already exists; refusing reuse'
    if(-not $SimulationRoot){
        $task=Get-ScheduledTask -TaskName $TaskName; Require ($null -ne $task) 'Scheduled Task is absent'
        $site=Get-Website -Name 'forwarder'; Require ($site.State -eq 'Started') 'IIS site is not Started'
        $bindings=Get-WebBinding -Name 'forwarder'; Require (@($bindings|Where-Object {$_.bindingInformation -eq '*:80:samand.forwarderet.ir'}).Count -eq 1) 'canonical HTTP binding is absent'; Require (@($bindings|Where-Object {$_.bindingInformation -eq '*:443:samand.forwarderet.ir'}).Count -eq 1) 'canonical HTTPS binding is absent'
        Require ((Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5101/api/health').StatusCode -eq 200) 'current backend health failed'
        Require (((Get-PSDrive -Name C).Free/1GB) -ge 5) 'insufficient disk capacity'
    }
    $script:PreviousEnvHash=Hash $script:ProductionEnv; $script:EnvBackup=Join-Path $script:RuntimeRoot ("production.env.$CandidateId.rollback"); $script:TaskBackup=Join-Path $script:RuntimeRoot ("$TaskName.$CandidateId.rollback.xml")
    Set-State 'STAGED_VERIFIED'
    if($ValidateOnly){ Set-State 'ABORTED_BEFORE_MUTATION'; $script:Evidence.outcome='ABORTED_BEFORE_MUTATION'; $script:Evidence|ConvertTo-Json -Depth 4; exit 0 }
    Write-Output 'MUTATION_BOUNDARY_REACHED'
    $script:Mutated=$true; Set-State 'ROLLBACK_STATE_CAPTURED'; Atomic-Copy $script:ProductionEnv $script:EnvBackup; Capture-TaskState
    Set-State 'STAGED'; if($SimulateStagingFailure){ Fail 'forced simulated staging failure' }; Expand-Archive -LiteralPath $ArtifactPath -DestinationPath $script:TargetRelease -ErrorAction Stop
    Verify-Release $script:TargetRelease
    Set-State 'CONFIG_PREPARED'; Write-Governed-Env $script:ProductionEnv; Validate-Env $script:ProductionEnv
    Set-State 'SWITCHING'; Set-TaskReference $script:TargetRelease; Set-IisReference (Join-Path $script:TargetRelease 'dist')
    Set-State 'STARTING'; if(-not $SimulationRoot){ Enable-ScheduledTask -TaskName $TaskName; Start-ScheduledTask -TaskName $TaskName }
    Set-State 'VERIFYING'; Verify-Release $script:TargetRelease -Runtime
    Require ((Get-TaskReference) -match [regex]::Escape($script:TargetRelease)) 'Scheduled Task target verification failed'; Require ((Get-IisReference) -eq (Join-Path $script:TargetRelease 'dist')) 'IIS target verification failed'
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
