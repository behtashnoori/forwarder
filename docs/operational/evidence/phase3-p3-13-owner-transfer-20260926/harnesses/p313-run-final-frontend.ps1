$ErrorActionPreference = 'Stop'
$evidence = 'D:\1-webapp\forwarder-dev\p313-qualification-c091490-20260926'
$source = 'c0914906af6675c016d5b77d51ecc8a0c05c0b72'
if ((git rev-parse HEAD).Trim() -ne $source -or (git status --porcelain)) { throw 'Source changed' }
$started = [DateTime]::UtcNow.ToString('o')
& node node_modules/vitest/vitest.mjs run *> (Join-Path $evidence 'frontend-full.log')
$code = $LASTEXITCODE
$unchanged = (git rev-parse HEAD).Trim() -eq $source -and -not (git status --porcelain)
@{ product_sha=$source; exit_code=$code; source_unchanged=$unchanged; started_at_utc=$started; finished_at_utc=[DateTime]::UtcNow.ToString('o'); status=$(if($code -eq 0 -and $unchanged){'PASS'}else{'FAIL_OR_SOURCE_CHANGED'}) } | ConvertTo-Json | Set-Content (Join-Path $evidence 'frontend-result.json') -Encoding utf8
Get-Content (Join-Path $evidence 'frontend-full.log') -Tail 12
if ($code -ne 0 -or -not $unchanged) { exit 1 }
