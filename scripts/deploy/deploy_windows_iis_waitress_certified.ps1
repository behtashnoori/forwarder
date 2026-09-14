#requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$PackageRoot,
    [string]$ReleaseRoot='C:\1-webapp\forwarder-production',
    [string]$SiteName='forwarder',
    [string]$TaskName='Forwarder Backend Production',
    [int]$Port=5101,
    [switch]$ValidateOnly,
    [switch]$Execute,
    [switch]$ConfirmDeployment,
    [string]$FixtureStatePath,
    [ValidateSet('','BACKEND_STOP','PORT_RELEASE','BACKEND_START','LISTENER_VERIFY','IIS_SWITCH','INTERNAL_HEALTH','PUBLIC_HEALTH')][string]$FailAt=''
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'

$ApplicationCommit='b4294fcf4657fbb39b1895ef32e282c92ff9a244'
$RequiredRevision='20260921_shipment_evidence_ownership'
$RuntimeArchiveName='Forwarder-Windows-Runtime-S7-RC-a257669-r4.zip'
$Timeouts=@{DB_GATE=15;TASK_STOP=30;TASK_START=30;BACKEND_STOP=30;BACKEND_START=30;PORT_RELEASE=30;LISTENER_START=30;LISTENER_IDENTITY=30;LISTENER_VERIFY=30;IIS_VERIFY=15;INTERNAL_HEALTH=15;PUBLIC_HEALTH=20;ROLLBACK_RECOVERY=45}
$ArtifactRoot=Join-Path $PackageRoot 'artifact'
$Script:FailedStage='PRECHECK'
$Script:Previous=$null
$Script:Target=$null
$Script:Fixture=$null

