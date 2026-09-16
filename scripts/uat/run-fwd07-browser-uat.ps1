param([string]$EvidenceDirectory = (Join-Path $env:TEMP ('forwarder-fwd07-browser-' + [guid]::NewGuid().ToString('N'))))
$ErrorActionPreference='Stop'
$repo=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$password=[guid]::NewGuid().ToString('N'); $apiPort=5057; $uiPort=8087
foreach($port in @($apiPort,$uiPort)) { $probe=[System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback,$port); try{$probe.Start()}finally{$probe.Stop()} }
New-Item -ItemType Directory -Force $EvidenceDirectory | Out-Null
$env:APP_ENV='test'; $env:FWD07_UAT_PASSWORD=$password; $env:FWD07_UAT_API_PORT="$apiPort"; $env:FWD07_UAT_BASE_URL="http://127.0.0.1:$uiPort"; $env:FWD07_UAT_EVIDENCE_DIR=$EvidenceDirectory; $env:VITE_BACKEND_URL="http://127.0.0.1:$apiPort"
function Wait-Ready($Url,$Process) {
 $deadline=[DateTime]::UtcNow.AddSeconds(30)
 do { if($Process.HasExited){throw 'Owned runtime exited before readiness'}; try{if((Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 1).StatusCode -eq 200){return}}catch{}; Start-Sleep -Milliseconds 250 } while([DateTime]::UtcNow -lt $deadline)
 throw "Startup readiness timeout: $Url"
}
$backend=$null; $frontend=$null; $runner=$null; $exitCode=1; $phase='startup'; $started=[DateTime]::UtcNow
try {
 $backend=Start-Process python -ArgumentList '-m','scripts.uat.fwd07_browser_fixture' -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $EvidenceDirectory 'backend.out') -RedirectStandardError (Join-Path $EvidenceDirectory 'backend.err')
 Wait-Ready "http://127.0.0.1:$apiPort/api/health" $backend
 $frontend=Start-Process node -ArgumentList 'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',"$uiPort",'--strictPort' -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $EvidenceDirectory 'frontend.out') -RedirectStandardError (Join-Path $EvidenceDirectory 'frontend.err')
 Wait-Ready "http://127.0.0.1:$uiPort" $frontend
 $phase='scenario'; $scenarioStarted=[DateTime]::UtcNow
 $runner=Start-Process node -ArgumentList 'scripts/uat/fwd07_browser_runner.mjs' -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $EvidenceDirectory 'runner.out') -RedirectStandardError (Join-Path $EvidenceDirectory 'runner.err')
 @{runId=(Split-Path $EvidenceDirectory -Leaf);launcherPid=$PID;backendPid=$backend.Id;frontendPid=$frontend.Id;runnerPid=$runner.Id;startupSeconds=($scenarioStarted-$started).TotalSeconds} | ConvertTo-Json | Set-Content (Join-Path $EvidenceDirectory 'run.json')
 $deadline=[DateTime]::UtcNow.AddSeconds(180)
 while(-not $runner.HasExited){if([DateTime]::UtcNow -gt $deadline){throw 'Scenario suite timeout: 180 seconds'};Start-Sleep -Milliseconds 500;$runner.Refresh()}
 $exitCode=$runner.ExitCode
 if($exitCode -ne 0){throw 'FWD07 browser failed; see result.json and runner.err'}
 $phase='completed';Write-Output "FWD07_BROWSER_EVIDENCE=$EvidenceDirectory"
} finally {
 foreach($owned in @($runner,$frontend,$backend)){if($owned -and -not $owned.HasExited){Stop-Process -Id $owned.Id -Force}}
 @{phase=$phase;exitCode=$exitCode;elapsedSeconds=([DateTime]::UtcNow-$started).TotalSeconds;ownedRuntimesStopped=$true} | ConvertTo-Json | Set-Content (Join-Path $EvidenceDirectory 'launcher-result.json')
 Remove-Item Env:FWD07_UAT_PASSWORD -ErrorAction SilentlyContinue
}
