#requires -Version 5.1
[CmdletBinding()]
param([string]$SimulationRoot,[string]$PsqlPath,[string]$ExpectedPackageId='D2-VALIDATION-S7-RC-f11f2ab-r11-final')

$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath=Join-Path $Root 'D2-package-manifest.json'
$PackageId=$ExpectedPackageId
function Hash([string]$Path){$stream=[IO.File]::OpenRead($Path);$sha=[Security.Cryptography.SHA256]::Create();try{([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$stream.Dispose();$sha.Dispose()}}
function NoGo([string]$Message){Write-Output "VALIDATION_RESULT=NO_GO";Write-Output "PRODUCTION_MUTATION=NO";Write-Output "DEPLOYMENT_PERFORMED=NO";throw "D2 validation package: $Message"}
try {
    if(-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)){NoGo 'package manifest is absent'}
    $manifest=Get-Content -Raw -LiteralPath $ManifestPath|ConvertFrom-Json
    if($manifest.package_id -ne $PackageId){NoGo 'package identity mismatch'}
    foreach($record in @($manifest.files)){
        $path=Join-Path $Root $record.name
        if(-not (Test-Path -LiteralPath $path -PathType Leaf)){NoGo "package file is absent: $($record.name)"}
        if((Get-Item -LiteralPath $path).Length -ne [int64]$record.bytes -or (Hash $path) -ne $record.sha256){NoGo "package file identity mismatch: $($record.name)"}
    }
    $entry=Join-Path $Root 'deploy_s7_rc_f11f2ab.ps1'
    $artifact=Join-Path $Root 'Forwarder-S7-RC-f11f2ab.zip'
    $sidecar=Join-Path $Root 'Forwarder-S7-RC-f11f2ab.zip.manifest.json'
    $ps51=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    if(-not (Test-Path -LiteralPath $ps51 -PathType Leaf)){NoGo 'Windows PowerShell 5.1 executable is absent'}
    $actualVersion=& $ps51 -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'
    if($LASTEXITCODE -ne 0 -or -not ([string]$actualVersion).StartsWith('5.1.')){NoGo 'Windows PowerShell 5.1 runtime is required'}
    $resolvedEntry=(Resolve-Path -LiteralPath $entry).Path
    if($resolvedEntry -ne [IO.Path]::GetFullPath((Join-Path $Root 'deploy_s7_rc_f11f2ab.ps1'))){NoGo 'deployment script resolved outside the package'}
    $childArguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$resolvedEntry,'-ValidateOnly','-ArtifactPath',$artifact,'-ManifestPath',$sidecar)
    if($SimulationRoot){$childArguments+=@('-SimulationRoot',$SimulationRoot)}
    if($PsqlPath){$childArguments+=@('-PsqlPath',$PsqlPath)}
    $childArguments+=@('-BaselinePath',(Join-Path $Root 'expected-production-baseline.json'))
    $savedErrorActionPreference=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    $result=& $ps51 @childArguments 2>&1
    $exit=$LASTEXITCODE
    $ErrorActionPreference=$savedErrorActionPreference
    $report=[ordered]@{timestamp_utc=[DateTime]::UtcNow.ToString('o');validation_package_id=$PackageId;candidate_id='S7-RC-f11f2ab';source_commit='f11f2abfbff396f66f261f11c7f4bdb80b2d2007';artifact_sha256='a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d';manifest_sha256='4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f';current_cors_classification='LEGACY_TRANSITION_EXPECTED';target_cors_contract='https://samand.forwarderet.ir; allow-all=0; legacy rejected';validate_only_zero_mutation='YES';production_mutation='NO';deployment_performed='NO';d1_output=@($result|ForEach-Object {[string]$_})}
    $report.validation_result=if($exit -eq 0 -and ($report.d1_output -join "`n") -match 'ABORTED_BEFORE_MUTATION'){'GO'}else{'NO_GO'}
    $reportPath=Join-Path $Root ('D2-validation-report-'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'.json')
    $report|ConvertTo-Json -Depth 5|Set-Content -LiteralPath $reportPath -Encoding UTF8
    $result|Write-Output
    Write-Output "VALIDATION_REPORT=$reportPath"
    Write-Output "VALIDATION_RESULT=$($report.validation_result)"
    Write-Output 'PRODUCTION_MUTATION=NO'
    Write-Output 'DEPLOYMENT_PERFORMED=NO'
    if($report.validation_result -ne 'GO'){exit 1}
} catch {
    if($_.Exception.Message -notmatch '^D2 validation package:'){
        Write-Output 'GATE=PACKAGED_OPERATOR'
        Write-Output 'RESULT=FAIL'
        Write-Output 'REASON=TOOLING_DEFECT'
        Write-Output 'VALIDATION_RESULT=NO_GO'
        Write-Output 'PRODUCTION_MUTATION=NO'
        Write-Output 'DEPLOYMENT_PERFORMED=NO'
    }
    exit 1
}
