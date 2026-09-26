param([string]$EvidenceDirectory,[string]$ProductSha)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null
if ((git rev-parse HEAD).Trim() -ne $ProductSha -or (git status --porcelain)) { throw 'Exact clean Product SHA required' }
$started = (Get-Date).ToUniversalTime().ToString('o')
node node_modules/vitest/vitest.mjs run --reporter=default --reporter=json --outputFile (Join-Path $EvidenceDirectory 'vitest.json') *> (Join-Path $EvidenceDirectory 'frontend.log')
$code = $LASTEXITCODE
$unchanged = (git rev-parse HEAD).Trim() -eq $ProductSha -and -not (git status --porcelain)
@{product_sha=$ProductSha; started=$started; finished=(Get-Date).ToUniversalTime().ToString('o'); source_unchanged=$unchanged; exit_code=$code; status=$(if($code -eq 0 -and $unchanged){'PASS'}else{'FAIL'})} | ConvertTo-Json | Set-Content (Join-Path $EvidenceDirectory 'result.json') -Encoding utf8
if ($code -ne 0 -or -not $unchanged) { exit 1 }
