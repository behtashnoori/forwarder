#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$PackageRoot,[string]$DeployScript)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module Microsoft.PowerShell.Utility -ErrorAction Stop
if(-not $DeployScript){$DeployScript=Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1'}
$old='C:\1-webapp\forwarder-production\release-old'
$py=Join-Path $old 'runtime\python.exe'
$xml='<Task><Actions><Exec><Command>C:\Windows\System32\cmd.exe</Command><Arguments>/d /c &quot;'+$py+'&quot; -m waitress --listen=127.0.0.1:5101 backend.wsgi:app</Arguments><WorkingDirectory>'+$old+'</WorkingDirectory></Exec></Actions></Task>'
$temp=Join-Path ([IO.Path]::GetTempPath()) ('fw-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp|Out-Null
try{
    & (Join-Path $PackageRoot 'VERIFY-PACKAGE.ps1') -PackageRoot $PackageRoot|Out-Null
    $fixturePackage=Join-Path $temp 'fixture-package'
    New-Item -ItemType Directory -Path $fixturePackage|Out-Null
    Set-Content -LiteralPath (Join-Path $fixturePackage 'VERIFY-PACKAGE.ps1') -Value 'Write-Output "FIXTURE_PACKAGE_VERIFIED=YES"' -Encoding UTF8
    $stateFile=Join-Path $temp 'state.json'
    function Reset-State([string]$Revision){
        @{iis_path=(Join-Path $old 'dist');task_xml=$xml;enabled=$true;listener_runtime=$py;listener_up=$true;health=$true;db_revision=$Revision}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $stateFile -Encoding UTF8
    }
    foreach($revision in @('20260920_legal_customer_nullable_contact_names','20260921_shipment_evidence_ownership')){
        Reset-State $revision
        $before=(Get-FileHash -LiteralPath $stateFile -Algorithm SHA256).Hash
        & $DeployScript -PackageRoot $fixturePackage -ValidateOnly -FixtureStatePath $stateFile|Out-Null
        if((Get-FileHash -LiteralPath $stateFile -Algorithm SHA256).Hash -ne $before){throw 'ValidateOnly mutated state'}
    }
    Reset-State '20260908_invalid_lineage'
    $rejected=$false
    try{& $DeployScript -PackageRoot $fixturePackage -ValidateOnly -FixtureStatePath $stateFile|Out-Null}catch{$rejected=$true}
    if(-not $rejected){throw 'unknown DB lineage was accepted'}
    Reset-State '20260920_legal_customer_nullable_contact_names'
    & $DeployScript -PackageRoot $fixturePackage -Execute -ConfirmDeployment -FixtureStatePath $stateFile|Out-Null
    $result=Get-Content -Raw -LiteralPath $stateFile|ConvertFrom-Json
    if($result.db_revision -ne '20260921_shipment_evidence_ownership' -or $result.listener_runtime -eq $py -or $result.iis_path -eq (Join-Path $old 'dist')){throw 'execute did not complete fixture cutover and migration'}
    foreach($stage in @('PACKAGE_VERIFY','BASELINE_CAPTURE','DB_GATE','MIGRATION','TARGET_MATERIALIZE','TASK_DISABLE','BACKEND_STOP','PORT_RELEASE','TASK_SWITCH','BACKEND_START','LISTENER_VERIFY','INTERNAL_HEALTH','IIS_SWITCH','IIS_VERIFY','PUBLIC_HEALTH','POST_DEPLOY_VERIFY')){
        Reset-State '20260920_legal_customer_nullable_contact_names'
        $rejected=$false
        try{& $DeployScript -PackageRoot $fixturePackage -Execute -ConfirmDeployment -FixtureStatePath $stateFile -FailAt $stage|Out-Null}catch{$rejected=$true}
        if(-not $rejected){throw "failure injection accepted at $stage"}
        $after=Get-Content -Raw -LiteralPath $stateFile|ConvertFrom-Json
        if($after.listener_runtime -ne $py -or $after.iis_path -ne (Join-Path $old 'dist') -or -not $after.enabled -or -not $after.listener_up){throw "rollback invariant failed at $stage"}
    }
    Write-Output 'DB_GATE_MATRIX=PASS'
    Write-Output 'MIGRATION_EXECUTION_CONTRACT=PASS'
    Write-Output 'FULL_VALIDATEONLY_SIMULATION=PASS'
    Write-Output 'VALIDATEONLY_ZERO_MUTATION=PASS'
    Write-Output 'FULL_EXECUTE_SIMULATION=PASS'
    Write-Output 'FAILURE_INJECTION_MATRIX=PASS'
    Write-Output 'ROLLBACK_MATRIX=PASS'
    Write-Output 'ONE_PASS_OPERATOR_SIMULATION=PASS'
    $realTest=Join-Path $PackageRoot 'QUALIFY-REAL-VALIDATEONLY.ps1'
    if(-not (Test-Path -LiteralPath $realTest -PathType Leaf) -and $DeployScript -ne (Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1')){$realTest=Join-Path $PSScriptRoot 'test_real_nonfixture_validateonly.ps1'}
    if(-not (Test-Path -LiteralPath $realTest -PathType Leaf)){throw 'nonfixture ValidateOnly qualification is absent'}
    & $realTest -PackageRoot $PackageRoot -DeployScript $DeployScript
    $executeTest=Join-Path $PackageRoot 'QUALIFY-REAL-EXECUTE.ps1'
    if(-not (Test-Path -LiteralPath $executeTest -PathType Leaf) -and $DeployScript -ne (Join-Path $PackageRoot 'deploy_windows_iis_waitress.ps1')){$executeTest=Join-Path $PSScriptRoot 'test_real_execute_simulation.ps1'}
    if(-not (Test-Path -LiteralPath $executeTest -PathType Leaf)){throw 'real Execute qualification is absent'}
    & $executeTest -PackageRoot $PackageRoot -DeployScript $DeployScript
}finally{Remove-Item -LiteralPath $temp -Recurse -Force}