function Write-Stage([string]$Name){$Script:FailedStage=$Name;Write-Output ('STAGE_'+$Name)}
function Stop-Release([string]$Expected,[string]$Actual,[int]$TimeoutSeconds=0){
    Write-Output ('FAILED_STAGE='+$Script:FailedStage)
    Write-Output ('EXPECTED='+$Expected)
    Write-Output ('ACTUAL='+$Actual)
    if($TimeoutSeconds -gt 0){Write-Output ('TIMEOUT_SECONDS='+$TimeoutSeconds)}
    throw ('RELEASE_STOP: '+$Script:FailedStage)
}
function Require([bool]$Condition,[string]$Expected,[string]$Actual){if(-not $Condition){Stop-Release $Expected $Actual}}
function Normalize-Path([string]$PathValue){
    Require (-not [string]::IsNullOrWhiteSpace($PathValue)) 'non-empty absolute Windows path' 'empty path'
    $clean=$PathValue.Trim().Trim('"').Trim("'") -replace '/','\'
    Require ($clean -notmatch '["'']') 'unquoted normalized path' $clean
    try{$absolute=[IO.Path]::GetFullPath($clean)}catch{Stop-Release 'valid absolute Windows path' $clean}
    return $absolute.TrimEnd('\')
}
function Same-Path([string]$Left,[string]$Right){return [string]::Equals((Normalize-Path $Left),(Normalize-Path $Right),[StringComparison]::OrdinalIgnoreCase)}
function Get-TaskRuntime([string]$TaskXml){
    try{[xml]$document=$TaskXml}catch{Stop-Release 'valid Scheduled Task XML' 'invalid XML'}
    $execActions=@($document.SelectNodes("//*[local-name()='Exec']"))
    Require ($execActions.Count -eq 1) 'exactly one Exec action' ([string]$execActions.Count)
    $commandPath=Normalize-Path ([string]$execActions[0].Command)
    $workingPath=Normalize-Path ([string]$execActions[0].WorkingDirectory)
    $taskArguments=[string]$execActions[0].Arguments
    if([IO.Path]::GetFileName($commandPath) -ieq 'python.exe'){$runtimePath=$commandPath}
    elseif([IO.Path]::GetFileName($commandPath) -ieq 'cmd.exe'){
        $runtimeMatches=@([regex]::Matches($taskArguments,'(?i)[A-Z]:[\\/][^\"]*?[\\/]runtime[\\/]python\.exe'))
        Require ($runtimeMatches.Count -eq 1) 'exactly one runtime python.exe in cmd arguments' ([string]$runtimeMatches.Count)
        $runtimePath=Normalize-Path $runtimeMatches[0].Value
    }else{Stop-Release 'cmd.exe or python.exe Scheduled Task launcher' $commandPath}
    Require ($runtimePath.StartsWith($workingPath+'\',[StringComparison]::OrdinalIgnoreCase)) 'runtime beneath WorkingDirectory' $runtimePath
    return $runtimePath
}
function Invoke-WithTimeout([string]$Operation,[int]$TimeoutSeconds,[scriptblock]$Work,[object[]]$ArgumentList=@()){
    $backgroundJob=Start-Job -ScriptBlock $Work -ArgumentList $ArgumentList
    try{
        if($null -eq (Wait-Job -Job $backgroundJob -Timeout $TimeoutSeconds)){Stop-Job -Job $backgroundJob -Force -ErrorAction SilentlyContinue;Stop-Release ($Operation+' completes') 'timeout' $TimeoutSeconds}
        $jobOutput=Receive-Job -Job $backgroundJob -ErrorAction Stop
        if($backgroundJob.State -ne 'Completed'){Stop-Release ($Operation+' completes') ([string]$backgroundJob.State) $TimeoutSeconds}
        return $jobOutput
    }finally{Remove-Job -Job $backgroundJob -Force -ErrorAction SilentlyContinue}
}
function Read-Fixture(){return Get-Content -Raw -LiteralPath $FixtureStatePath|ConvertFrom-Json}
function Write-Fixture(){ConvertTo-Json $Script:Fixture -Depth 8|Set-Content -LiteralPath $FixtureStatePath -Encoding UTF8}
function Assert-NotInjected([string]$StageName){if($FailAt -eq $StageName){Stop-Release ($StageName+' succeeds') 'injected failure' $Timeouts[$StageName]}}
function Get-IisPath(){if($FixtureStatePath){return [string]$Script:Fixture.iis_path};Import-Module WebAdministration -ErrorAction Stop;return [string](Get-Website -Name $SiteName -ErrorAction Stop).PhysicalPath}
function Get-TaskXml(){if($FixtureStatePath){return [string]$Script:Fixture.task_xml};return [string](Export-ScheduledTask -TaskName $TaskName)}
function Get-ListenerRuntime(){if($FixtureStatePath){Require ([bool]$Script:Fixture.listener_up) 'listener present' 'listener absent';return [string]$Script:Fixture.listener_runtime};$rows=@(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop|Where-Object {$_.LocalAddress -eq '127.0.0.1'});$ownerIds=@($rows|Select-Object -ExpandProperty OwningProcess|Sort-Object -Unique);Require ($ownerIds.Count -eq 1) 'one unique listener owner' ([string]$ownerIds.Count);$processId=[int]$ownerIds[0];$process=Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction Stop;Require (-not [string]::IsNullOrWhiteSpace([string]$process.ExecutablePath)) 'listener executable path' 'missing ExecutablePath';Require ([string]$process.CommandLine -match '(?i)-m\s+waitress' -and [string]$process.CommandLine -match '(?i)backend\.wsgi:app') 'Waitress backend.wsgi:app listener' ([string]$process.CommandLine);return [string]$process.ExecutablePath}
function Verify-Database(){Assert-NotInjected 'DB_GATE';if($FixtureStatePath){Require ([string]$Script:Fixture.db_revision -eq $RequiredRevision) $RequiredRevision ([string]$Script:Fixture.db_revision);return};$pythonPath=[string]$Script:Previous.python;Invoke-WithTimeout 'DB revision gate' $Timeouts.DB_GATE {param($Executable,$Gate,$Root);& $Executable $Gate '--app-root' $Root '--env-file' 'C:\1-webapp\forwarder-runtime\production.env';if($LASTEXITCODE -ne 0){throw 'revision gate failed'}} @($pythonPath,(Join-Path $PackageRoot 'revision_gate.py'),$ArtifactRoot)|Out-Null}
function Stop-Backend(){Assert-NotInjected 'BACKEND_STOP';if($FixtureStatePath){$Script:Fixture.task_running=$false;$Script:Fixture.listener_up=$false;Write-Fixture;return};Invoke-WithTimeout 'Scheduled Task stop' $Timeouts.BACKEND_STOP {param($Name);Stop-ScheduledTask -TaskName $Name -ErrorAction Stop} @($TaskName)|Out-Null}
function Wait-PortReleased(){Assert-NotInjected 'PORT_RELEASE';if($FixtureStatePath){Require (-not [bool]$Script:Fixture.listener_up) 'port released' 'listener remains';return};Invoke-WithTimeout 'port release' $Timeouts.PORT_RELEASE {param($ListenPort,$Limit);$releaseDeadline=[DateTime]::UtcNow.AddSeconds($Limit);do{if(-not (Get-NetTCPConnection -State Listen -LocalPort $ListenPort -ErrorAction SilentlyContinue)){return};Start-Sleep -Milliseconds 250}while([DateTime]::UtcNow -lt $releaseDeadline);throw 'port release timeout'} @($Port,$Timeouts.PORT_RELEASE)|Out-Null}
function Create-Target(){if($FixtureStatePath){$Script:Fixture.target_created=$true;Write-Fixture;return};New-Item -ItemType Directory -Path $Script:Target.root -ErrorAction Stop|Out-Null;Get-ChildItem -LiteralPath $ArtifactRoot -Force|Copy-Item -Destination $Script:Target.root -Recurse -Force;$targetRuntime=Join-Path $Script:Target.root 'runtime\python.exe';if(-not(Test-Path -LiteralPath $targetRuntime -PathType Leaf)){Expand-Archive -LiteralPath (Join-Path $Script:Target.root $RuntimeArchiveName) -DestinationPath (Join-Path $Script:Target.root 'runtime') -ErrorAction Stop};Require (Test-Path -LiteralPath $targetRuntime -PathType Leaf) 'runtime\python.exe present after target creation' 'runtime missing'}
function Start-Target(){Assert-NotInjected 'BACKEND_START';if($FixtureStatePath){$Script:Fixture.task_xml=[string]$Script:Target.task_xml;$Script:Fixture.task_running=$true;$Script:Fixture.listener_up=$true;$Script:Fixture.listener_runtime=if($FailAt -eq 'LISTENER_VERIFY'){'C:\wrong\runtime\python.exe'}else{[string]$Script:Target.python};Write-Fixture;return};Invoke-WithTimeout 'target task registration and start' $Timeouts.BACKEND_START {param($Name,$Xml);Register-ScheduledTask -TaskName $Name -Xml $Xml -Force|Out-Null;Start-ScheduledTask -TaskName $Name -ErrorAction Stop} @($TaskName,[string]$Script:Target.task_xml)|Out-Null}
function Verify-TargetListener(){Assert-NotInjected 'LISTENER_VERIFY';if($FixtureStatePath){$observed=Get-ListenerRuntime;Require (Same-Path $observed $Script:Target.python) $Script:Target.python $observed;return};Invoke-WithTimeout 'listener appearance and identity' $Timeouts.LISTENER_VERIFY {param($Expected,$ListenPort,$Limit);$listenerDeadline=[DateTime]::UtcNow.AddSeconds($Limit);do{$connections=@(Get-NetTCPConnection -State Listen -LocalPort $ListenPort -ErrorAction SilentlyContinue|Where-Object {$_.LocalAddress -eq '127.0.0.1'});$owners=@($connections|Select-Object -ExpandProperty OwningProcess|Sort-Object -Unique);if($owners.Count -eq 1){$candidateProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$owners[0]) -ErrorAction SilentlyContinue;if($null -ne $candidateProcess -and [string]::Equals([IO.Path]::GetFullPath([string]$candidateProcess.ExecutablePath),[IO.Path]::GetFullPath($Expected),[StringComparison]::OrdinalIgnoreCase)){return}};Start-Sleep -Milliseconds 250}while([DateTime]::UtcNow -lt $listenerDeadline);throw 'listener verification timeout'} @([string]$Script:Target.python,$Port,$Timeouts.LISTENER_VERIFY)|Out-Null}
function Switch-Iis(){Assert-NotInjected 'IIS_SWITCH';if($FixtureStatePath){$Script:Fixture.iis_path=[string]$Script:Target.iis;Write-Fixture}else{Invoke-WithTimeout 'IIS switch' $Timeouts.IIS_VERIFY {param($Name,$Path);Import-Module WebAdministration;Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.applicationHost/sites/site[@name='$Name']/application[@path='/']/virtualDirectory[@path='/']" -Name physicalPath -Value $Path} @($SiteName,[string]$Script:Target.iis)|Out-Null};Require (Same-Path (Get-IisPath) $Script:Target.iis) $Script:Target.iis (Get-IisPath)}
function Verify-Health([string]$Kind,[int]$TimeoutSeconds){Assert-NotInjected $Kind;if($FixtureStatePath){Require ([bool]$Script:Fixture.health) ($Kind+' healthy') 'unhealthy';return};$uri=if($Kind -eq 'INTERNAL_HEALTH'){"http://127.0.0.1:$Port/api/health"}{'https://samand.forwarderet.ir/api/health'};Invoke-WithTimeout $Kind $TimeoutSeconds {param($HealthUri);$response=Invoke-WebRequest -UseBasicParsing -Uri $HealthUri -TimeoutSec 5;if($response.StatusCode -lt 200 -or $response.StatusCode -ge 300){throw 'unhealthy'};$payload=$response.Content|ConvertFrom-Json;Require ($null -ne $payload) 'JSON health response' 'invalid JSON'} @($uri)|Out-Null}
function Restore-Previous(){Write-Stage 'ROLLBACK';if($FixtureStatePath){$Script:Fixture.iis_path=[string]$Script:Previous.iis;$Script:Fixture.task_xml=[string]$Script:Previous.task_xml;$Script:Fixture.task_running=$true;$Script:Fixture.listener_up=$true;$Script:Fixture.listener_runtime=[string]$Script:Previous.python;$Script:Fixture.health=$true;$Script:Fixture.target_active=$false;Write-Fixture}else{Invoke-WithTimeout 'rollback recovery' $Timeouts.ROLLBACK_RECOVERY {param($Name,$Xml,$IisPath);Import-Module WebAdministration;Register-ScheduledTask -TaskName $Name -Xml $Xml -Force|Out-Null;Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.applicationHost/sites/site[@name='$Name']/application[@path='/']/virtualDirectory[@path='/']" -Name physicalPath -Value $IisPath;Start-ScheduledTask -TaskName $Name} @($TaskName,[string]$Script:Previous.task_xml,[string]$Script:Previous.iis)|Out-Null}}

Require (-not($ValidateOnly -and $Execute)) 'one mode' 'both modes';if(-not $ValidateOnly -and -not $Execute){$ValidateOnly=$true};if($Execute){Require $ConfirmDeployment '-ConfirmDeployment with -Execute' 'confirmation absent'}
if($FixtureStatePath){$Script:Fixture=Read-Fixture}
Write-Stage 'PACKAGE_VERIFY';& (Join-Path $PackageRoot 'VERIFY-PACKAGE.ps1') -PackageRoot $PackageRoot
Write-Stage 'BASELINE_CAPTURE';$previousIis=Get-IisPath;$previousTask=Get-TaskXml;$previousPython=Get-TaskRuntime $previousTask;$previousRoot=Split-Path -Parent (Split-Path -Parent $previousPython);$previousListener=Get-ListenerRuntime;Require (Same-Path $previousListener $previousPython) $previousPython $previousListener
$Script:Previous=[pscustomobject]@{iis=$previousIis;task_xml=$previousTask;python=$previousPython;root=$previousRoot;process_id=if($FixtureStatePath){91320}else{0}}
Write-Stage 'DB_GATE';Verify-Database
if($ValidateOnly){Write-Output 'FULL_VALIDATEONLY_SIMULATION=PASS';exit 0}
$targetRoot=Join-Path $ReleaseRoot 'release-forwarder-systemic-workflow-certified';$targetPython=Join-Path $targetRoot 'runtime\python.exe';$Script:Target=[pscustomobject]@{root=$targetRoot;python=$targetPython;iis=(Join-Path $targetRoot 'dist');task_xml=$previousTask.Replace($previousRoot,$targetRoot)}
try{Write-Stage 'BACKEND_STOP';Stop-Backend;Write-Stage 'PORT_RELEASE';Wait-PortReleased;Write-Stage 'TARGET_RELEASE';Create-Target;Write-Stage 'BACKEND_START';Start-Target;Write-Stage 'LISTENER_VERIFY';Verify-TargetListener;Write-Stage 'IIS_SWITCH';Switch-Iis;Write-Stage 'INTERNAL_HEALTH';Verify-Health 'INTERNAL_HEALTH' $Timeouts.INTERNAL_HEALTH;Write-Stage 'PUBLIC_HEALTH';Verify-Health 'PUBLIC_HEALTH' $Timeouts.PUBLIC_HEALTH;if($FixtureStatePath){$Script:Fixture.target_active=$true;Write-Fixture};Write-Output 'FULL_EXECUTE_SIMULATION=PASS'}catch{Restore-Previous;throw}
