# All resources and child environments are created by the shared owned runner.
$ErrorActionPreference = 'Stop'
Push-Location (Resolve-Path (Join-Path $PSScriptRoot '../..'))
try {
    python -B -m scripts.uat.run_fwd07_disposable_postgres --browser
    if ($LASTEXITCODE -ne 0) { throw 'Owned browser qualification failed' }
} finally { Pop-Location }
